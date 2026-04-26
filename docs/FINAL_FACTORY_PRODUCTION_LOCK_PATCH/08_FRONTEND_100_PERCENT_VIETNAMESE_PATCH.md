# 08 — FRONTEND 100% VIETNAMESE PATCH

## Mục tiêu

Khóa toàn bộ giao diện frontend về tiếng Việt, không để hardcoded English quay lại sau khi merge patch.

Luật production:

```txt
DEFAULT UI LANGUAGE = vi
NO HARDCODED ENGLISH IN JSX
NO USER-FACING STRING OUTSIDE i18n DICTIONARY
NO PRODUCTION BUILD IF i18n GUARD FAILS
```

---

## Phạm vi bắt buộc quét

Áp dụng cho toàn bộ:

```txt
frontend/src/app/**/*.tsx
frontend/src/components/**/*.tsx
frontend/src/hooks/**/*.ts
frontend/src/lib/**/*.ts
frontend/src/store/**/*.tsx
```

Ngoại lệ hợp lệ:

```txt
className
ARIA technical key nếu không hiển thị
API method: GET / POST / PATCH / DELETE
URL/env key
CSS token
provider/model id
log/debug chỉ dành cho developer
```

---

## File cần sửa chính

### App pages

```txt
frontend/src/app/page.tsx
frontend/src/app/error.tsx
frontend/src/app/not-found.tsx
frontend/src/app/layout.tsx
frontend/src/app/analytics/page.tsx
frontend/src/app/audio/page.tsx
frontend/src/app/autopilot/page.tsx
frontend/src/app/avatar-builder/page.tsx
frontend/src/app/dashboard/page.tsx
frontend/src/app/factory/page.tsx
frontend/src/app/marketplace/page.tsx
frontend/src/app/production-studio/page.tsx
frontend/src/app/projects/page.tsx
frontend/src/app/projects/[id]/page.tsx
frontend/src/app/render-jobs/page.tsx
frontend/src/app/render-jobs/[jobId]/page.tsx
frontend/src/app/script-upload/page.tsx
frontend/src/app/settings/page.tsx
frontend/src/app/strategy/page.tsx
frontend/src/app/templates/page.tsx
frontend/src/app/wallet/page.tsx
```

### Components

```txt
frontend/src/components/Sidebar.tsx
frontend/src/components/DashboardShell.tsx
frontend/src/components/IncidentDrawer.tsx
frontend/src/components/PreviewEditingLayer.tsx
frontend/src/components/RealtimeProgressUI.tsx
frontend/src/components/RebuildDecisionPanel.tsx
frontend/src/components/ScriptUploadPreviewFlow.tsx
frontend/src/components/ToastViewport.tsx
frontend/src/components/ValidationPanel.tsx
frontend/src/components/avatar-builder/*.tsx
frontend/src/components/creator/*.tsx
frontend/src/components/factory/*.tsx
frontend/src/components/marketplace/*.tsx
frontend/src/components/shared/*.tsx
frontend/src/components/strategy/*.tsx
frontend/src/components/templates/*.tsx
```

---

## Kiến trúc i18n chuẩn

### 1. Dictionary

Giữ cấu trúc:

```txt
frontend/src/i18n/vi.ts
frontend/src/i18n/en.ts
frontend/src/i18n/useT.ts
```

Bổ sung namespace đầy đủ:

