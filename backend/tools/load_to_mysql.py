# ─────────────────────────────────────────────
# load_to_mysql.py — giftia.db（SQLite）のデータを MySQL に移す（3周目）
# 対応する要件定義書: 8章（移行性）
#
# 使い方（backend/ で実行。.env に MySQL の接続情報を書いておく）:
#   python tools/load_to_mysql.py              # テーブルを作り直してデータを入れる（確認あり）
#   python tools/load_to_mysql.py --yes        # 確認を飛ばす
#   python tools/load_to_mysql.py --no-create  # テーブルは自分で作った（チームの DDL）ので、データだけ入れる
#
# ★作り直すと、そのDBのテーブルはすべて消える★
# DB の中のテーブルをすべて消し、schema_mysql.sql（チームが後ろに足したものも含む）のとおりに作り直す。
# 足したテーブルのデータは、自分たちのスクリプト（extract_facts.py など）で入れ直す。手で入れたデータは戻らない。
# チームで1つのDBを使うので、流すのは代表の1人だけにする。
#
# ★約28万件の注文を 1 行ずつ INSERT すると非常に遅い★
# ここでは 5,000 行ずつまとめて送る（executemany）。1 回の往復で多くの行を送るのが速さの鍵。
# 外部キーがあるので、参照される側（products・users）から順に入れる。
# ─────────────────────────────────────────────
import argparse
import os
import pathlib
import re
import sqlite3
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["USE_MYSQL"] = "true"
from database import get_connection  # noqa: E402

ORDER = ["products", "product_scenes", "users", "orders", "order_items", "reviews"]  # 配布データのテーブル
CHUNK = 5000
DDL_PATH = pathlib.Path(__file__).parent / "schema_mysql.sql"


def statements(ddl: str) -> list[str]:
    """schema_mysql.sql を、コメントを除いた文ごとに分ける。"""
    result = []
    for stmt in ddl.split(";"):
        body = "\n".join(line for line in stmt.splitlines() if not line.strip().startswith("--")).strip()
        if body:
            result.append(body)
    return result


def recreate_tables(cur, stmts: list[str]) -> None:
    """DB の中のテーブルをすべて消してから、DDL のとおりに作り直す。"""
    # DDL に書かれていないテーブル（extract_facts.py が作る product_facts など）が products を参照したまま残ると、
    # products の型を変えたときに作り直せなくなる。チーム専用の DB なので、中身は「DDL＋データを入れるスクリプト」から毎回作る
    cur.execute("SELECT TABLE_NAME AS t, TABLE_TYPE AS type FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()")
    existing = cur.fetchall()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")  # 参照し合っているテーブルを、順番を気にせず消すため
    for row in existing:
        cur.execute(f"DROP {'VIEW' if row['type'] == 'VIEW' else 'TABLE'} IF EXISTS `{row['t']}`")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    for body in stmts:
        cur.execute(body)
    tables = [m.group(1) for s in stmts if (m := re.match(r"CREATE TABLE\s+`?(\w+)`?", s, re.I))]
    print(f"消したテーブル: {', '.join(r['t'] for r in existing) or 'なし'}")
    print(f"作ったテーブル: {', '.join(tables)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", default=os.environ.get("SQLITE_PATH", "giftia.db"))
    ap.add_argument("--no-create", action="store_true")
    ap.add_argument("--yes", action="store_true", help="作り直す前の確認を飛ばす")
    args = ap.parse_args()

    if not os.path.exists(args.sqlite):
        sys.exit(f"SQLite のファイルが見つかりません: {args.sqlite}")
    src = sqlite3.connect(args.sqlite)
    dst = get_connection()
    cur = dst.cursor()
    target = f"{os.environ['DB_HOST']} / {os.environ['DB_NAME']}"

    if not args.no_create:
        if not args.yes:
            answer = input(f"{target} のテーブルをすべて消して作り直します。続けますか [y/N]: ")
            if answer.strip().lower() != "y":
                sys.exit("中止しました")
        recreate_tables(cur, statements(DDL_PATH.read_text(encoding="utf-8")))

    ok = True
    for table in ORDER:
        cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
        insert = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
        rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}")
        start = time.time()
        while batch := rows.fetchmany(CHUNK):
            cur.executemany(insert, batch)
        dst.commit()
        expected = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        actual = cur.fetchone()["n"]
        mark = "一致" if expected == actual else "★不一致"
        ok &= expected == actual
        print(f"{table:15s} SQLite {expected:>8,}行 → MySQL {actual:>8,}行  {mark}（{time.time() - start:.1f}秒）")
    dst.close()
    print(f"完了: {target}" if ok else "件数が一致しないテーブルがあります。上の★を確認してください")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
