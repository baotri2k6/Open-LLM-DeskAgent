class ChatUI {
  log;
  form;
  input;
  attachBtn;
  fileInput;
  previewArea;
  previewThumb;
  _attachedImageBase64 = null;
  constructor({ log, form, input, attachBtn, fileInput, previewArea, previewThumb }) {
    this.log = log;
    this.form = form;
    this.input = input;
    this.attachBtn = attachBtn;
    this.fileInput = fileInput;
    this.previewArea = previewArea;
    this.previewThumb = previewThumb;
    this._initEvents();
  }
  _initEvents() {
    this.attachBtn?.addEventListener("click", () => {
      this.fileInput?.click();
    });
    this.fileInput?.addEventListener("change", (event) => {
      const target = event.target;
      const file = target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        this._attachedImageBase64 = e.target?.result;
        if (this.previewThumb) this.previewThumb.src = this._attachedImageBase64;
        if (this.previewArea) this.previewArea.style.display = "flex";
      };
      reader.readAsDataURL(file);
    });
  }
  clearAttachedImage() {
    this._attachedImageBase64 = null;
    if (this.fileInput) this.fileInput.value = "";
    if (this.previewArea) this.previewArea.style.display = "none";
    if (this.previewThumb) this.previewThumb.src = "";
  }
  getAttachedImage() {
    return this._attachedImageBase64;
  }
  onSubmit(callback) {
    this.form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = this.input.value.trim();
      if (!text && !this._attachedImageBase64) return;
      const imageToSend = this._attachedImageBase64;
      this.input.value = "";
      this.clearAttachedImage();
      this.setDisabled(true);
      try {
        await callback(text, imageToSend);
      } finally {
        this.setDisabled(false);
        this.input.focus();
      }
    });
  }
  setDisabled(disabled) {
    this.input.disabled = disabled;
    const submitBtn = this.form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = disabled;
  }
  appendMessage(role, text) {
    const el = document.createElement("div");
    el.className = `msg msg-${role}`;
    const header = document.createElement("div");
    header.className = "msg-header";
    header.textContent = role === "user" ? "B\u1EA1n" : "IceGirl";
    el.appendChild(header);
    const body = document.createElement("div");
    body.className = "msg-body";
    body.textContent = text;
    el.appendChild(body);
    this.log.appendChild(el);
    this.log.scrollTop = this.log.scrollHeight;
    return el;
  }
}
export {
  ChatUI
};
