export class AudioPlayer {
  private _onAudioElement: (el: HTMLAudioElement) => void;
  public audio: HTMLAudioElement;
  public audioContext: AudioContext | null = null;
  public analyser: AnalyserNode | null = null;
  public dataArray: Uint8Array | null = null;

  constructor({ onAudioElement }: { onAudioElement?: (el: HTMLAudioElement) => void } = {}) {
    this._onAudioElement = onAudioElement ?? (() => {});
    this.audio = new Audio();
    this.audio.crossOrigin = "anonymous";
    this._onAudioElement(this.audio);
  }

  private _resolveUrl(url: string): string {
    if (!url) return "";
    if (/^https?:\/\//i.test(url)) return url;
    return `http://127.0.0.1:8765${url.startsWith("/") ? url : `/${url}`}`;
  }

  private _initAudioContext(): void {
    if (this.audioContext) return;
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioCtx();
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

  async play(url: string, onAmplitude?: (amp: number) => void): Promise<void> {
    if (!url) return;
    
    this.audio.src = this._resolveUrl(url);
    this._initAudioContext();

    if (this.audioContext && this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }

    let animationId: number | null = null;
    if (this.analyser && onAmplitude && this.dataArray) {
      const checkVolume = () => {
        if (this.audio.paused || this.audio.ended) {
          onAmplitude(0);
          return;
        }
        if (this.analyser && this.dataArray) {
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
        }
      };

      this.audio.addEventListener("play", () => {
        checkVolume();
      }, { once: true });
    }

    await this.audio.play();

    await new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        if (animationId !== null) cancelAnimationFrame(animationId);
        if (onAmplitude) onAmplitude(0);
        this.audio.removeEventListener("ended", onEnded);
        this.audio.removeEventListener("error", onError);
      };
      const onEnded = () => {
        cleanup();
        resolve();
      };
      const onError = (e: any) => {
        cleanup();
        reject(e);
      };
      this.audio.addEventListener("ended", onEnded);
      this.audio.addEventListener("error", onError);
    });
  }

  stop(): void {
    this.audio.pause();
    this.audio.currentTime = 0;
    this.audio.dispatchEvent(new Event("ended"));
  }
}
