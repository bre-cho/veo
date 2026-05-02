import OpenAI from "openai";
import { getSupabaseServiceClient, getUserFromBearer } from "@/lib/supabase/server";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "missing" });

async function uploadImageToSupabase(url: string, userId: string, jobId: string, index: number) {
  const supabase = getSupabaseServiceClient();
  const bucket = process.env.SUPABASE_ASSET_BUCKET || "generated-assets";

  const imageRes = await fetch(url);
  if (!imageRes.ok) {
    throw new Error(`Failed to download generated image: ${imageRes.status}`);
  }

  const bytes = await imageRes.arrayBuffer();
  const contentType = imageRes.headers.get("content-type") || "image/png";
  const ext = contentType.includes("jpeg") ? "jpg" : "png";
  const path = `${userId}/${jobId}/asset-${index}.${ext}`;

  const { error } = await supabase.storage.from(bucket).upload(path, bytes, {
    contentType,
    upsert: true
  });

  if (error) {
    throw new Error(error.message);
  }

  const { data } = supabase.storage.from(bucket).getPublicUrl(path);
  return data.publicUrl;
}

async function generateImageUrls(prompt: string) {
  if (!process.env.OPENAI_API_KEY) {
    return [
      `https://dummyimage.com/1024x1024/111827/ffffff&text=${encodeURIComponent(prompt.slice(0, 80))}`
    ];
  }

  const response = await openai.images.generate({
    model: "gpt-image-1",
    prompt,
    size: "1024x1024"
  });

  return (response.data || []).map((img) => img.url).filter(Boolean) as string[];
}

export async function POST(req: Request) {
  try {
    const auth = await getUserFromBearer(req);
    if (!auth.user) {
      return Response.json({ error: auth.error }, { status: 401 });
    }

    const body = await req.json();
    const prompt = String(body.prompt || "").trim();
    const projectId = body.projectId ? String(body.projectId) : null;

    if (!prompt) {
      return Response.json({ error: "Prompt is required" }, { status: 400 });
    }

    const supabase = getSupabaseServiceClient();

    const { data: job, error: insertError } = await supabase
      .from("generation_jobs")
      .insert({
        user_id: auth.user.id,
        project_id: projectId,
        prompt,
        status: "queued"
      })
      .select("id")
      .single();

    if (insertError || !job) {
      throw new Error(insertError?.message || "Cannot create job");
    }

    const jobId = job.id as string;

    void (async () => {
      const supabaseInner = getSupabaseServiceClient();
      try {
        await supabaseInner.from("generation_jobs").update({ status: "processing" }).eq("id", jobId);

        const generatedUrls = await generateImageUrls(prompt);
        const uploadedUrls: string[] = [];

        for (let i = 0; i < generatedUrls.length; i += 1) {
          const uploaded = await uploadImageToSupabase(generatedUrls[i], auth.user!.id, jobId, i + 1);
          uploadedUrls.push(uploaded);
        }

        await supabaseInner
          .from("generation_jobs")
          .update({ status: "completed", result_urls: uploadedUrls, error: null })
          .eq("id", jobId);
      } catch (error: any) {
        await supabaseInner
          .from("generation_jobs")
          .update({ status: "failed", error: error.message || "Job failed" })
          .eq("id", jobId);
      }
    })();

    return Response.json({ jobId, status: "queued" });
  } catch (error: any) {
    return Response.json({ error: error.message || "Create job failed" }, { status: 500 });
  }
}
