class MicListener {
  stream = null;
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return this.stream;
  }
  stop() {
    if (!this.stream) return;
    this.stream.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
}
export {
  MicListener
};
