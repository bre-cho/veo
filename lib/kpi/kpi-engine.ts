export function calculateKpi(row: {
  spend: number;
  impressions: number;
  clicks: number;
  leads: number;
  sales: number;
  revenue: number;
}) {
  return {
    ctr: row.impressions ? Number(((row.clicks / row.impressions) * 100).toFixed(2)) : 0,
    cpc: row.clicks ? Number((row.spend / row.clicks).toFixed(2)) : 0,
    cpl: row.leads ? Number((row.spend / row.leads).toFixed(2)) : 0,
    cpa: row.sales ? Number((row.spend / row.sales).toFixed(2)) : 0,
    roas: row.spend ? Number((row.revenue / row.spend).toFixed(2)) : 0,
    profit: row.revenue - row.spend
  };
}

export function optimizeFromKpi(metrics: any) {
  if (metrics.ctr < 1.5) return "Hook yếu → test viral version hoặc tăng contrast.";
  if (metrics.cpl > 50000) return "Offer/CTA yếu → test conversion version.";
  if (metrics.roas >= 2) return "Winner → scale ngân sách x2.";
  return "Tiếp tục test thêm visual + hook.";
}
