# ─────────────────────────────────────────────
# search_business.py — 取引先へのお礼（ヒアリングC）向けの検索：候補取得 → 順位付け → 理由生成
# 対応する要件定義書: 6章（ランキング設計）
#
# search.py（いまの Giftia の検索）と同じ3つの関数の形で、中身を1つの Job に合わせて書き換えた実例。
#
# Job：仕事の相手に、関係を損なわずにお礼をしたい。相手の好みは分からないので「外さないこと」が大事。
#   Cさんが何度も確かめていたこと（Exhibit 2）：会社宛てに送れるか／常温で置けるか／個包装か／賞味期限は十分か
#
#   候補取得：常温・個包装・賞味期限が「説明文に書いてあって、条件を満たす」商品だけを取る（product_facts を使う）
#             お酒は、相手が飲むか分からないので既定で外す
#   順位付け：「外さない」ことを表す値で並べる＝レビュー評価（件数で割り引く）＋販売実績＋会社宛ての注文実績＋日持ちの長さ
#   理由生成：確かめた事実と、その出どころ（説明文／注文データ）をそのまま書く
#
# product_facts は tools/extract_facts.py で作る（配布の giftia.db には入っていない）。
# ─────────────────────────────────────────────

import math
from dataclasses import dataclass

from database import fetch_all


@dataclass
class BusinessCondition:
    """取引先へのお礼で受け取る条件"""
    price_min: int | None = None
    price_max: int | None = None
    min_shelf_days: int = 30        # 賞味期限は製造日から何日以上あればよいか
    need_indiv_wrap: bool = True    # 相手の職場で分けやすいように、個包装にするか
    exclude_alcohol: bool = True    # 相手がお酒を飲むか分からないので外す
    include_unknown: bool = False   # 説明文に書いていない商品も候補に入れるか（入れると、書いていない分だけ順位を下げる）


FACT_COLUMNS = ["room_temp", "indiv_wrap", "shelf_life_days", "office_orders"]


# ── 1. 候補取得 ──────────────────────────────
def find_candidates(cond: BusinessCondition) -> list[dict]:
    """商品に product_facts を横につなげて取り、条件で絞る。"""
    pivot = ",\n".join(
        f"MAX(CASE WHEN f.fact = '{c}' THEN f.value END) AS {c}" for c in FACT_COLUMNS
    )
    where, params = ["p.stock > 0", "p.category IN ('食品', '飲料', '酒類')"], []  # 常温・賞味期限が意味を持つ食べもの・飲みもの
    if cond.exclude_alcohol:
        where.append("p.category <> '酒類'")
    if cond.price_min is not None:
        where.append("p.price >= ?")
        params.append(cond.price_min)
    if cond.price_max is not None:
        where.append("p.price <= ?")
        params.append(cond.price_max)
    query = f"""
        SELECT p.product_id, p.product_name, p.category, p.price, p.brand, p.size, p.delivery_days,
               p.gift_wrap, p.message_card, p.rating, p.review_count, p.sales_count, p.stock, p.registered_at,
               {pivot}
        FROM products p LEFT JOIN product_facts f ON f.product_id = p.product_id
        WHERE {' AND '.join(where)}
        GROUP BY p.product_id, p.product_name, p.category, p.price, p.brand, p.size, p.delivery_days,
                 p.gift_wrap, p.message_card, p.rating, p.review_count, p.sales_count, p.stock, p.registered_at
    """
    rows = fetch_all(query, tuple(params))

    def ok(value, good) -> bool:
        """書いてあって条件を満たす → True。書いていない → include_unknown のときだけ True。"""
        return good(value) if value is not None else cond.include_unknown

    return [
        r for r in rows
        if ok(r["room_temp"], lambda v: v == 1)
        and (not cond.need_indiv_wrap or ok(r["indiv_wrap"], lambda v: v == 1))
        and ok(r["shelf_life_days"], lambda v: v >= cond.min_shelf_days)
    ]


# ── 2. 順位付け ──────────────────────────────
def safe_score(item: dict) -> float:
    """「外さない」度合い。どれも、受け取った人が困らなかった実績や確かさを表す値。"""
    rating = (item["rating"] or 0) * min(1.0, item["review_count"] / 20)  # レビューが少ないと割り引く
    sales = math.log10(1 + item["sales_count"])
    office = math.log10(1 + (item["office_orders"] or 0)) * 1.5           # 会社宛てに贈られてきた実績
    shelf = min(item["shelf_life_days"] or 0, 180) / 180                    # 日持ちが長いほど相手の都合に合わせやすい
    unknown = sum(item[c] is None for c in ("room_temp", "indiv_wrap", "shelf_life_days"))
    return rating + sales + office + shelf - 2 * unknown                    # 書いていない事実があるほど下げる


def rank(items: list[dict], cond: BusinessCondition) -> list[dict]:
    for it in items:
        it["score"] = round(safe_score(it), 3)
    return sorted(items, key=lambda it: (-it["score"], it["product_id"]))


# ── 3. 理由生成 ──────────────────────────────
def make_reason(item: dict, cond: BusinessCondition) -> str:
    """確かめた事実を、出どころと一緒に書く。書いていない事実は「記載なし」とはっきり書く。"""
    facts = [
        "常温で保存できる" if item["room_temp"] == 1 else "保存方法は記載なし",
        {1: "個包装", 0: "個包装ではない", None: "個包装かは記載なし"}[item["indiv_wrap"]],
        f"日持ち{item['shelf_life_days']}日以上" if item["shelf_life_days"] else "賞味期限は記載なし",
    ]
    parts = ["・".join(f for f in facts if f) + "（説明文より）"]
    if item["office_orders"]:
        parts.append(f"会社宛ての注文{item['office_orders']}件（直近1年）")
    if item["rating"] is not None and item["review_count"] >= 5:
        parts.append(f"評価{item['rating']:.1f}（{item['review_count']}件）")
    return "／".join(parts)


# ── まとめて呼ぶ ─────────────────────────────
def search(cond: BusinessCondition, limit: int = 20) -> dict:
    candidates = find_candidates(cond)
    ranked = rank(candidates, cond)[:limit]
    for it in ranked:
        it["reason"] = make_reason(it, cond)
    return {"total_candidates": len(candidates), "results": ranked}
