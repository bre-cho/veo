import "./globals.css";

import { LocaleProvider } from "@/src/store/locale-store";

export const metadata = {
  title: "He thong dieu phoi dung phim",
  description: "Bang dieu khien quy trinh san xuat theo du an",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
