export interface ChatUIOptions {
  log: HTMLElement;
  form: HTMLFormElement;
  input: HTMLInputElement;
  attachBtn?: HTMLElement;
  fileInput?: HTMLInputElement;
  previewArea?: HTMLElement;
  previewThumb?: HTMLImageElement;
}

export class ChatUI {
  private log: HTMLElement;
  private form: HTMLFormElement;
  private input: HTMLInputElement;
  private attachBtn?: HTMLElement;
  private fileInput?: HTMLInputElement;
  private previewArea?: HTMLElement;
  private previewThumb?: HTMLImageElement;
  private _attachedImageBase64: string | null = null;

  constructor({ log, form, input, attachBtn, fileInput, previewArea, previewThumb }: ChatUIOptions) {
    this.log = log;
    this.form = form;
    this.input = input;
    this.attachBtn = attachBtn;
    this.fileInput = fileInput;
    this.previewArea = previewArea;
    this.previewThumb = previewThumb;
    this._initEvents();
  }

  private _initEvents(): void {
    this.attachBtn?.addEventListener("click", () => {
      this.fileInput?.click();
    });

    this.fileInput?.addEventListener("change", (event: Event) => {
      const target = event.target as HTMLInputElement;
      const file = target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e: ProgressEvent<FileReader>) => {
        this._attachedImageBase64 = e.target?.result as string;
        if (this.previewThumb) this.previewThumb.src = this._attachedImageBase64;
        if (this.previewArea) this.previewArea.style.display = "flex";
      };
      reader.readAsDataURL(file);
    });
  }

  public clearAttachedImage(): void {
    this._attachedImageBase64 = null;
    if (this.fileInput) this.fileInput.value = "";
    if (this.previewArea) this.previewArea.style.display = "none";
    if (this.previewThumb) this.previewThumb.src = "";
  }

  public getAttachedImage(): string | null {
    return this._attachedImageBase64;
  }

  public onSubmit(callback: (text: string, image?: string | null) => Promise<void> | void): void {
    this.form.addEventListener('submit', async (event: Event) => {
      event.preventDefault();
      const text = this.input.value.trim();
      if (!text && !this._attachedImageBase64) return;
      
      const imageToSend = this._attachedImageBase64;
      this.input.value = '';
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

  public setDisabled(disabled: boolean): void {
    this.input.disabled = disabled;
    const submitBtn = this.form.querySelector('button[type="submit"]') as HTMLButtonElement | null;
    if (submitBtn) submitBtn.disabled = disabled;
  }

  public appendMessage(role: string, text: string): HTMLDivElement {
    const el = document.createElement("div");
    el.className = `msg msg-${role}`;
    
    const header = document.createElement("div");
    header.className = "msg-header";
    header.textContent = role === "user" ? "Bạn" : "IceGirl";
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
