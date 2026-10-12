"use client";

// 検索フォーム。チームの入力項目（関係性・避けたいこと など）はここに足し、
// lib/api.ts の SearchParams と backend/search.py の Condition にも同じ項目を足す。

import { useState } from "react";
import type { SearchParams } from "@/lib/api";
import type { Meta } from "@/types";

// 価格帯は「下限以上・上限未満」（決定#35）。API の price_max は「以下」なので、円の整数として上限−1 を渡す
const PRICE_BANDS: Record<string, [string, string]> = {
  "": ["", ""], "〜3,000円": ["", "2999"], "3,000〜5,000円": ["3000", "4999"],
  "5,000〜10,000円": ["5000", "9999"], "10,000円〜": ["10000", ""],
};

export default function SearchForm({ meta, loading, onSearch }: {
  meta: Meta | null; loading: boolean; onSearch: (p: SearchParams) => void;
}) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [scene, setScene] = useState("");
  const [band, setBand] = useState("");
  const [sort, setSort] = useState("recommend");
  const [useLlm, setUseLlm] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const [price_min, price_max] = PRICE_BANDS[band];
    onSearch({ mode: "standard", q: q.trim(), category, scene, price_min, price_max, sort, use_llm: useLlm });
  };

  return (
    <form className="form" onSubmit={submit}>
      <input className="q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="キーワード（例：送別 お菓子）" />
      <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="カテゴリー">
        <option value="">すべてのカテゴリー</option>
        {meta?.categories.map((c) => <option key={c}>{c}</option>)}
      </select>
      <select value={scene} onChange={(e) => setScene(e.target.value)} aria-label="贈るシーン">
        <option value="">すべてのシーン</option>
        {meta?.scenes.map((s) => <option key={s}>{s}</option>)}
      </select>
      <select value={band} onChange={(e) => setBand(e.target.value)} aria-label="価格帯">
        {Object.keys(PRICE_BANDS).map((b) => <option key={b} value={b}>{b || "すべての価格帯"}</option>)}
      </select>
      <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="並べ替え">
        {meta && Object.entries(meta.sorts).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      {meta?.llm && (
        <label className="llm">
          <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> 理由をLLMで作る
        </label>
      )}
      <button type="submit" disabled={loading}>{loading ? "検索中…" : "検索"}</button>
    </form>
  );
}
