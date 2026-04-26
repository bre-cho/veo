# 04 — Frontend Factory Command Center Guide

## Mục tiêu

Trang `/factory` phải trở thành **bảng điều khiển nhà máy**, không chỉ là timeline.

## Component cần có

```txt
frontend/src/components/factory/FactoryArtifactPanel.tsx
frontend/src/components/factory/FactoryQAPanel.tsx
frontend/src/components/factory/FactorySEOPanel.tsx
frontend/src/components/factory/FactoryPublishPanel.tsx
frontend/src/components/factory/FactoryIncidentPanel.tsx
frontend/src/components/factory/FactoryMemoryPanel.tsx
```

Nếu repo đã có component tương tự, sửa component hiện có, không tạo trùng.

---

## 1. FactoryArtifactPanel

Hiển thị:

```txt
video_url
render_job_id
manifest_scene_count
estimated_duration_seconds
artifact_validation.ok
issues
warnings
```

Skeleton:

```tsx
export function FactoryArtifactPanel({ run }: { run: any }) {
  const executeStage = run?.stages?.find((s: any) => s.stage_name === "EXECUTE_RENDER");
  const output = executeStage?.output || executeStage?.output_summary || {};
  const validation = output?.artifact_validation || {};

  return (
    <section className="rounded-2xl border p-4">
      <h2 className="text-lg font-semibold">Artifact render</h2>
      <p>Mã render: {output.render_job_id || "Chưa có"}</p>
      <p>Trạng thái artifact: {validation.ok ? "Hợp lệ" : "Chưa hợp lệ"}</p>
      {validation.issues?.length ? (
        <ul>{validation.issues.map((x: string) => <li key={x}>{x}</li>)}</ul>
      ) : null}
    </section>
  );
}
```

Sau đó đưa text vào i18n.

---

## 2. FactoryQAPanel

Hiển thị:

```txt
qa_passed
issues
warnings
scene_count
subtitle_count
total_duration_seconds
retry_strategy
```

---

## 3. FactorySEOPanel

Hiển thị:

```txt
title
description
tags
hashtags_video
hashtags_channel
```

---

## 4. FactoryPublishPanel

Phải có:

```txt
status: dry_run | blocked_pending_approval | approved_publish_ready | published
requires_approval
button approve_publish
button publish_live nếu đã approve
```

API cần gọi:

```txt
POST /api/v1/factory/runs/{run_id}/approve_publish
POST /api/v1/factory/runs/{run_id}/publish
```

---

## 5. Vietnamese hard lock

Tất cả UI text mặc định phải là tiếng Việt.

Không để hardcoded English kiểu:

```txt
Loading
Error
Approve
Retry
Publish
Render job
Unknown error
```

Đưa vào:

```txt
frontend/src/i18n/vi.ts
frontend/src/i18n/en.ts
```

Ví dụ key:

```ts
factory.artifact.title = "Artifact render"
factory.qa.title = "Kiểm định chất lượng"
factory.publish.approve = "Phê duyệt xuất bản"
factory.publish.dryRun = "Chế độ nháp"
factory.incident.title = "Sự cố"
factory.memory.title = "Bộ nhớ học được"
```

## Frontend pass criteria

```bash
cd frontend
npm run typecheck
```

và:

```bash
python scripts/ci/check_frontend_i18n.py
```


## Bổ sung bắt buộc: Việt hóa 100% giao diện

Xem chi tiết trong `08_FRONTEND_100_PERCENT_VIETNAMESE_PATCH.md`. Mọi text hiển thị cho người dùng phải đi qua `useT()` và dictionary `vi.ts`; production mặc định tiếng Việt, CI fail nếu còn hardcoded English user-facing.
