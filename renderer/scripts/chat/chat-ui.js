export class ChatUI {
  constructor({ log, form, input }) {
    this.log = log;
    this.form = form;
    this.input = input;
  }

  onSubmit(callback) {
    this.form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const text = this.input.value.trim();
      if (!text) return;
      this.input.value = '';
      this.input.disabled = true;
      try {
        await callback(text);
      } finally {
        this.input.disabled = false;
        this.input.focus();
      }
    });
  }

  append(element) {
    this.log.appendChild(element);
    this.log.scrollTop = this.log.scrollHeight;
  }
}
