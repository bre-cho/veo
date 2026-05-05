import path from "path";
import fs from "fs/promises";

const ROOT = path.join(process.cwd(), "data", "self-learning-ai-store");
export const WINNERS = path.join(ROOT, "winner_dna.json");
export const EVENTS = path.join(ROOT, "events.json");
export const MODEL = path.join(ROOT, "weight_model.json");

export async function readJson<T>(filePath: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export async function writeJson(filePath: string, data: unknown): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");
}

export function nowTs(): number {
  return Math.floor(Date.now() / 1000);
}
