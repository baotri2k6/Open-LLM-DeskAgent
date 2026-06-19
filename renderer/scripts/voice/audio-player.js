export class AudioPlayer {
  constructor({ onAudioElement } = {}) {
    this._onAudioElement = onAudioElement ?? (() => {});
    this.audio = new Audio();
    this.audio.crossOrigin = "anonymous";
    this.audioContext = null;
    this.analyser = null;
    this.dataArray = null;
  }

  _resolveUrl(url) {
    if (!url) return "";
    if (/^https?:\/\//i.test(url)) return url;
    return `http://127.0.0.1:8765${url.startsWith("/") ? url : `/${url}`}`;
  }

  _initAudioContext() {
    if (this.audioContext) return;
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      const source = this.audioContext.createMediaElementSource(this.audio);
      source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    } catch (err) {
      console.warn("Failed to initialize Web Audio context:", err);
    }
  }

  async play(url, onAmplitude) {
    if (!url) return;
    
    this.audio.src = this._resolveUrl(url);
    this._initAudioContext();

    if (this.audioContext && this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }

    let animationId = null;
    if (this.analyser && onAmplitude) {
      const checkVolume = () => {
        if (this.audio.paused || this.audio.ended) {
          onAmplitude(0);
          return;
        }
        this.analyser.getByteTimeDomainData(this.dataArray);
        let sum = 0;
        const len = this.dataArray.length;
        for (let i = 0; i < len; i++) {
          const v = (this.dataArray[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / len);
        const amplitude = Math.min(1.0, rms * 4.0);
        onAmplitude(amplitude);
        animationId = requestAnimationFrame(checkVolume);
      };

      this.audio.addEventListener("play", () => {
        checkVolume();
      }, { once: true });
    }

    await this.audio.play();

    await new Promise((resolve, reject) => {
      const cleanup = () => {
        if (animationId) cancelAnimationFrame(animationId);
        if (onAmplitude) onAmplitude(0);
        this.audio.removeEventListener("ended", onEnded);
        this.audio.removeEventListener("error", onError);
      };
      const onEnded = () => {
        cleanup();
        resolve();
      };
      const onError = (e) => {
        cleanup();
        reject(e);
      };
      this.audio.addEventListener("ended", onEnded);
      this.audio.addEventListener("error", onError);
    });
  }
}
