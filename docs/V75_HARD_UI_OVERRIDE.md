# V7.5 Hard UI Override

Patch này ép toàn bộ UI về SaaS style khi các trang vẫn bị raw/dev mode.

## Cài đặt

App Router:

```bash
cp app/globals.css ./app/globals.css
```

Nếu dùng `src/app`:

```bash
cp app/globals.css ./src/app/globals.css
```

Trong `app/layout.tsx` phải có:

```ts
import "./globals.css";
```

## Nếu Tailwind chưa ăn class

Kiểm tra `tailwind.config.ts`:

```ts
content: [
  "./app/**/*.{js,ts,jsx,tsx,mdx}",
  "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  "./components/**/*.{js,ts,jsx,tsx,mdx}",
  "./src/components/**/*.{js,ts,jsx,tsx,mdx}"
]
```

## Class khuyến nghị

- Grid: `templates-grid`, `metrics-grid`, `score-grid`, `dashboard-metrics`
- Card: `card`, `template-card`, `metric-card`
- Table: `dashboard-table`, row: `dashboard-row`
- Signup: `signup-grid`
- Optimize: `optimize-grid`
- Output: `output-preview`
