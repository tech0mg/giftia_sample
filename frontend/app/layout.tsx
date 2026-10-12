import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Giftia ギフト検索（サンプル）",
  description: "Tech0 Step3-1 Giftia ケースのサンプルアプリ",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
