# ─────────────────────────────────────────────
# llm.py — 推薦理由を LLM（OpenAI API）で作る（任意・4周目）
# 対応する要件定義書: 6.1（方式）・6.3（推薦理由）・6.4（テストケース）・8章（セキュリティ）
#
# 使うのは、環境変数 OPENAI_API_KEY と OPENAI_MODEL が両方あるときだけ。
# どちらかがない・API が失敗したときは None を返し、search.make_reason() の理由をそのまま使う。
#
# 約束（講義設計書 決定#13）
#   ・呼び出しは FastAPI 側からだけ。キーを Next.js（NEXT_PUBLIC_…）や GitHub に置かない
#   ・キーは .env（ローカル）と Azure のアプリ設定（本番）にだけ置く
#   ・会員の個人情報は送らない（送るのは検索条件と商品の公開情報だけ）
#   ・出力は毎回変わる。テストでは「何が満たされていれば合格か」を決めておく（要件定義書 6.4）
# ─────────────────────────────────────────────

import json
import os

SYSTEM = (
    "あなたはギフトECの商品説明を書くアシスタントです。"
    "与えられた商品データに書かれている事実だけを使い、なぜこの商品が検索条件に合うのかを、"
    "商品ごとに40字以内の日本語1文で書いてください。データにないこと（味・香りの感想など）は書かないでください。"
    '出力は {"reasons": {"商品ID": "理由", ...}} の JSON だけにしてください。'
)


def enabled() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_MODEL"))


def llm_reasons(items: list[dict], condition: dict) -> dict[str, str] | None:
    """商品ID → 理由 の dict を返す。使えないときは None（呼び出し側はテンプレートの理由を使う）。"""
    if not enabled() or not items:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    payload = {
        "condition": condition,
        "items": [{k: it.get(k) for k in ("product_id", "product_name", "category", "price", "rating", "review_count",
                                           "sales_count", "delivery_days", "reason")} for it in items],
    }
    try:
        client = OpenAI(timeout=15)  # OPENAI_API_KEY は環境変数から読まれる
        res = client.chat.completions.create(
            model=os.environ["OPENAI_MODEL"],
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            response_format={"type": "json_object"},
        )
        reasons = json.loads(res.choices[0].message.content).get("reasons", {})
        ids = {it["product_id"] for it in items}
        return {k: str(v)[:80] for k, v in reasons.items() if k in ids}  # 知らない商品IDや長すぎる文は捨てる
    except Exception:  # 失敗しても検索自体は止めない
        return None
