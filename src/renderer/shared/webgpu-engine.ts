import { CreateWebWorkerMLCEngine } from "https://esm.sh/@mlc-ai/web-llm";

let engine: any = null;
const SELECTED_MODEL = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC";

export const WebGPUEngine = {
  isInitialized(): boolean {
    return engine !== null;
  },

  async init(onProgress: ((text: string, progress: number) => void) | null = null): Promise<boolean> {
    if (engine) return true;

    try {
      console.log("[WebGPU] Initializing WebWorkerMLCEngine...");
      const worker = new Worker(new URL("./webgpu-worker.js", import.meta.url));
      
      engine = await CreateWebWorkerMLCEngine(
        worker,
        SELECTED_MODEL,
        {
          initProgressCallback: (report: any) => {
            console.log("[WebGPU Progress]", report.text);
            if (onProgress) {
              const match = report.text.match(/(\d+)%/);
              const progressVal = match ? parseInt(match[1]) / 100 : 0;
              onProgress(report.text, progressVal);
            }
          }
        }
      );
      console.log("[WebGPU] Model loaded and engine initialized successfully");
      return true;
    } catch (err) {
      console.error("[WebGPU] Failed to initialize:", err);
      engine = null;
      throw err;
    }
  },

  async chat(messages: any[], onChunk: ((text: string) => void) | null = null): Promise<string> {
    if (!engine) {
      throw new Error("WebGPU engine not initialized. Please call init() first.");
    }

    try {
      console.log("[WebGPU] Generating response...");
      const responseStream = await engine.chat.completions.create({
        messages,
        stream: true
      });

      let fullText = "";
      for await (const chunk of responseStream) {
        const text = chunk.choices[0]?.delta?.content || "";
        if (text) {
          fullText += text;
          if (onChunk) {
            onChunk(text);
          }
        }
      }
      return fullText;
    } catch (err) {
      console.error("[WebGPU] Error in chat completion:", err);
      throw err;
    }
  }
};
