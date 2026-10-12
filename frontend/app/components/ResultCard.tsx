// 検索結果の1件。推薦理由（reason）を目立つ位置に出す
import { placeholder } from "@/lib/api";
import type { Product } from "@/types";

export default function ResultCard({ product: p, rank }: { product: Product; rank: number }) {
  return (
    <article className="card">
      <img src={placeholder(p.category)} alt={`${p.category}の仮画像`} width={120} height={120} />
      <div className="body">
        <p className="meta">{rank}位・{p.category}・{p.brand}</p>
        <h2>{p.product_name}</h2>
        <p className="price">{p.price.toLocaleString()}円</p>
        <p className="reason">{p.reason}</p>
        <p className="meta">
          {p.rating !== null ? `評価${p.rating.toFixed(1)}（${p.review_count}件）` : "レビューなし"}・{p.delivery_days}日でお届け
          {p.gift_wrap ? "・ラッピング可" : ""}
        </p>
      </div>
    </article>
  );
}
