import { getSupabaseServiceClient, getUserFromBearer } from "@/lib/supabase/server";

export async function GET(req: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const auth = await getUserFromBearer(req);
    if (!auth.user) {
      return Response.json({ error: auth.error }, { status: 401 });
    }

    const params = await context.params;
    const supabase = getSupabaseServiceClient();

    const { data, error } = await supabase
      .from("generation_jobs")
      .select("id,status,prompt,result_urls,error,created_at")
      .eq("id", params.id)
      .eq("user_id", auth.user.id)
      .single();

    if (error || !data) {
      return Response.json({ error: "Job not found" }, { status: 404 });
    }

    return Response.json({ job: data });
  } catch (error: any) {
    return Response.json({ error: error.message || "Get job failed" }, { status: 500 });
  }
}