```ts
export const vi = {
  common: {
    loading: "Đang tải",
    load: "Tải",
    save: "Lưu",
    saving: "Đang lưu…",
    cancel: "Hủy",
    close: "Đóng",
    apply: "Áp dụng",
    edit: "Sửa",
    delete: "Xóa",
    retry: "Thử lại",
    approve: "Phê duyệt",
    reject: "Từ chối",
    unknownError: "Lỗi không xác định",
    createdSuccessfully: "Đã tạo thành công",
    failed: "Thất bại",
    status: "Trạng thái",
    score: "Điểm",
    action: "Hành động",
    mode: "Chế độ",
  },
  nav: {
    dashboard: "Bảng điều khiển",
    factory: "Nhà máy video AI",
    projects: "Dự án",
    renderJobs: "Hàng chờ render",
    scriptUpload: "Tải kịch bản",
    audio: "Xưởng âm thanh",
    avatarBuilder: "Tạo Avatar",
    marketplace: "Chợ Avatar",
    analytics: "Phân tích",
    wallet: "Ví tiền",
    settings: "Cài đặt",
    strategy: "Chiến lược",
    templates: "Mẫu dựng video",
  },
  factory: {
    title: "Nhà máy video AI",
    subtitle: "Vận hành khép kín từ ý tưởng đến xuất bản.",
    runDetailLoading: "Đang tải chi tiết phiên chạy",
    stageTimeline: "Tiến trình các công đoạn",
    qualityGate: "Cổng kiểm chất lượng",
    memory: "Bộ nhớ học lại",
    renderJob: "Job render",
    seoPackage: "Gói SEO",
    publishPayload: "Gói xuất bản",
    approvePublish: "Phê duyệt xuất bản",
    retryStage: "Chạy lại công đoạn",
    cancelRun: "Hủy phiên chạy",
    artifactPreview: "Xem trước artifact",
    blocked: "Đã chặn",
    dryRun: "Chạy thử",
    livePublish: "Xuất bản thật",
  },
  render: {
    realtimeProgress: "Tiến trình thời gian thực",
    decisionFailed: "Không tạo được quyết định render",
    approveFailed: "Phê duyệt thất bại",
    rebuildReason: "Lý do dựng lại",
    selectedStrategy: "Chiến lược đã chọn",
    estimatedCost: "Chi phí ước tính",
    estimatedTime: "Thời gian ước tính",
    affectedScenes: "Cảnh bị ảnh hưởng",
  },
  preview: {
    sceneEditor: "Trình sửa cảnh",
    subtitleEditor: "Trình sửa phụ đề",
    deleteScene: "Xóa cảnh",
    deleteSubtitle: "Xóa phụ đề",
    validateFailed: "Không kiểm tra được bản xem trước",
    rebuildSubtitleFailed: "Không dựng lại được phụ đề",
    durationRecalculateFailed: "Không tính lại được thời lượng",
    previewRecalculateFailed: "Không tính lại được bản xem trước",
  },
  scriptUpload: {
    selectTxtOrDocx: "Vui lòng chọn file .txt hoặc .docx",
    uploadFailed: "Tải lên thất bại",
    validationErrors: "Bản xem trước có lỗi. Vui lòng sửa trước khi tạo dự án.",
    projectCreated: "Dự án đã được tạo thành công!",
    createdProject: "Dự án đã tạo",
  },
  avatar: {
    identity: "Danh tính",
    visual: "Hình ảnh",
    voice: "Giọng nói",
    motion: "Chuyển động",
    preview: "Xem trước",
    avatarName: "Tên Avatar",
    role: "Vai trò",
    niche: "Ngách nội dung",
    market: "Thị trường",
    skinTone: "Tông da",
    hairStyle: "Kiểu tóc",
    outfit: "Trang phục",
    background: "Bối cảnh",
    ageRange: "Độ tuổi",
    genderExpression: "Biểu đạt giới tính",
    accent: "Giọng vùng miền",
    tone: "Sắc thái giọng",
    pitch: "Cao độ",
    speed: "Tốc độ",
    gestureSet: "Bộ cử chỉ",
    idleAnimation: "Chuyển động chờ",
    lipsyncMode: "Chế độ khớp môi",
    draftNotPublished: "Bản nháp — chưa xuất bản",
    published: "Đã xuất bản",
    publish: "Xuất bản",
    publishing: "Đang xuất bản…",
    draftSaved: "Đã lưu bản nháp",
  },
  audio: {
    title: "Xưởng âm thanh",
    voiceProfile: "Hồ sơ giọng nói",
    backgroundMusic: "Nhạc nền",
    generateNarration: "Tạo lời dẫn",
  },
  marketplace: {
    title: "Chợ Avatar",
    searchPlaceholder: "Tìm Avatar…",
    trendingAvatars: "Avatar thịnh hành",
    recommendedAvatars: "Avatar gợi ý",
    free: "Miễn phí",
    selectMarket: "Chọn thị trường",
  },
  creator: {
    totalAvatars: "Tổng số Avatar",
    amountUsd: "Số tiền (USD)",
    requestPayout: "Yêu cầu rút tiền",
    requesting: "Đang gửi yêu cầu…",
    payoutRequested: "Đã gửi yêu cầu rút tiền ✓",
  },
  templates: {
    scheduledAt: "Thời điểm lên lịch (ISO datetime)",
    executionWindowStart: "Bắt đầu khung thực thi",
    executionWindowEnd: "Kết thúc khung thực thi",
    pathType: "Loại đường dẫn",
    confidenceDelta: "Chênh lệch độ tin cậy",
    approvalDelta: "Chênh lệch phê duyệt",
    outcome: "Kết quả",
    evaluatedAt: "Thời điểm đánh giá",
  },
  wallet: {
    title: "Ví tiền",
    subtitle: "Theo dõi doanh thu và yêu cầu rút tiền.",
  },
  analytics: {
    title: "Phân tích",
    marketplacePerformance: "Hiệu suất chợ Avatar",
  },
  settings: {
    title: "Cài đặt",
  },
};
```

