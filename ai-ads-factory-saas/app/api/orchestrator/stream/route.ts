import OpenAI from "openai";
import { agents } from "@/lib/agents/prompts";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "missing" });
export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: Request) {
  const input = await req.json();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let context = "INPUT:\n" + JSON.stringify(input, null, 2);

      for (const agent of agents) {
        controller.enqueue(encoder.encode("event: agent_start\ndata: " + JSON.stringify({ agent: agent.name }) + "\n\n"));

        let output = "";
        if (!process.env.OPENAI_API_KEY) {
          output = `## ${agent.name}\nMock output cho ${input.product}. Thêm OPENAI_API_KEY để chạy agent thật.\nCTA: Nhận demo miễn phí.`;
        } else {
          try {
            const completion = await openai.chat.completions.create({
              model: "gpt-4.1-mini",
              messages: [
                { role: "system", content: `Bạn là ${agent.name}. Conversion > đẹp. Ít chữ. Luôn có CTA. Chuẩn Unicode tiếng Việt.` },
                { role: "user", content: agent.prompt + "\n\nContext:\n" + context }
              ]
            });
            output = completion.choices[0]?.message?.content || "";
          } catch (error) {
            output = `## ${agent.name}\nOpenAI call failed: ${String(error)}\nFallback CTA: Nhận demo miễn phí.`;
          }
        }

        context += "\n\n## " + agent.name + "\n" + output;
        controller.enqueue(encoder.encode("event: agent_done\ndata: " + JSON.stringify({ agent: agent.name, output }) + "\n\n"));
      }

      controller.enqueue(encoder.encode("event: done\ndata: {}\n\n"));
      controller.close();
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive"
    }
  });
}
