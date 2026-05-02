import { getUserFromBearer } from "@/lib/supabase/server";

export async function POST(req: Request) {
  try {
    const auth = await getUserFromBearer(req);
    if (!auth.user) {
      return Response.json({ error: auth.error }, { status: 401 });
    }

    const accessToken = process.env.TIKTOK_ACCESS_TOKEN;
    if (!accessToken) {
      return Response.json({ error: "Missing TIKTOK_ACCESS_TOKEN" }, { status: 500 });
    }

    const body = await req.json();
    const videoUrl = String(body.videoUrl || "").trim();
    const caption = String(body.caption || "").trim();

    if (!videoUrl || !caption) {
      return Response.json({ error: "videoUrl and caption are required" }, { status: 400 });
    }

    const response = await fetch("https://open.tiktokapis.com/v2/post/publish/video/init/", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        post_info: {
          title: caption,
          privacy_level: "SELF_ONLY"
        },
        source_info: {
          source: "PULL_FROM_URL",
          video_url: videoUrl
        }
      })
    });

    const payload = await response.json();
    if (!response.ok) {
      return Response.json({ error: payload }, { status: response.status });
    }

    return Response.json({ result: payload });
  } catch (error: any) {
    return Response.json({ error: error.message || "TikTok post failed" }, { status: 500 });
  }
}
