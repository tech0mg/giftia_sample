"use client";

// ─────────────────────────────────────────────
// Giftia ギフト検索 — メインページ
// 対応する要件定義書: 4.2（画面一覧）
//
// データの流れ:
//   検索フォーム → searchProducts()（lib/api.ts）→ FastAPI /api/search
//   → 候補取得 → 順位付け → 理由生成（backend/search.py）→ 結果カード
// ─────────────────────────────────────────────

import { useEffect, useState } from "react";
import BusinessForm from "./components/BusinessForm";
import ResultCard from "./components/ResultCard";
import SearchForm from "./components/SearchForm";
import { fetchMeta, searchProducts, type SearchParams } from "@/lib/api";
import type { Meta, SearchResponse } from "@/types";

export default function Home() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [mode, setMode] = useState<"standard" | "business">("standard");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMeta().then(setMeta).catch((e) => setError(`APIにつながりません：${e.message}`));
  }, []);

  const onSearch = async (p: SearchParams) => {
    setLoading(true);
    setError(null);
    try {
      setData(await searchProducts(p));
    } catch (e) {
      setError(e instanceof Error ? e.message : "予期しないエラーが発生しました");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page">
      <header className="header">
        <h1>Giftia</h1>
      </header>

      <nav className="modes">
        {meta && Object.entries(meta.modes).map(([k, label]) => (
          <button key={k} type="button" className={mode === k ? "on" : ""}
                  onClick={() => { setMode(k as "standard" | "business"); setData(null); }}>
            {label}
          </button>
        ))}
      </nav>
      <p className="summary">
        {mode === "standard"
          ? "いまの Giftia の検索（キーワード一致度・販売実績・レビュー評価で並べる）"
          : "取引先へのお礼（ヒアリングC）：説明文で確かめられる商品だけを出し、外さない順に並べる"}
      </p>

      {mode === "standard"
        ? <SearchForm meta={meta} loading={loading} onSearch={onSearch} />
        : <BusinessForm loading={loading} llm={!!meta?.llm} onSearch={onSearch} />}

      {error && <p className="error">{error}</p>}

      {data && (
        <section>
          <p className="summary">
            候補 {data.total_candidates.toLocaleString()} 件から上位 {data.results.length} 件
            {data.reason_source === "llm" ? "（理由：LLM）" : "（理由：データから作成）"}
          </p>
          {data.results.length === 0 && <p>条件に合う商品が見つかりませんでした。</p>}
          <div className="grid">
            {data.results.map((p, i) => (
              <ResultCard key={p.product_id} product={p} rank={i + 1} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
