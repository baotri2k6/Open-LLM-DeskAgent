class VoiceRecorder {
  _stream = null;
  _audioCtx = null;
  _source = null;
  _processor = null;
  _samples = [];
  _isRecording = false;
  _noiseFloor = 0.015;
  _minThreshold = 0.012;
  _maxThreshold = 0.08;
  _margin = 0.012;
  _hasSpoken = false;
  _isSpeaking = false;
  _silenceStart = null;
  _recordingStart = 0;
  _silenceCallbackTriggered = false;
  _onSilenceCallback = null;
  onSpeechStartCallback = null;
  initialTimeoutMs = 6e3;
  lastDraftText = "";
  async start(onSilenceCallback) {
    if (this._isRecording) return true;
    this._samples = [];
    this._hasSpoken = false;
    this._isSpeaking = false;
    this._silenceStart = null;
    this._silenceCallbackTriggered = false;
    this._recordingStart = Date.now();
    this._onSilenceCallback = onSilenceCallback;
    this.lastDraftText = "";
    this._stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16e3,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this._audioCtx = new AudioContextClass({ sampleRate: 16e3 });
    if (!this._audioCtx) return false;
    this._source = this._audioCtx.createMediaStreamSource(this._stream);
    this._processor = this._audioCtx.createScriptProcessor(4096, 1, 1);
    this._processor.onaudioprocess = (e) => {
      if (!this._isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      const chunk = new Float32Array(inputData.length);
      chunk.set(inputData);
      this._samples.push(chunk);
      let sum = 0;
      for (let i = 0; i < inputData.length; i++) {
        sum += inputData[i] * inputData[i];
      }
      const rms = Math.sqrt(sum / inputData.length);
      if (rms < this._noiseFloor * 1.5 || rms < 0.02) {
        this._noiseFloor = this._noiseFloor * 0.95 + rms * 0.05;
      }
      const threshold = Math.max(
        this._minThreshold,
        Math.min(this._maxThreshold, this._noiseFloor + this._margin)
      );
      if (rms > threshold) {
        if (!this._isSpeaking) {
          this._isSpeaking = true;
          if (!this._hasSpoken) {
            this._hasSpoken = true;
            if (this.onSpeechStartCallback) {
              this.onSpeechStartCallback(rms);
            }
          }
        }
        this._silenceStart = null;
      } else {
        this._isSpeaking = false;
        if (this._hasSpoken) {
          if (this._silenceStart === null) {
            this._silenceStart = Date.now();
          } else {
            const silenceMs = Date.now() - this._silenceStart;
            const text = (this.lastDraftText || "").trim();
            const endsWithPunctuation = /[.!?]$/.test(text);
            const requiredSilenceMs = endsWithPunctuation ? 600 : 1500;
            if (silenceMs >= requiredSilenceMs) {
              this._triggerSilence();
            }
          }
        } else {
          const elapsed = Date.now() - this._recordingStart;
          if (elapsed >= this.initialTimeoutMs) {
            console.log("[VoiceRecorder] Initial timeout reached: no speech detected");
            this._triggerSilence();
          }
        }
      }
    };
    this._source.connect(this._processor);
    this._processor.connect(this._audioCtx.destination);
    this._isRecording = true;
    return true;
  }
  _triggerSilence() {
    if (this._silenceCallbackTriggered) return;
    this._silenceCallbackTriggered = true;
    if (this._onSilenceCallback) {
      this._onSilenceCallback();
    }
  }
  stop() {
    return new Promise((resolve) => {
      this._isRecording = false;
      try {
        this._processor?.disconnect();
        this._source?.disconnect();
        if (this._audioCtx && this._audioCtx.state !== "closed") {
          this._audioCtx.close();
        }
      } catch (err) {
        console.warn("[VoiceRecorder] cleanup error:", err);
      }
      this._stream?.getTracks().forEach((track) => track.stop());
      this._stream = null;
      this._source = null;
      this._processor = null;
      this._audioCtx = null;
      const concatenated = this._getConcatenatedSamples();
      if (concatenated.length === 0) {
        resolve(null);
        return;
      }
      const wavBuffer = this._buildWAV(concatenated);
      const wavBlob = new Blob([wavBuffer], { type: "audio/wav" });
      const reader = new FileReader();
      reader.onload = () => {
        const res = reader.result;
        resolve(res.split(",")[1]);
      };
      reader.readAsDataURL(wavBlob);
    });
  }
  clearBuffer() {
    this._samples = [];
    this._silenceStart = null;
    this._recordingStart = Date.now();
  }
  resetSpeakingState() {
    this._isSpeaking = false;
    this._hasSpoken = false;
  }
  async getWavBase64() {
    const concatenated = this._getConcatenatedSamples();
    if (concatenated.length === 0) return null;
    const wavBuffer = this._buildWAV(concatenated);
    const wavBlob = new Blob([wavBuffer], { type: "audio/wav" });
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => {
        const res = reader.result;
        resolve(res.split(",")[1]);
      };
      reader.readAsDataURL(wavBlob);
    });
  }
  get isRecording() {
    return this._isRecording;
  }
  _getConcatenatedSamples() {
    let totalLength = 0;
    for (const chunk of this._samples) {
      totalLength += chunk.length;
    }
    const result = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this._samples) {
      result.set(chunk, offset);
      offset += chunk.length;
    }
    return result;
  }
  _buildWAV(samples) {
    const targetSampleRate = 16e3;
    const numChannels = 1;
    const bitDepth = 16;
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
    view.setUint32(28, targetSampleRate * numChannels * bitDepth / 8, true);
    view.setUint16(32, numChannels * bitDepth / 8, true);
    view.setUint16(34, bitDepth, true);
    this._writeString(view, 36, "data");
    view.setUint32(40, dataLength, true);
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const sample = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(
        offset,
        sample < 0 ? sample * 32768 : sample * 32767,
        true
      );
    }
    return buffer;
  }
  _writeString(view, offset, text) {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  }
}
export {
  VoiceRecorder
};
