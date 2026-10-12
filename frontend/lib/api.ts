// API を呼ぶ関数をここにまとめる（画面のコードに URL を散らばらせない）
import type { Meta, SearchResponse } from "@/types";

// API は別のアプリ（ローカル：http://localhost:8000、Azure：https://<チーム>-api.azurewebsites.net）。
// NEXT_PUBLIC_ の値はビルドのときに画面のコードへ埋め込まれ、ブラウザに配られる。秘密の値は置かない
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const fetchMeta = () => get<Meta>("/api/meta");

export type SearchParams = {
  mode: "standard" | "business";
  q?: string; category?: string; scene?: string; sort?: string;
  price_min: string; price_max: string;
  use_llm: boolean;
  // 取引先へのお礼の版だけで使う
  min_shelf_days?: number; need_indiv_wrap?: boolean; exclude_alcohol?: boolean; include_unknown?: boolean;
};

export function searchProducts(p: SearchParams) {
  const qs = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => {
    if (v === "" || v === undefined) return;
    if (v === false && k !== "need_indiv_wrap" && k !== "exclude_alcohol") return;  // false を送る必要がある項目だけ残す
    qs.set(k, String(v));
  });
  return get<SearchResponse>(`/api/search?${qs.toString()}`);
}

// カテゴリー → 仮画像（本物の商品画像は配布DBに含まれない。講義設計書 決定#26）
const SLUG: Record<string, string> = {
  食品: "food", 飲料: "drink", 酒類: "alcohol", 生活雑貨: "goods", インテリア: "interior",
  コスメ: "cosme", 家電: "appliance", ビジネス小物: "business", フラワー: "flower", カタログギフト: "catalog",
};
export const placeholder = (category: string) => `/placeholders/${SLUG[category] ?? "goods"}.svg`;
