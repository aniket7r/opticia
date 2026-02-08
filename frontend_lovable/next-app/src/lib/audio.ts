/**
 * Audio processing utilities for Opticia AI.
 * Handles PCM conversion and audio streaming.
 */

const TARGET_SAMPLE_RATE = 16000;

/**
 * Converts Float32Array audio samples to 16-bit PCM.
 */
export function float32ToPcm16(float32Array: Float32Array): Int16Array {
  const pcm16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    // Clamp to [-1, 1] and convert to 16-bit
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm16;
}

/**
 * Converts Int16Array PCM to base64 string.
 */
export function pcm16ToBase64(pcm16: Int16Array): string {
  const bytes = new Uint8Array(pcm16.buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Downsamples audio from source rate to target rate.
 */
export function downsample(
  buffer: Float32Array,
  sourceRate: number,
  targetRate: number
): Float32Array {
  if (sourceRate === targetRate) {
    return buffer;
  }

  const ratio = sourceRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const srcIndex = i * ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, buffer.length - 1);
    const fraction = srcIndex - srcIndexFloor;

    // Linear interpolation
    result[i] = buffer[srcIndexFloor] * (1 - fraction) + buffer[srcIndexCeil] * fraction;
  }

  return result;
}

/**
 * Audio processor using AudioWorklet for real-time PCM conversion.
 */
export class AudioProcessor {
  private audioContext: AudioContext | null = null;
  private mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private stream: MediaStream | null = null;
  private onChunk: ((base64Pcm: string) => void) | null = null;
  private isProcessing = false;

  /**
   * Start processing audio from a MediaStream.
   */
  async start(
    stream: MediaStream,
    onChunk: (base64Pcm: string) => void
  ): Promise<void> {
    if (this.isProcessing) {
      return;
    }

    this.stream = stream;
    this.onChunk = onChunk;

    // Create audio context
    this.audioContext = new AudioContext({
      sampleRate: 48000, // Browser default, will downsample
    });

    // Create media stream source
    this.mediaStreamSource = this.audioContext.createMediaStreamSource(stream);

    // Use ScriptProcessor as fallback (AudioWorklet requires HTTPS)
    await this.setupScriptProcessor();

    this.isProcessing = true;
  }

  private async setupScriptProcessor(): Promise<void> {
    if (!this.audioContext || !this.mediaStreamSource) return;

    const bufferSize = 4096;
    // @ts-ignore - ScriptProcessorNode is deprecated but widely supported
    const scriptNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

    scriptNode.onaudioprocess = (event) => {
      if (!this.isProcessing || !this.onChunk) return;

      const inputData = event.inputBuffer.getChannelData(0);

      // Downsample to 16kHz
      const downsampled = downsample(
        inputData,
        this.audioContext!.sampleRate,
        TARGET_SAMPLE_RATE
      );

      // Convert to PCM16
      const pcm16 = float32ToPcm16(downsampled);

      // Convert to base64
      const base64 = pcm16ToBase64(pcm16);

      this.onChunk(base64);
    };

    this.mediaStreamSource.connect(scriptNode);
    scriptNode.connect(this.audioContext.destination);

    // @ts-ignore
    this.workletNode = scriptNode;
  }

  /**
   * Stop processing and clean up.
   */
  stop(): void {
    this.isProcessing = false;

    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }

    if (this.mediaStreamSource) {
      this.mediaStreamSource.disconnect();
      this.mediaStreamSource = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.stream = null;
    this.onChunk = null;
  }
}

/**
 * Decodes base64 PCM audio to AudioBuffer for playback.
 */
export async function decodePcmAudio(
  base64Pcm: string,
  sampleRate: number = 24000
): Promise<AudioBuffer> {
  // Decode base64 to bytes
  const binaryString = atob(base64Pcm);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // Convert to Int16Array
  const pcm16 = new Int16Array(bytes.buffer);

  // Convert to Float32Array for AudioBuffer
  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7fff);
  }

  // Create AudioBuffer
  const audioContext = new AudioContext();
  const audioBuffer = audioContext.createBuffer(1, float32.length, sampleRate);
  audioBuffer.copyToChannel(float32, 0);

  return audioBuffer;
}

/**
 * Audio player for streaming AI audio responses.
 */
export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private queue: AudioBuffer[] = [];
  private isPlaying = false;
  private currentSource: AudioBufferSourceNode | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.audioContext = new AudioContext();
    }
  }

  /**
   * Add audio chunk to playback queue.
   */
  async enqueue(base64Pcm: string, sampleRate: number = 24000): Promise<void> {
    if (!this.audioContext) return;

    const buffer = await decodePcmAudio(base64Pcm, sampleRate);
    this.queue.push(buffer);

    if (!this.isPlaying) {
      this.playNext();
    }
  }

  private playNext(): void {
    if (!this.audioContext || this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const buffer = this.queue.shift()!;

    this.currentSource = this.audioContext.createBufferSource();
    this.currentSource.buffer = buffer;
    this.currentSource.connect(this.audioContext.destination);
    this.currentSource.onended = () => this.playNext();
    this.currentSource.start();
  }

  /**
   * Stop playback and clear queue.
   */
  stop(): void {
    if (this.currentSource) {
      this.currentSource.stop();
      this.currentSource = null;
    }
    this.queue = [];
    this.isPlaying = false;
  }

  /**
   * Clean up resources.
   */
  dispose(): void {
    this.stop();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}
