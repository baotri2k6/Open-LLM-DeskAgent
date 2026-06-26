/**
 * lipsync.js — Lipsync dựa trên Web Audio API amplitude analysis.
 *
 * Khi TTS audio phát, phân tích amplitude realtime và truyền
 * giá trị 0-1 vào callback để avatar controller điều khiển miệng.
 */

export class LipSyncController {
  constructor(onAmplitude) {
    /** @type {(amp: number) => void} */
    this._onAmplitude = onAmplitude ?? (() => {});
    this._ctx = null;
    this._analyser = null;
    this._source = null;
    this._rafId = null;
    this._active = false;
  }

  /**
   * Bắt đầu theo dõi amplitude từ HTMLAudioElement.
   * @param {HTMLAudioElement} audioEl
   */
  attachToAudio(audioEl) {
    this._detach();

    try {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      this._analyser = this._ctx.createAnalyser();
      this._analyser.fftSize = 256;
      this._analyser.smoothingTimeConstant = 0.7;

      this._source = this._ctx.createMediaElementSource(audioEl);
      this._source.connect(this._analyser);
      this._analyser.connect(this._ctx.destination);

      audioEl.addEventListener('play', () => this._startLoop(), { once: false });
      audioEl.addEventListener('pause', () => this._stopLoop(), { once: false });
      audioEl.addEventListener('ended', () => this._stopLoop(), { once: false });

      if (!audioEl.paused) this._startLoop();
    } catch (err) {
      console.warn('[LipSync] Web Audio API unavailable:', err);
      // Fallback: oscillate manually when audio plays
      audioEl.addEventListener('play', () => this._startFallback(), { once: false });
      audioEl.addEventListener('pause', () => this._stopFallback(), { once: false });
      audioEl.addEventListener('ended', () => this._stopFallback(), { once: false });
    }
  }

  _startLoop() {
    if (this._rafId) return;
    this._active = true;
    const data = new Uint8Array(this._analyser?.frequencyBinCount ?? 0);
    let smoothedAmp = 0;
    const SMOOTH = 0.6; // 0 = giật, 1 = không cử động

    const tick = () => {
      if (!this._active) return;
      if (this._analyser) {
        this._analyser.getByteFrequencyData(data);
        // RMS of low-mid frequencies (voice range ~80-3000 Hz)
        const slice = data.slice(2, 30);
        let sum = 0;
        for (const v of slice) sum += v * v;
        const rms = Math.sqrt(sum / slice.length) / 255;
        smoothedAmp = smoothedAmp * SMOOTH + rms * (1 - SMOOTH);
        this._onAmplitude(Math.min(1, smoothedAmp * 2.5));
      }
      this._rafId = requestAnimationFrame(tick);
    };
    this._rafId = requestAnimationFrame(tick);
  }

  _stopLoop() {
    this._active = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
    this._onAmplitude(0);
  }

  // Fallback nếu không có Web Audio API
  _fallbackInterval = null;
  _phase = 0;

  _startFallback() {
    if (this._fallbackInterval) return;
    this._fallbackInterval = setInterval(() => {
      this._phase += 0.5;
      const amp = 0.3 + 0.7 * Math.abs(Math.sin(this._phase));
      this._onAmplitude(amp);
    }, 50);
  }

  _stopFallback() {
    if (this._fallbackInterval) {
      clearInterval(this._fallbackInterval);
      this._fallbackInterval = null;
    }
    this._onAmplitude(0);
  }

  _detach() {
    this._stopLoop();
    this._stopFallback();
    if (this._source) {
      try { this._source.disconnect(); } catch { /* ignore */ }
      this._source = null;
    }
    if (this._ctx) {
      try { this._ctx.close(); } catch { /* ignore */ }
      this._ctx = null;
    }
  }

  destroy() {
    this._detach();
  }
}