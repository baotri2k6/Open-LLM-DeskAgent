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

  // Planning/task checklist management
  private checklistContainer: HTMLDivElement | null = null;
  private pollInterval: any = null;

  public startPollingChecklist(): void {
    if (this.pollInterval) return;
    this.pollInterval = setInterval(async () => {
      try {
        const res = await (window as any).companion.invoke("ai:get-notifications", "coding");
        if (res && res.notifications && res.notifications.length > 0) {
          for (const note of res.notifications) {
            const type = note.event_type;
            const payload = note.payload;
            if (!type) continue;
            
            if (type === "PlanCreated") {
              const steps = payload?.steps ?? [];
              this.renderTaskChecklist(steps);
            } else if (type === "PlanStepStarted") {
              const idx = payload?.step_index;
              this.updateStepStatus(idx, 'in_progress');
            } else if (type === "PlanStepFinished") {
              const idx = payload?.step_index;
              const success = payload?.success;
              this.updateStepStatus(idx, success ? 'done' : 'failed');
            } else if (type === "PlanFinished") {
              const items = this.checklistContainer?.querySelectorAll(".checklist-item");
              items?.forEach(item => {
                item.className = "checklist-item done";
              });
            } else if (type === "PlanFailed") {
              const items = this.checklistContainer?.querySelectorAll(".checklist-item");
              items?.forEach(item => {
                if (!item.classList.contains("done")) {
                  item.className = "checklist-item failed";
                }
              });
            }
          }
        }
      } catch (err) {
        console.warn("[notifications] ChatUI failed to fetch coding notifications:", err);
      }
    }, 2000);
  }

  public stopPollingChecklist(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  public renderTaskChecklist(steps: any[]): void {
    if (!this.checklistContainer) {
      this.checklistContainer = document.createElement("div");
      this.checklistContainer.className = "checklist-container";
      this.checklistContainer.innerHTML = `
        <h4>Kế hoạch thực hiện:</h4>
        <ul class="checklist-list"></ul>
      `;
      // Gắn vào container chat phía trên input box/form
      this.log.parentNode?.insertBefore(this.checklistContainer, this.form);
    }
    
    const ul = this.checklistContainer.querySelector("ul");
    if (ul) {
      ul.innerHTML = "";
      steps.forEach((step, idx) => {
        const li = document.createElement("li");
        li.className = `checklist-item ${step.status || 'pending'}`;
        li.id = `chat-chk-step-${idx}`;
        li.innerHTML = `<span class="chk-status"></span> <span class="chk-desc">${step.description}</span>`;
        ul.appendChild(li);
      });
    }
    this.log.scrollTop = this.log.scrollHeight;
  }

  public updateStepStatus(idx: number, status: 'pending' | 'in_progress' | 'done' | 'failed'): void {
    const item = document.getElementById(`chat-chk-step-${idx}`);
    if (item) {
      item.className = `checklist-item ${status}`;
    }
  }
}
