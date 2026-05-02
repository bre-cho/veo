import OpenAI from "openai";
import { getUserFromBearer } from "@/lib/supabase/server";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "missing" });

export async function POST(req: Request) {
  try {
    const auth = await getUserFromBearer(req);
    if (!auth.user) {
      return Response.json({ error: auth.error }, { status: 401 });
    }

    const body = await req.json();
    const prompt = String(body.prompt || "").trim();

    if (!prompt) {
      return Response.json({ error: "Prompt is required" }, { status: 400 });
    }

    if (!process.env.OPENAI_API_KEY) {
      const mockUrl = `https://dummyimage.com/1024x1024/0a0f2c/ffffff&text=${encodeURIComponent(
        prompt.slice(0, 80)
      )}`;
      return Response.json({ urls: [mockUrl], mock: true });
    }

    const response = await openai.images.generate({
      model: "gpt-image-1",
      prompt,
      size: "1024x1024"
    });

    const urls = (response.data || []).map((img) => img.url).filter(Boolean) as string[];
    return Response.json({ urls, mock: false });
  } catch (error: any) {
    return Response.json({ error: error.message || "Image generation failed" }, { status: 500 });
  }
}
