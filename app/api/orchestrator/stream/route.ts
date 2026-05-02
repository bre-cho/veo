import OpenAI from "openai";
import { agents } from "@/lib/agents/prompts";
import { getUserFromBearer } from "@/lib/supabase/server";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "missing" });

export async function POST(req: Request) {
  const auth = await getUserFromBearer(req);
  if (!auth.user) {
    return Response.json({ error: auth.error }, { status: 401 });
  }

  const input = await req.json();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let context = "INPUT:\n" + JSON.stringify(input, null, 2);

      for (const agent of agents) {
        controller.enqueue(
          encoder.encode("event: agent_start\ndata: " + JSON.stringify({ agent: agent.name }) + "\n\n")
        );

        let output = "";

        if (!process.env.OPENAI_API_KEY) {
          output = mockOutput(agent.name, input);
        } else {
          const completion = await openai.chat.completions.create({
            model: "gpt-4.1-mini",
            messages: [
              {
                role: "system",
                content: `
Bạn là ${agent.name}.
Nguyên tắc:
- Conversion > đẹp
- Ít chữ, rõ thông điệp
- Luôn có CTA
- Không dùng thương hiệu/bản quyền chưa được phép
- Chuẩn tiếng Việt Unicode
`
              },
              {
                role: "user",
                content: agent.prompt + "\n\nContext trước đó:\n" + context
              }
            ]
          });

          output = completion.choices[0]?.message?.content || "";
        }

        context += "\n\n## " + agent.name + "\n" + output;

        controller.enqueue(
          encoder.encode("event: agent_done\ndata: " + JSON.stringify({ agent: agent.name, output }) + "\n\n")
        );
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

function mockOutput(agent: string, input: any) {
  return `## ${agent}

Sản phẩm: ${input.product || "AI Design Tool"}

- Insight: khách muốn tạo ads nhanh, đẹp, có chuyển đổi.
- Big idea: biến 1 ý tưởng thành ads bán hàng trong 60 giây.
- Hook: Bạn đang đốt tiền ads mà không có khách?
- CTA: Nhận demo miễn phí.
- Ghi chú: Đây là mock output. Thêm OPENAI_API_KEY để chạy agent thật.`;
}
