/**
 * WAV recorder based on Web Audio API (AudioContext + ScriptProcessorNode).
 * Outputs: base64 PCM16 mono WAV at 16 kHz, suitable for Whisper.
 * Includes Adaptive VAD (moving average Noise Floor) and End-of-Utterance (EoU) detection.
 */
export class VoiceRecorder {
  constructor() {
    this._stream = null;
    this._audioCtx = null;
    this._source = null;
    this._processor = null;
    this._samples = [];
    this._isRecording = false;

    // VAD & EoU Configuration
    this._noiseFloor = 0.015;
    this._minThreshold = 0.012;
    this._maxThreshold = 0.08;
    this._margin = 0.012;
    
    this._hasSpoken = false;
    this._isSpeaking = false;
    this._silenceStart = null;
    this._recordingStart = 0;
    this._silenceCallbackTriggered = false;
    
    // Callbacks
    this._onSilenceCallback = null;
    this.onSpeechStartCallback = null;
    
    // Settings
    this.initialTimeoutMs = 6000; // Auto-cancel if no speech in 6s
    this.lastDraftText = "";
  }

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

    // Web Audio API setup with dynamic resampling to 16000 Hz
    this._stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this._audioCtx = new AudioContextClass({ sampleRate: 16000 });
    this._source = this._audioCtx.createMediaStreamSource(this._stream);
    this._processor = this._audioCtx.createScriptProcessor(4096, 1, 1);

    this._processor.onaudioprocess = (e) => {
      if (!this._isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);

      // Store samples
      const chunk = new Float32Array(inputData.length);
      chunk.set(inputData);
      this._samples.push(chunk);

      // RMS calculation
      let sum = 0;
      for (let i = 0; i < inputData.length; i++) {
        sum += inputData[i] * inputData[i];
      }
      const rms = Math.sqrt(sum / inputData.length);

      // Adaptive Noise Floor update (only if not active speech)
      if (rms < this._noiseFloor * 1.5 || rms < 0.02) {
        this._noiseFloor = this._noiseFloor * 0.95 + rms * 0.05;
      }

      // Compute dynamic threshold
      const threshold = Math.max(
        this._minThreshold,
        Math.min(this._maxThreshold, this._noiseFloor + this._margin)
      );

      // Voice Activity Detection (VAD)
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
        
        // Silence detection
        if (this._hasSpoken) {
          if (this._silenceStart === null) {
            this._silenceStart = Date.now();
          } else {
            const silenceMs = Date.now() - this._silenceStart;
            
            // End-of-Utterance (EoU) Detection
            const text = (this.lastDraftText || "").trim();
            const endsWithPunctuation = /[.!?]$/.test(text);
            const requiredSilenceMs = endsWithPunctuation ? 600 : 1500;

            if (silenceMs >= requiredSilenceMs) {
              this._triggerSilence();
            }
          }
        } else {
          // Initial timeout if no speech started yet
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

      // Disconnect and clean up Audio Nodes
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

      // Concatenate all float samples
      const concatenated = this._getConcatenatedSamples();
      if (concatenated.length === 0) {
        resolve(null);
        return;
      }

      const wavBuffer = this._buildWAV(concatenated);
      const wavBlob = new Blob([wavBuffer], { type: "audio/wav" });
      
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(",")[1]);
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
      reader.onload = () => resolve(reader.result.split(",")[1]);
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
    const targetSampleRate = 16000;
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
}
