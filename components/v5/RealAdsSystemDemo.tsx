'use client';

import { useState } from 'react';

type Variant = any;

export function RealAdsSystemDemo() {
  const [product, setProduct] = useState('serum trị mụn');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    const res = await fetch('/api/generate-ads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product, industry: 'auto', goal: 'sale', audience: 'khách hàng Việt Nam' })
    });
    setResult(await res.json());
    setLoading(false);
  }

  async function copyPrompt(variantId: string, prompt: string) {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedId(variantId);
      setTimeout(() => setCopiedId((current) => (current === variantId ? null : current)), 1500);
    } catch {
      setCopiedId(null);
      alert('Không thể copy prompt trên trình duyệt này.');
    }
  }

  return (
    <div className="mx-auto max-w-6xl p-6 space-y-6">
      <div className="rounded-2xl border p-6 shadow-sm bg-white">
        <h1 className="text-3xl font-bold">VISUAL ENGINE — REAL ADS SYSTEM</h1>
        <p className="mt-2 text-gray-600">Nhập sản phẩm → sinh 3 ads → chấm điểm → chọn winner.</p>
        <div className="mt-4 flex gap-3">
          <input className="flex-1 rounded-xl border px-4 py-3" value={product} onChange={(e) => setProduct(e.target.value)} />
          <button onClick={run} className="rounded-xl bg-black px-5 py-3 text-white">{loading ? 'Đang chạy...' : 'Tạo ads'}</button>
        </div>
      </div>

      {result?.winner && (
        <div className="rounded-2xl border-2 border-black p-5 bg-yellow-50">
          <div className="text-sm uppercase tracking-wide">Winner đề xuất</div>
          <div className="text-2xl font-bold">{result.winner.title} — {result.winner.score.finalScore}/100</div>
          <p className="mt-2">{result.winner.hook}</p>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        {result?.variants?.map((v: Variant) => (
          <div key={v.id} className="rounded-2xl border p-4 bg-white shadow-sm">
            <div className="font-bold text-xl">{v.title}</div>
            <div className="text-sm text-gray-500">{v.mechanism}</div>
            <p className="mt-3 font-semibold">{v.hook}</p>
            <div className="mt-3 text-sm">Điểm: <b>{v.score.finalScore}</b> | CTR: {v.score.ctr} | Trust: {v.score.trust}</div>
            <pre className="mt-3 max-h-56 overflow-auto rounded-xl bg-gray-100 p-3 text-xs whitespace-pre-wrap">{v.imagePrompt}</pre>
            <button
              onClick={() => copyPrompt(v.id, v.imagePrompt)}
              className="mt-3 w-full rounded-xl border px-3 py-2"
            >
              {copiedId === v.id ? 'Đã sao chép' : 'Sao chép prompt'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
