import { PGlite } from "https://esm.sh/@electric-sql/pglite";
import { pipeline } from "https://esm.sh/@huggingface/transformers";

let db: PGlite | null = null;
let extractor: any = null;

async function getDB(): Promise<PGlite> {
  if (db) return db;
  db = new PGlite();
  
  await db.exec(`
    CREATE TABLE IF NOT EXISTS memories (
      id SERIAL PRIMARY KEY,
      content TEXT UNIQUE NOT NULL,
      embedding TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);
  
  return db;
}

async function getExtractor(onProgress: ((prog: number) => void) | null = null): Promise<any> {
  if (extractor) return extractor;
  
  extractor = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", {
    progress_callback: (info: any) => {
      if (onProgress && info.status === "progress") {
        onProgress(info.progress);
      }
    }
  });
  
  return extractor;
}

function cosineSimilarity(a: number[], b: number[]): number {
  let dotProduct = 0;
  let mA = 0;
  let mB = 0;
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    mA += a[i] * a[i];
    mB += b[i] * b[i];
  }
  if (mA === 0 || mB === 0) return 0;
  return dotProduct / (Math.sqrt(mA) * Math.sqrt(mB));
}

export const LocalDB = {
  async init(onProgress: ((prog: number) => void) | null = null): Promise<boolean> {
    try {
      await getDB();
      await getExtractor(onProgress);
      console.log("[LocalDB] Initialized successfully");
      
      await this.syncFromBackend();
      return true;
    } catch (err) {
      console.error("[LocalDB] Failed to initialize:", err);
      return false;
    }
  },

  async addMemory(text: string): Promise<number | null> {
    try {
      const database = await getDB();
      const extract = await getExtractor();
      
      const checkRes = await database.query("SELECT id FROM memories WHERE content = $1", [text]);
      if (checkRes.rows.length > 0) {
        return (checkRes.rows[0] as any).id;
      }
      
      const output = await extract(text, { pooling: "mean", normalize: true });
      const embeddingArray = Array.from(output.data) as number[];
      
      const res = await database.query(
        "INSERT INTO memories (content, embedding) VALUES ($1, $2) RETURNING id",
        [text, JSON.stringify(embeddingArray)]
      );
      
      console.log("[LocalDB] Added memory:", text);
      return (res.rows[0] as any).id;
    } catch (err) {
      console.error("[LocalDB] Error adding memory:", err);
      return null;
    }
  },

  async deleteMemory(id: number): Promise<boolean> {
    try {
      const database = await getDB();
      await database.query("DELETE FROM memories WHERE id = $1", [id]);
      console.log("[LocalDB] Deleted memory id:", id);
      return true;
    } catch (err) {
      console.error("[LocalDB] Error deleting memory:", err);
      return false;
    }
  },

  async searchMemories(queryText: string, limit: number = 5): Promise<any[]> {
    try {
      const database = await getDB();
      const extract = await getExtractor();
      
      const allMemories = await database.query("SELECT id, content, embedding FROM memories");
      if (allMemories.rows.length === 0) return [];
      
      const output = await extract(queryText, { pooling: "mean", normalize: true });
      const queryEmbedding = Array.from(output.data) as number[];
      
      const results = allMemories.rows.map((row: any) => {
        const itemEmbedding = JSON.parse(row.embedding) as number[];
        const similarity = cosineSimilarity(queryEmbedding, itemEmbedding);
        return {
          id: row.id,
          text: row.content,
          similarity
        };
      });
      
      return results
        .filter(r => r.similarity >= 0.4)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, limit);
        
    } catch (err) {
      console.error("[LocalDB] Error searching memories:", err);
      return [];
    }
  },
  
  async syncFromBackend(): Promise<void> {
    try {
      const backendMemories = await (window as any).companion.invoke("ai:get-memories", {});
      if (backendMemories && backendMemories.memories) {
        console.log(`[LocalDB] Syncing ${backendMemories.memories.length} memories from backend...`);
        for (const mem of backendMemories.memories) {
          const text = mem.text || mem.content;
          if (text) {
            await this.addMemory(text);
          }
        }
        console.log("[LocalDB] Backend memories synchronized");
      }
    } catch (err) {
      console.warn("[LocalDB] Failed to sync from backend:", err);
    }
  }
};
