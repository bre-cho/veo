import { getUserFromBearer } from "@/lib/supabase/server";

export async function POST(req: Request) {
  try {
    const auth = await getUserFromBearer(req);
    if (!auth.user) {
      return Response.json({ error: auth.error }, { status: 401 });
    }

    const accessToken = process.env.TIKTOK_ACCESS_TOKEN;
    const advertiserId = process.env.TIKTOK_ADVERTISER_ID;

    if (!accessToken || !advertiserId) {
      return Response.json({ error: "Missing TIKTOK_ACCESS_TOKEN or TIKTOK_ADVERTISER_ID" }, { status: 500 });
    }

    const body = await req.json();
    const name = String(body.name || "AI Ads Campaign");
    const objectiveType = String(body.objectiveType || "CONVERSIONS");
    const budget = Number(body.budget || 500000);

    const response = await fetch("https://business-api.tiktok.com/open_api/v1.3/campaign/create/", {
      method: "POST",
      headers: {
        "Access-Token": accessToken,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        advertiser_id: advertiserId,
        campaign_name: name,
        objective_type: objectiveType,
        budget_mode: "BUDGET_MODE_DAY",
        budget
      })
    });

    const payload = await response.json();
    if (!response.ok || payload.code !== 0) {
      return Response.json({ error: payload }, { status: 400 });
    }

    return Response.json({ result: payload.data });
  } catch (error: any) {
    return Response.json({ error: error.message || "Create TikTok campaign failed" }, { status: 500 });
  }
}
