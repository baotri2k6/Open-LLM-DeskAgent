importScripts("https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.46/dist/index.js");

const handler = new webllm.WebWorkerMLCEngineHandler();
self.onmessage = (msg) => {
  handler.onmessage(msg);
};
