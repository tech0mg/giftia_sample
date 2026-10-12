# ─────────────────────────────────────────────
# search.py — 検索ロジック（候補取得 → 順位付け → 理由生成）
# 対応する要件定義書: 6章（ランキング設計）
#
# このサンプルは「いまの Giftia の検索」を再現したもの（Exhibit 3）。
#   ・候補取得：キーワード・カテゴリー・価格帯・贈るシーンで絞り込む
#   ・順位付け：おすすめ順＝キーワード一致度＋販売実績＋レビュー評価（ほか、人気・評価・価格・新着）
#   ・理由生成：データから分かる事実を並べるだけ
#
# ★チームが差し替える場所★
#   find_candidates() … 自分たちの入力（関係性・避けたいこと など）で候補を絞る
#   rank()            … 自分たちのロジック（スコアリング／ルール／LLM）で並べる
#   make_reason()     … 「なぜこの商品なのか」を顧客課題に合わせて説明する
#   3つとも同じ形（dict を受け取り dict を返す）のまま中身を変えれば、main.py と画面はそのまま動く。
# ─────────────────────────────────────────────

import math
from dataclasses import dataclass, field

from database import fetch_all

SORTS = {"recommend": "おすすめ順", "popular": "人気順", "rating": "評価順", "price_asc": "価格の安い順", "new": "新着順"}


@dataclass
class Condition:
    """画面から受け取る検索条件。チームの入力項目を足すときは、ここに項目を足す。"""
    keywords: list[str] = field(default_factory=list)  # 空白で区切った語。すべてを含む商品を探す（AND）
    category: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    scene: str | None = None  # 贈るシーンのタグ（product_scenes.scene_tag）
    sort: str = "recommend"


# ── 1. 候補取得 ──────────────────────────────
def find_candidates(cond: Condition) -> list[dict]:
    """条件に合う商品を DB から取る。並べ替えはしない（rank() の仕事）。
    8,000件なら全件取って Python で並べても速い。件数が増えたら、ここで上限や索引を考える（要件定義書 8章）。"""
    where, params = ["p.stock > 0"], []  # 在庫切れは出さない
    for word in cond.keywords:
        where.append("(p.product_name LIKE ? OR p.brand LIKE ? OR p.description LIKE ?)")
        params += [f"%{word}%"] * 3
    if cond.category:
        where.append("p.category = ?")
        params.append(cond.category)
    if cond.price_min is not None:
        where.append("p.price >= ?")
        params.append(cond.price_min)
    if cond.price_max is not None:
        where.append("p.price <= ?")
        params.append(cond.price_max)
    if cond.scene:
        where.append("EXISTS (SELECT 1 FROM product_scenes s WHERE s.product_id = p.product_id AND s.scene_tag = ?)")
        params.append(cond.scene)

    query = f"""
        SELECT p.product_id, p.product_name, p.category, p.price, p.brand, p.description, p.size,
               p.delivery_days, p.gift_wrap, p.message_card, p.rating, p.review_count, p.sales_count,
               p.stock, p.registered_at
        FROM products p
        WHERE {' AND '.join(where)}
    """
    return fetch_all(query, tuple(params))


# ── 2. 順位付け ──────────────────────────────
def keyword_score(item: dict, keywords: list[str]) -> float:
    """キーワード一致度：商品名に入っていれば3点、ブランドなら2点、説明文だけなら1点（語ごとに足す）。"""
    score = 0.0
    for w in keywords:
        if w in item["product_name"]:
            score += 3
        elif w in item["brand"]:
            score += 2
        elif w in (item["description"] or ""):
            score += 1
    return score


def recommend_score(item: dict, keywords: list[str]) -> float:
    """おすすめ順のスコア＝キーワード一致度＋販売実績＋レビュー評価（Exhibit 3 の説明どおりの組み合わせ）。"""
    sales = math.log10(1 + item["sales_count"])                    # 売れ筋ほど高い（桁で効く）
    rating = (item["rating"] or 0) * min(1.0, item["review_count"] / 20)  # レビューが少ない商品の評価は割り引く
    return keyword_score(item, keywords) * 2 + sales + rating


def rank(items: list[dict], cond: Condition) -> list[dict]:
    """候補を並べ替える。score は画面で確認できるように返す。"""
    for it in items:
        it["score"] = round(recommend_score(it, cond.keywords), 3)
    key = {
        "recommend": lambda it: (-it["score"], it["product_id"]),
        "popular": lambda it: (-it["sales_count"], it["product_id"]),
        "rating": lambda it: (-(it["rating"] or 0), -it["review_count"], it["product_id"]),
        "price_asc": lambda it: (it["price"], it["product_id"]),
        "new": lambda it: (it["registered_at"], it["product_id"]),
    }[cond.sort if cond.sort in SORTS else "recommend"]
    items = sorted(items, key=key)
    if cond.sort == "new":
        items.reverse()
    return items


# ── 3. 理由生成 ──────────────────────────────
def make_reason(item: dict, cond: Condition) -> str:
    """データから言える事実だけで、表示する理由を作る（推測は書かない）。"""
    parts = []
    hits = [w for w in cond.keywords if w in item["product_name"] or w in item["brand"] or w in (item["description"] or "")]
    if hits:
        parts.append(f"「{'・'.join(hits)}」に一致")
    if cond.scene:
        parts.append(f"「{cond.scene}」のタグ付き")
    if item["sales_count"] >= 100:
        parts.append(f"直近1年で{item['sales_count']:,}個の売れ筋")
    if item["rating"] is not None and item["review_count"] >= 5:
        parts.append(f"評価{item['rating']:.1f}（{item['review_count']}件）")
    if item["delivery_days"] <= 2:
        parts.append(f"{item['delivery_days']}日でお届け")
    return "・".join(parts) if parts else "条件に合う商品"


# ── まとめて呼ぶ ─────────────────────────────
def search(cond: Condition, limit: int = 20) -> dict:
    candidates = find_candidates(cond)
    ranked = rank(candidates, cond)[:limit]
    for it in ranked:
        it["reason"] = make_reason(it, cond)
        it.pop("description", None)  # 一覧には長い説明文を返さない（商品詳細APIで返す）
    return {"total_candidates": len(candidates), "results": ranked}
