"use client";

// 取引先へのお礼（ヒアリングC）の検索フォーム。
// 「相手の好みが分からない」ので、聞くのは予算と、外せない条件だけにしている。

import { useState } from "react";
import type { SearchParams } from "@/lib/api";

// 価格帯は「下限以上・上限未満」（決定#35）。API の price_max は「以下」なので、円の整数として上限−1 を渡す
const PRICE_BANDS: Record<string, [string, string]> = {
  "": ["", ""], "〜3,000円": ["", "2999"], "3,000〜5,000円": ["3000", "4999"],
  "5,000〜10,000円": ["5000", "9999"], "10,000円〜": ["10000", ""],
};

export default function BusinessForm({ loading, llm, onSearch }: {
  loading: boolean; llm: boolean; onSearch: (p: SearchParams) => void;
}) {
  const [band, setBand] = useState("3,000〜5,000円");
  const [minShelf, setMinShelf] = useState(30);
  const [needIndiv, setNeedIndiv] = useState(true);
  const [excludeAlcohol, setExcludeAlcohol] = useState(true);
  const [includeUnknown, setIncludeUnknown] = useState(false);
  const [useLlm, setUseLlm] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const [price_min, price_max] = PRICE_BANDS[band];
    onSearch({
      mode: "business", price_min, price_max, min_shelf_days: minShelf,
      need_indiv_wrap: needIndiv, exclude_alcohol: excludeAlcohol, include_unknown: includeUnknown, use_llm: useLlm,
    });
  };

  return (
    <form className="form" onSubmit={submit}>
      <select value={band} onChange={(e) => setBand(e.target.value)} aria-label="予算">
        {Object.keys(PRICE_BANDS).map((b) => <option key={b} value={b}>{b || "すべての価格帯"}</option>)}
      </select>
      <label className="llm">
        賞味期限
        <select value={minShelf} onChange={(e) => setMinShelf(Number(e.target.value))} aria-label="賞味期限の下限">
          {[14, 30, 60, 90].map((d) => <option key={d} value={d}>{d}日以上</option>)}
        </select>
      </label>
      <label className="llm"><input type="checkbox" checked={needIndiv} onChange={(e) => setNeedIndiv(e.target.checked)} /> 個包装のみ</label>
      <label className="llm"><input type="checkbox" checked={excludeAlcohol} onChange={(e) => setExcludeAlcohol(e.target.checked)} /> お酒を外す</label>
      <label className="llm"><input type="checkbox" checked={includeUnknown} onChange={(e) => setIncludeUnknown(e.target.checked)} /> 説明文に記載のない商品も含める</label>
      {llm && <label className="llm"><input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> 理由をLLMで作る</label>}
      <button type="submit" disabled={loading}>{loading ? "検索中…" : "探す"}</button>
    </form>
  );
}
