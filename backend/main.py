# ─────────────────────────────────────────────
# main.py — FastAPI アプリケーション
# 対応する要件定義書: 4.3（API一覧）
#
# 起動（ローカル開発）:
#   uvicorn main:app --reload
# 起動（Azure App Service・5周目。スタートアップコマンドに書く）:
#   gunicorn -w 2 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0 --timeout 120 main:app
# 確認:
#   http://localhost:8000/docs                         → Swagger UI（APIを画面から試せる）
#   http://localhost:8000/api/search?q=タオル&scene=送別 → 検索
# ─────────────────────────────────────────────

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import llm
import search_business
from database import fetch_all, get_db_type
from search import SORTS, Condition, search

MODES = {"standard": "いまの検索", "business": "取引先へのお礼"}

load_dotenv()

app = FastAPI(title="Giftia Search API", description="Giftia ギフト検索 — バックエンドAPI（サンプル）", version="1.0.0")

# ── CORS ────────────────────────────────────
# 画面（Next.js）とこの API は別のアプリなので、オリジン（URL の頭）が違う。ブラウザから呼ぶには許可が要る。
#   ローカル：画面 http://localhost:3000 → API http://localhost:8000（既定値）
#   Azure  ：画面 https://<チーム>-web.azurewebsites.net → API https://<チーム>-api.azurewebsites.net
#            App Service のアプリ設定で CORS_ORIGINS に画面の URL を入れる（カンマ区切りで複数可）
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
                   allow_methods=["GET"], allow_headers=["*"])


@app.get("/")
def root():
    """直接開いたときの案内"""
    return {"service": "Giftia Search API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health():
    """ヘルスチェック（どのDBにつながっているか）"""
    return {"service": "Giftia Search API", "status": "ok", "db": get_db_type(), "llm": llm.enabled()}


@app.get("/api/meta")
def meta():
    """検索フォームの選択肢（カテゴリー・贈るシーン・並べ替え）を DB から返す。"""
    categories = [r["category"] for r in fetch_all("SELECT DISTINCT category FROM products ORDER BY category")]
    scenes = [r["scene_tag"] for r in fetch_all("SELECT scene_tag, COUNT(*) AS n FROM product_scenes GROUP BY scene_tag ORDER BY n DESC")]
    return {"categories": categories, "scenes": scenes, "sorts": SORTS, "modes": MODES, "llm": llm.enabled()}


@app.get("/api/search")
def search_products(
    q: str = Query(default="", description="キーワード（空白区切りで複数語。すべてを含む商品）"),
    category: str | None = Query(default=None),
    price_min: int | None = Query(default=None, ge=0),
    price_max: int | None = Query(default=None, ge=0),
    scene: str | None = Query(default=None, description="贈るシーンのタグ"),
    sort: str = Query(default="recommend", description="、".join(f"{k}={v}" for k, v in SORTS.items())),
    limit: int = Query(default=20, ge=1, le=100),
    use_llm: bool = Query(default=False, description="true なら推薦理由を LLM で作る（キーが設定されているときだけ）"),
    mode: str = Query(default="standard", description="standard=いまの検索（search.py）／business=取引先へのお礼（search_business.py）"),
    min_shelf_days: int = Query(default=30, ge=0, description="business：賞味期限の下限（日）"),
    need_indiv_wrap: bool = Query(default=True, description="business：個包装に限るか"),
    exclude_alcohol: bool = Query(default=True, description="business：お酒を外すか"),
    include_unknown: bool = Query(default=False, description="business：説明文に書いていない商品も入れるか"),
):
    """検索：候補取得 → 順位付け → 理由生成。mode で、どちらの3関数を使うかを切り替える。"""
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"mode は {', '.join(MODES)} のどちらかにしてください")
    if price_min is not None and price_max is not None and price_min > price_max:
        raise HTTPException(status_code=400, detail="price_min が price_max より大きくなっています")
    if mode == "business":
        cond_b = search_business.BusinessCondition(price_min=price_min, price_max=price_max, min_shelf_days=min_shelf_days,
                                                   need_indiv_wrap=need_indiv_wrap, exclude_alcohol=exclude_alcohol,
                                                   include_unknown=include_unknown)
        try:
            result = search_business.search(cond_b, limit=limit)
        except Exception as e:
            if "product_facts" in str(e):
                raise HTTPException(status_code=503, detail="product_facts がありません。backend/ で python tools/extract_facts.py を実行してください")
            raise
        return _with_reasons(result, cond_b.__dict__, use_llm, mode)
    if sort not in SORTS:
        raise HTTPException(status_code=400, detail=f"sort は {', '.join(SORTS)} のどれかにしてください")
    cond = Condition(keywords=q.split(), category=category or None, price_min=price_min, price_max=price_max,
                     scene=scene or None, sort=sort)
    return _with_reasons(search(cond, limit=limit), cond.__dict__, use_llm, mode)


def _with_reasons(result: dict, condition: dict, use_llm: bool, mode: str) -> dict:
    """LLM を使うなら理由を差し替える（使えなければデータから作った理由のまま）。"""
    result["reason_source"] = "template"
    if use_llm:
        reasons = llm.llm_reasons(result["results"], condition)
        if reasons:
            for it in result["results"]:
                it["reason"] = reasons.get(it["product_id"], it["reason"])
            result["reason_source"] = "llm"
    result["mode"] = mode
    result["condition"] = condition
    return result


@app.get("/api/products/{product_id}")
def product_detail(product_id: str):
    """商品の詳細（説明文・シーンタグ・本文つきレビューの新しい順5件）"""
    rows = fetch_all("SELECT * FROM products WHERE product_id = ?", (product_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="商品が見つかりません")
    item = rows[0]
    item["scenes"] = [r["scene_tag"] for r in fetch_all("SELECT scene_tag FROM product_scenes WHERE product_id = ?", (product_id,))]
    item["reviews"] = fetch_all("""SELECT rating, comment, posted_at FROM reviews
                                   WHERE product_id = ? AND comment IS NOT NULL ORDER BY posted_at DESC LIMIT 5""", (product_id,))
    return item
