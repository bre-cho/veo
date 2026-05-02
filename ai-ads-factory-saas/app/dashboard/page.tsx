"use client";

import { useEffect, useState } from "react";

type Metrics = {
  totalUsers: number;
  paidUsers: number;
  totalJobs: number;
  completedJobs: number;
  failedJobs: number;
  completionRate: number;
  totalCredits: number;
};

const emptyMetrics: Metrics = {
  totalUsers: 0,
  paidUsers: 0,
  totalJobs: 0,
  completedJobs: 0,
  failedJobs: 0,
  completionRate: 0,
  totalCredits: 0
};

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const res = await fetch("/api/metrics", { cache: "no-store" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load metrics");
        if (mounted) setMetrics(data);
      } catch (err) {
        if (mounted) setError(String(err));
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>Dashboard KPI</h1>
      <p style={{ color: "#CBD5E1" }}>Theo doi user, credits va performance cua pipeline render.</p>

      {loading && <p style={{ color: "#CBD5E1", marginTop: 20 }}>Đang tải KPI...</p>}
      {error && <p style={{ color: "#FCA5A5", marginTop: 20 }}>{error}</p>}

      {!loading && !error && (
        <section className="stack-on-mobile" style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
          <div className="card"><h3>Total Users</h3><h2>{metrics.totalUsers}</h2></div>
          <div className="card"><h3>Paid Users</h3><h2>{metrics.paidUsers}</h2></div>
          <div className="card"><h3>Total Credits</h3><h2>{metrics.totalCredits}</h2></div>
          <div className="card"><h3>Total Jobs</h3><h2>{metrics.totalJobs}</h2></div>
          <div className="card"><h3>Completed Jobs</h3><h2>{metrics.completedJobs}</h2></div>
          <div className="card"><h3>Failed Jobs</h3><h2>{metrics.failedJobs}</h2></div>
          <div className="card"><h3>Completion Rate</h3><h2>{metrics.completionRate}%</h2></div>
        </section>
      )}
    </main>
  );
}
