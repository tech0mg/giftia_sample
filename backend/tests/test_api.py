# ─────────────────────────────────────────────
# test_api.py — サンプルのテスト（pytest）
#   cd backend && pytest -q
# 配布データの事実（Exhibit 3 の検索件数・ヒアリングのペルソナ）が API から見えることも確かめる。
# ─────────────────────────────────────────────
import pytest
from fastapi.testclient import TestClient

import llm
from database import fetch_all
from main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_meta_lists_choices():
    m = client.get("/api/meta").json()
    assert len(m["categories"]) == 10
    assert "送別" in m["scenes"] and len(m["scenes"]) == 9


def test_exhibit3_search_counts():
    """Exhibit 3：「40代 女性 送別 プレゼント」で約180件、3,000〜5,000円で約70件"""
    all_ = client.get("/api/search", params={"q": "40代 女性 送別 プレゼント"}).json()
    band = client.get("/api/search", params={"q": "40代 女性 送別 プレゼント", "price_min": 3000, "price_max": 5000}).json()
    assert 150 <= all_["total_candidates"] <= 220
    assert 50 <= band["total_candidates"] <= 90


def test_farewell_ranking_top_is_persona_a_hand_cream():
    """ヒアリングA：送別ランキングの1位はハンドクリーム、2位は焼き菓子"""
    r = client.get("/api/search", params={"scene": "送別", "sort": "popular", "limit": 2}).json()["results"]
    assert "ハンドクリーム" in r[0]["product_name"] and "焼き菓子" in r[1]["product_name"]


def test_results_have_reason_and_are_sorted():
    r = client.get("/api/search", params={"q": "タオル", "sort": "price_asc"}).json()
    prices = [it["price"] for it in r["results"]]
    assert prices == sorted(prices)
    assert all(it["reason"] for it in r["results"])
    assert r["reason_source"] == "template"


def test_price_filter_is_respected():
    r = client.get("/api/search", params={"price_min": 3000, "price_max": 5000, "limit": 100}).json()["results"]
    assert all(3000 <= it["price"] <= 5000 for it in r)


@pytest.mark.parametrize("params", [{"sort": "cheap"}, {"price_min": 5000, "price_max": 3000}])
def test_bad_request(params):
    assert client.get("/api/search", params=params).status_code == 400


def test_product_detail_and_404():
    d = client.get("/api/products/G0001").json()
    assert d["product_name"].endswith("国産タオルギフトセット") and "送別" in d["scenes"]
    assert client.get("/api/products/G9999").status_code == 404


def test_member_apis_do_not_exist():
    """ログインと会員の API は持たない（会員の履歴は DB で分析する）"""
    assert client.get("/api/me").status_code == 404
    assert client.get("/api/me/orders").status_code == 404


def test_persona_e_repeats_same_gifts():
    """ヒアリングE：毎年お中元・お歳暮に、同じ2人へ同じ商品（API ではなく DB で確かめる）"""
    rows = fetch_all("""SELECT o.recipient_key, i.product_id FROM orders o
                        JOIN order_items i ON i.order_id = o.order_id
                        WHERE o.user_id = ? AND i.line_no = 1""", ("U-PERSONA-E",))
    assert len(rows) == 8
    assert len({(r["recipient_key"], r["product_id"]) for r in rows}) == 2


def test_llm_is_skipped_without_key():
    assert llm.llm_reasons([{"product_id": "G0001"}], {}) is None
    r = client.get("/api/search", params={"q": "タオル", "use_llm": "true"}).json()
    assert r["reason_source"] == "template"


def test_llm_reasons_replace_template(monkeypatch):
    monkeypatch.setattr(llm, "llm_reasons", lambda items, cond: {items[0]["product_id"]: "LLMの理由"})
    r = client.get("/api/search", params={"q": "タオル", "use_llm": "true", "limit": 3}).json()
    assert r["reason_source"] == "llm" and r["results"][0]["reason"] == "LLMの理由"


# ── Cの版：取引先へのお礼（search_business.py）──────────────
def business(**params):
    return client.get("/api/search", params={"mode": "business", "limit": 100, **params}).json()


def test_business_keeps_only_confirmed_facts():
    """常温・個包装・賞味期限30日以上が説明文で確かめられ、お酒でない商品だけが出る"""
    r = business()
    assert r["total_candidates"] > 0 and r["mode"] == "business"
    for it in r["results"]:
        assert it["room_temp"] == 1 and it["indiv_wrap"] == 1 and it["shelf_life_days"] >= 30
        assert it["category"] != "酒類"
        assert "（説明文より）" in it["reason"]


def test_business_finds_persona_c_purchase():
    """ヒアリングC：有名店の個包装焼き菓子（フィナンシェ 12個入 3,780円）が、3,000〜5,000円の候補に入る"""
    ids = [it["product_name"] for it in business(price_min=3000, price_max=5000)["results"]]
    assert any("しらかば堂 フィナンシェ詰め合わせ 12個入" in n for n in ids)


def test_business_include_unknown_widens_and_marks_missing():
    strict = business()["total_candidates"]
    loose = business(include_unknown="true")
    assert loose["total_candidates"] > strict
    assert any("記載なし" in it["reason"] for it in loose["results"]) or loose["total_candidates"] > 100


def test_bad_mode():
    assert client.get("/api/search", params={"mode": "other"}).status_code == 400
