importScripts("https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.46/dist/index.js");

const handler = new (self as any).webllm.WebWorkerMLCEngineHandler();
self.onmessage = (msg: MessageEvent) => {
  handler.onmessage(msg);
};
