import { NextResponse } from "next/server";
import { listDeployAuditLogs } from "@/lib/v7/audit";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const limit = Math.max(1, Math.min(200, Number(url.searchParams.get("limit") || 50)));
    const campaignId = url.searchParams.get("campaign_id")?.trim() || null;
    const action = url.searchParams.get("action")?.trim() || null;
    const status = url.searchParams.get("status")?.trim() || null;
    const platform = url.searchParams.get("platform")?.trim() || null;
    const logs = await listDeployAuditLogs(limit);
    const filteredLogs = logs.filter((log: any) => {
      if (campaignId && String(log.campaign_id || "") !== campaignId) {
        return false;
      }
      if (action && String(log.action || "") !== action) {
        return false;
      }
      if (status && String(log.status || "") !== status) {
        return false;
      }
      if (platform) {
        const platforms = String(log.platform || "")
          .split(",")
          .map((entry) => entry.trim());

        if (!platforms.includes(platform)) {
          return false;
        }
      }
      return true;
    });
    return NextResponse.json({ ok: true, logs: filteredLogs });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || "Cannot load audit logs" }, { status: 500 });
  }
}