`en.ts` có thể giữ để dev debug, nhưng production default luôn là `vi`.

---

## 2. Hook dùng trong component

```ts
// frontend/src/i18n/useT.ts
import { useMemo } from "react";
import { vi } from "./vi";
import { en } from "./en";
import { useLocale } from "@/store/locale-store";

type Dict = typeof vi;
const dictionaries = { vi, en } as const;

function getByPath(obj: Record<string, any>, path: string): string {
  return path.split(".").reduce((acc, key) => acc?.[key], obj) ?? path;
}

export function useT() {
  const { languageCode } = useLocale();
  const dict = dictionaries[languageCode as keyof typeof dictionaries] ?? vi;
  return useMemo(() => (key: string) => getByPath(dict as Dict, key), [dict]);
}
```

---

## 3. Quy tắc sửa component

### Sai

```tsx
<button>Cancel</button>
<h1>Factory Command Center</h1>
<p>Decision failed</p>
```

### Đúng

```tsx
const t = useT();

<button>{t("common.cancel")}</button>
<h1>{t("factory.title")}</h1>
<p>{t("render.decisionFailed")}</p>
```

---

## 4. Các cụm tiếng Anh phải thay ngay

```txt
Close → Đóng
Cancel → Hủy
Apply → Áp dụng
Edit → Sửa
Delete → Xóa
Loading → Đang tải
Load → Tải
Retry → Thử lại
Approve → Phê duyệt
Settings → Cài đặt
Analytics → Phân tích
Wallet → Ví tiền
Factory Command Center → Trung tâm điều hành nhà máy
Realtime Progress → Tiến trình thời gian thực
Decision failed → Không tạo được quyết định
Approve failed → Phê duyệt thất bại
Audio Studio → Xưởng âm thanh
Voice profile → Hồ sơ giọng nói
Background music → Nhạc nền
Generate narration → Tạo lời dẫn
Avatar Builder → Tạo Avatar
Avatar Marketplace → Chợ Avatar
Production Dashboard → Bảng điều khiển sản xuất
Marketplace performance insights → Thông tin hiệu suất chợ Avatar
Trending Avatars → Avatar thịnh hành
View earnings and request payouts → Xem doanh thu và yêu cầu rút tiền
Amount (USD) → Số tiền (USD)
Request Payout → Yêu cầu rút tiền
Payout requested successfully → Đã gửi yêu cầu rút tiền
Scene Editor → Trình sửa cảnh
Subtitle Editor → Trình sửa phụ đề
Delete scene → Xóa cảnh
Delete subtitle → Xóa phụ đề
Character Reference Pack → Bộ tham chiếu nhân vật
Apply character lock to all scenes → Áp khóa nhân vật cho mọi cảnh
Save Veo Config → Lưu cấu hình Veo
Text to Video → Văn bản thành video
Image to Video → Ảnh thành video
```

---

## 5. CI guard bắt buộc

Thêm hoặc thay thế:

```txt
scripts/ci/check_frontend_i18n.py
```

Code mẫu:

