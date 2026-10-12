# ─────────────────────────────────────────────
# extract_facts.py — 商品の「事実」を集めて product_facts テーブルに入れる（Cの版で使う）
# 対応する要件定義書: 5.2〜5.4（追加するデータ・どこに持たせたか・データ供給計画）
#
# 取引先へのお礼（ヒアリングC）では「常温で置けるか」「個包装か」「賞味期限は十分か」を確かめたい。
# でも、配布データの products にはその列がない。説明文の末尾の仕様欄に、書き方ばらばらで、一部の商品にだけ書かれている。
#
#   【保存方法】直射日光・高温多湿を避けて常温で保存
#   【賞味期限】製造日より90日
#   【包装】1個ずつ小袋入り
#
# そこで、このスクリプトで事実を取り出し、別テーブル product_facts に「値」と「出どころ（source）」を一緒に入れる。
#
#   product_facts(product_id, fact, value, source)
#     fact   : room_temp（常温で保存できる 1/0）／indiv_wrap（個包装 1/0）／shelf_life_days（日持ちの日数）
#              ／office_orders（直近1年の会社宛て注文数）
#     source : description_rule（説明文からルールで抽出）／orders（注文データから集計）
#
# 書かれていない事実は、行を作らない（「不明」と「いいえ」を区別するため）。
# products は変えない。新商品が入ったら、このスクリプトを流し直せばよい（データ供給計画）。
#
# 使い方（backend/ で実行）:
#   python tools/extract_facts.py         # .env の DB（SQLite または MySQL）に作る
# ─────────────────────────────────────────────
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from database import USE_MYSQL, get_connection, sql  # noqa: E402

DDL = """CREATE TABLE product_facts (
    product_id VARCHAR(10) NOT NULL,
    fact       VARCHAR(30) NOT NULL,
    value      INTEGER     NOT NULL,
    source     VARCHAR(30) NOT NULL,
    PRIMARY KEY (product_id, fact),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)"""


def spec_lines(description: str) -> list[str]:
    """説明文の末尾の仕様欄（【…】で始まる行）だけを取り出す。"""
    return [line.strip() for line in description.splitlines() if line.strip().startswith("【")]


def extract(description: str) -> dict[str, int]:
    """仕様欄から事実を取り出す。分からないものは入れない。"""
    facts = {}
    for line in spec_lines(description):
        if line.startswith("【保存方法】") or line.startswith("【配送】"):
            if re.search(r"要冷蔵|冷蔵庫|要冷凍|冷凍庫|冷凍便", line):
                facts["room_temp"] = 0
            elif re.search(r"常温|冷蔵不要|直射日光を避けて保存", line):
                facts["room_temp"] = 1
        elif line.startswith("【個包装】"):
            if "あり" in line:
                facts["indiv_wrap"] = 1
            elif "なし" in line:
                facts["indiv_wrap"] = 0
        elif line.startswith("【包装】"):
            if re.search(r"個包装|1個ずつ|小袋", line):
                facts["indiv_wrap"] = 1
            elif "まとめて" in line:
                facts["indiv_wrap"] = 0
        elif line.startswith("【賞味期限】") or line.startswith("【消費期限】"):
            if m := re.search(r"(?:製造日より|お届け日を含め)(\d+)日", line):
                facts["shelf_life_days"] = int(m.group(1))
            elif m := re.search(r"発送日から(\d+)日以上", line):
                facts["shelf_life_days"] = int(m.group(1))  # 「以上」なので下限の値を入れる
            elif m := re.search(r"約(\d+)か月", line):
                facts["shelf_life_days"] = int(m.group(1)) * 30
            elif m := re.search(r"約(\d+)週間", line):
                facts["shelf_life_days"] = int(m.group(1)) * 7
            # 「長め（パッケージに記載）」「到着後お早めに」は日数が分からないので入れない
    return facts


def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS product_facts")
    cur.execute(DDL + (" DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs" if USE_MYSQL else ""))

    cur.execute("SELECT product_id, description FROM products")
    rows = []
    for r in cur.fetchall():
        pid, desc = (r["product_id"], r["description"])
        rows += [(pid, fact, value, "description_rule") for fact, value in extract(desc).items()]

    # 会社宛ての注文数（直近1年）：取引先に贈られている実績。説明文ではなく注文データから集計する
    cur.execute(sql("""SELECT i.product_id, COUNT(DISTINCT o.order_id) AS n
                       FROM orders o JOIN order_items i ON i.order_id = o.order_id
                       WHERE o.ship_to_type = '会社' AND o.ordered_at >= ?
                       GROUP BY i.product_id"""), ("2025-07-01",))
    rows += [(r["product_id"], "office_orders", r["n"], "orders") for r in cur.fetchall()]

    cur.executemany(sql("INSERT INTO product_facts (product_id, fact, value, source) VALUES (?, ?, ?, ?)"), rows)
    conn.commit()
    cur.execute("SELECT fact, source, COUNT(*) AS n FROM product_facts GROUP BY fact, source ORDER BY fact")
    for r in cur.fetchall():
        print(f"{r['fact']}（{r['source']}）: {r['n']:,}件")
    conn.close()


if __name__ == "__main__":
    main()
