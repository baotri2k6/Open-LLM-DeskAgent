/**
 * WAV recorder adapted from Open-LLM-VTuber's web_tool recorder.
 * Output: base64 PCM16 mono WAV at 16 kHz, suitable for Whisper.
 */
export class VoiceRecorder {
  constructor() {
    this._mediaRecorder = null;
    this._stream = null;
    this._chunks = [];
    this._isRecording = false;
    this._audioCtx = null;
  }

  async start() {
    if (this._isRecording) return true;

    this._chunks = [];
    this._stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000 },
    });

    this._mediaRecorder = new MediaRecorder(
      this._stream,
      this._getRecorderOptions(),
    );
    this._isRecording = true;
    this._mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) this._chunks.push(event.data);
    });
    this._mediaRecorder.start();
    return true;
  }

  stop() {
    return new Promise((resolve) => {
      if (!this._mediaRecorder || !this._isRecording) {
        resolve(null);
        return;
      }

      this._mediaRecorder.addEventListener(
        "stop",
        async () => {
          this._isRecording = false;

          const blob = new Blob(this._chunks, {
            type: this._mediaRecorder.mimeType || "audio/webm",
          });
          const arrayBuffer = await blob.arrayBuffer();

          let audioBuffer;
          try {
            this._audioCtx ??= new (
              window.AudioContext || window.webkitAudioContext
            )();
            audioBuffer = await this._audioCtx.decodeAudioData(arrayBuffer);
          } catch (err) {
            console.error("[VoiceRecorder] decodeAudioData failed:", err);
            this._cleanup();
            resolve(null);
            return;
          }

          const wavBuffer = this._buildWAV(audioBuffer);
          const wavBlob = new Blob([wavBuffer], { type: "audio/wav" });
          const b64 = await new Promise((res) => {
            const reader = new FileReader();
            reader.onload = () => res(reader.result.split(",")[1]);
            reader.readAsDataURL(wavBlob);
          });

          this._cleanup();
          resolve(b64);
        },
        { once: true },
      );

      this._mediaRecorder.stop();
    });
  }

  get isRecording() {
    return this._isRecording;
  }

  _getRecorderOptions() {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
    ];
    const mimeType = candidates.find((type) =>
      MediaRecorder.isTypeSupported?.(type),
    );
    return mimeType ? { mimeType } : {};
  }

  _cleanup() {
    this._stream?.getTracks().forEach((track) => track.stop());
    this._stream = null;
    this._mediaRecorder = null;
    this._chunks = [];
  }

  _buildWAV(audioBuffer) {
    const targetSampleRate = 16000;
    const numChannels = 1;
    const bitDepth = 16;

    let samples = audioBuffer.getChannelData(0);
    if (audioBuffer.sampleRate !== targetSampleRate) {
      samples = this._resample(
        samples,
        audioBuffer.sampleRate,
        targetSampleRate,
      );
    }

    const dataLength = samples.length * (bitDepth / 8);
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);

    this._writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + dataLength, true);
    this._writeString(view, 8, "WAVE");
    this._writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, targetSampleRate, true);
    view.setUint32(28, (targetSampleRate * numChannels * bitDepth) / 8, true);
    view.setUint16(32, (numChannels * bitDepth) / 8, true);
    view.setUint16(34, bitDepth, true);
    this._writeString(view, 36, "data");
    view.setUint32(40, dataLength, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const sample = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(
        offset,
        sample < 0 ? sample * 0x8000 : sample * 0x7fff,
        true,
      );
    }

    return buffer;
  }

  _writeString(view, offset, text) {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  }

  _resample(data, fromSampleRate, toSampleRate) {
    const ratio = toSampleRate / fromSampleRate;
    const output = new Float32Array(Math.round(data.length * ratio));

    for (let i = 0; i < output.length; i++) {
      const position = i / ratio;
      const index = Math.floor(position);
      const fraction = position - index;
      output[i] =
        index + 1 < data.length
          ? data[index] * (1 - fraction) + data[index + 1] * fraction
          : data[index];
    }

    return output;
  }
}
