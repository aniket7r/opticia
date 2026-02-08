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
 * Falls back to ScriptProcessorNode if AudioWorklet is unavailable.
 */
export class AudioProcessor {
  private audioContext: AudioContext | null = null;
  private mediaStreamSource: MediaStreamAudioSourceNode | null = null;
  private processorNode: AudioWorkletNode | ScriptProcessorNode | null = null;
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

    // Try AudioWorklet first, fall back to ScriptProcessor
    try {
      await this.setupAudioWorklet();
    } catch {
      console.warn("[AudioProcessor] AudioWorklet unavailable, using ScriptProcessor fallback");
      this.setupScriptProcessor();
    }

    this.isProcessing = true;
  }

  private async setupAudioWorklet(): Promise<void> {
    if (!this.audioContext || !this.mediaStreamSource) return;

    await this.audioContext.audioWorklet.addModule("/audio-worklet-processor.js");
    const workletNode = new AudioWorkletNode(this.audioContext, "pcm-processor");

    workletNode.port.onmessage = (event) => {
      if (!this.isProcessing || !this.onChunk) return;

      const { samples, sampleRate: sourceSampleRate } = event.data;

      // Downsample to 16kHz
      const downsampled = downsample(samples, sourceSampleRate, TARGET_SAMPLE_RATE);

      // Convert to PCM16 and base64
      const pcm16 = float32ToPcm16(downsampled);
      const base64 = pcm16ToBase64(pcm16);

      this.onChunk(base64);
    };

    this.mediaStreamSource.connect(workletNode);
    // Connect to destination to keep the pipeline alive (output is silent)
    workletNode.connect(this.audioContext.destination);

    this.processorNode = workletNode;
  }

  private setupScriptProcessor(): void {
    if (!this.audioContext || !this.mediaStreamSource) return;

    const bufferSize = 4096;
    const scriptNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

    scriptNode.onaudioprocess = (event: AudioProcessingEvent) => {
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

    this.processorNode = scriptNode;
  }

  /**
   * Stop processing and clean up.
   */
  stop(): void {
    this.isProcessing = false;

    if (this.processorNode) {
      this.processorNode.disconnect();
      this.processorNode = null;
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

// Shared AudioContext for decoding - created lazily
let sharedDecodingContext: AudioContext | null = null;

function getDecodingContext(): AudioContext {
  if (!sharedDecodingContext || sharedDecodingContext.state === "closed") {
    sharedDecodingContext = new AudioContext();
  }
  return sharedDecodingContext;
}

/**
 * Decodes base64 PCM audio to AudioBuffer for playback.
 */
export async function decodePcmAudio(
  base64Pcm: string,
  sampleRate: number = 24000,
  audioContext?: AudioContext
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

  // Use provided context or shared context
  const ctx = audioContext || getDecodingContext();
  const audioBuffer = ctx.createBuffer(1, float32.length, sampleRate);
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

    try {
      // Resume context if suspended (browser autoplay policy)
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      // Pass our context to avoid creating new ones
      const buffer = await decodePcmAudio(base64Pcm, sampleRate, this.audioContext);
      this.queue.push(buffer);

      if (!this.isPlaying) {
        this.playNext();
      }
    } catch (error) {
      console.error("[AudioPlayer] Error enqueueing audio:", error);
    }
  }

  private async playNext(): Promise<void> {
    if (!this.audioContext || this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    // Check if context is in a bad state
    if (this.audioContext.state === "closed") {
      console.warn("[AudioPlayer] AudioContext is closed, recreating...");
      this.audioContext = new AudioContext();
    }

    // Resume if suspended
    if (this.audioContext.state === "suspended") {
      try {
        await this.audioContext.resume();
      } catch (err) {
        console.error("[AudioPlayer] Failed to resume context:", err);
        this.isPlaying = false;
        return;
      }
    }

    this.isPlaying = true;
    const buffer = this.queue.shift()!;

    try {
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = buffer;
      this.currentSource.connect(this.audioContext.destination);
      this.currentSource.onended = () => this.playNext();
      this.currentSource.start();
    } catch (error) {
      console.error("[AudioPlayer] Error playing audio:", error);
      // Try to continue with next chunk
      this.playNext();
    }
  }

  /**
   * Stop playback and clear queue.
   */
  stop(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch {
        // Ignore errors when stopping (may already be stopped)
      }
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