```py
#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"

TARGET_DIRS = [SRC / "app", SRC / "components", SRC / "hooks", SRC / "lib", SRC / "store"]
TARGET_SUFFIXES = {".tsx", ".ts"}

ALLOW_FILE_PARTS = {
    "frontend/src/i18n/en.ts",
    "frontend/src/i18n/vi.ts",
    "frontend/src/i18n/useT.ts",
}

ALLOW_SUBSTRINGS = {
    "use client",
    "className",
    "http://",
    "https://",
    "NEXT_PUBLIC_",
    "API_BASE_URL",
    "Content-Type",
    "application/json",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "SSE",
    "UUID",
    "Veo",
    "Runway",
    "Kling",
    "YouTube",
    "USD",
    "ISO",
}

# Bắt literal có chữ cái tiếng Anh và có khả năng user-facing.
STRING_RE = re.compile(r"(?P<quote>[\"'`])(?P<text>(?:\\.|(?!\1).)*?[A-Za-z][^\"'`]*)\1")
CLASS_RE = re.compile(r"^[a-z0-9_:\-/\[\]\.\s$#%(),]+$")


def is_allowed(path: Path, text: str) -> bool:
    normalized = str(path.relative_to(ROOT)).replace("\\", "/")
    if normalized in ALLOW_FILE_PARTS:
        return True
    if any(token in text for token in ALLOW_SUBSTRINGS):
        return True
    if CLASS_RE.match(text.strip()):
        return True
    if text.strip().startswith(("/", "@/", "#", ".")):
        return True
    if "${" in text and len(text.split()) <= 3:
        return True
    return False


def main() -> int:
    violations: list[str] = []
    for base in TARGET_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in TARGET_SUFFIXES:
                continue
            raw = path.read_text(encoding="utf-8", errors="ignore")
            for idx, line in enumerate(raw.splitlines(), 1):
                for match in STRING_RE.finditer(line):
                    text = match.group("text").strip()
                    if len(text) < 3:
                        continue
                    if is_allowed(path, text):
                        continue
                    # user-facing candidates usually contain spaces, title-case, or common UI words
                    if " " in text or text[:1].isupper():
                        violations.append(f"{path.relative_to(ROOT)}:{idx}: {text}")
    if violations:
        print("❌ Frontend i18n guard failed. Move user-facing strings into i18n dictionaries:")
        print("\n".join(violations[:300]))
        if len(violations) > 300:
            print(f"... and {len(violations) - 300} more")
        return 1
    print("✅ Frontend i18n guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## 6. Package scripts

Trong `frontend/package.json` thêm:

```json
{
  "scripts": {
    "i18n:check": "python ../scripts/ci/check_frontend_i18n.py"
  }
}
```

Hoặc chạy từ root:

```bash
python scripts/ci/check_frontend_i18n.py
```

---

## 7. CI workflow phải có i18n gate

Trong `.github/workflows/unified-runtime-check.yml` thêm:

```yaml
- name: Frontend i18n guard
  run: python scripts/ci/check_frontend_i18n.py

- name: Frontend typecheck
  working-directory: frontend
  run: npm run typecheck
```

---

## 8. Acceptance criteria

Patch này chỉ pass khi:

```txt
1. frontend/src/app không còn hardcoded English user-facing
2. frontend/src/components không còn hardcoded English user-facing
3. frontend/src/i18n/vi.ts đầy đủ key đang dùng
4. locale default = vi
5. Sidebar, Factory, Render Jobs, Audio, Avatar, Marketplace, Analytics, Wallet, Settings đều hiển thị tiếng Việt
6. npm run typecheck pass
7. python scripts/ci/check_frontend_i18n.py pass
8. Production build không fallback UI tiếng Anh
```

---

## 9. Patch order khuyến nghị

```txt
1. Bổ sung key vào vi.ts và en.ts
2. Sửa useT nếu chưa support nested key
3. Sửa Sidebar + DashboardShell trước
4. Sửa app pages
5. Sửa Factory components
6. Sửa Render/Preview components
7. Sửa Avatar Builder
8. Sửa Marketplace/Creator/Wallet
9. Sửa Templates/Strategy
10. Chạy i18n guard
11. Chạy frontend typecheck
12. Merge khi CI pass
```
