import "./globals.css";

export const metadata = {
  title: "AI Ads Factory SaaS",
  description: "AI Creative Revenue Operating System"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        {children}
      </body>
    </html>
  );
}
