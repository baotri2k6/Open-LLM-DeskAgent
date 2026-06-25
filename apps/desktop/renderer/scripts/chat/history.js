export class ChatHistory {
  constructor(limit = 40) { this._msgs = []; this._limit = limit; }
  add(role, text) {
    const msg = { id: `${role}_${Date.now()}`, role, text, ts: new Date() };
    this._msgs.push(msg);
    if (this._msgs.length > this._limit) this._msgs.shift();
    return msg;
  }
  all() { return [...this._msgs]; }
}