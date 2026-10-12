// 画面は Azure App Service（Node.js）の Web アプリで next start として動かす（5周目）
// API は別の Web アプリ（FastAPI）。画面はすべてブラウザ側で動き（"use client"）、ブラウザから API を直接呼ぶ
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: { unoptimized: true },
};
export default nextConfig;
