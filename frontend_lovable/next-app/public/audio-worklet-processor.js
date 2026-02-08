/**
 * AudioWorklet processor for real-time PCM audio capture.
 * Runs in a separate thread for better performance.
 */
class PcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 4096;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0];

    // Accumulate samples
    for (let i = 0; i < channelData.length; i++) {
      this._buffer.push(channelData[i]);
    }

    // When buffer is full, send it
    if (this._buffer.length >= this._bufferSize) {
      const samples = new Float32Array(this._buffer.splice(0, this._bufferSize));
      this.port.postMessage({ samples, sampleRate: sampleRate });
    }

    return true;
  }
}

registerProcessor("pcm-processor", PcmProcessor);
