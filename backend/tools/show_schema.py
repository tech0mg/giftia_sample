# ─────────────────────────────────────────────
# show_schema.py — MySQL に実際にあるテーブル・カラム・外部キー・行数を一覧にする（3周目）
# 対応する要件定義書: 5.1 ER図・5.2 追加するデータの定義・付録B（実装とのずれの確認）
#
# 使い方（backend/ で実行。.env に MySQL の接続情報を書いておく）:
#   python tools/show_schema.py
#
# 要件定義書の ER図 は Word に貼った画像なので、コードと自動ではそろわない。
# この一覧と ER図 を1行ずつ見比べて、ずれていたらどちらかを直す。
# ─────────────────────────────────────────────
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["USE_MYSQL"] = "true"
from database import fetch_all  # noqa: E402


def main():
    columns = fetch_all("""SELECT TABLE_NAME AS t, COLUMN_NAME AS c, COLUMN_TYPE AS type, IS_NULLABLE AS nullable, COLUMN_KEY AS k
                           FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()
                           ORDER BY TABLE_NAME, ORDINAL_POSITION""")
    fks = fetch_all("""SELECT TABLE_NAME AS t, COLUMN_NAME AS c, REFERENCED_TABLE_NAME AS rt, REFERENCED_COLUMN_NAME AS rc
                       FROM information_schema.KEY_COLUMN_USAGE
                       WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL""")
    ref = {(f["t"], f["c"]): f"→ {f['rt']}({f['rc']})" for f in fks}
    for table in dict.fromkeys(col["t"] for col in columns):
        n = fetch_all(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]
        print(f"\n■ {table}（{n:,}行）")
        for col in (c for c in columns if c["t"] == table):
            key = {"PRI": "PK", "MUL": "", "UNI": "UNIQUE"}.get(col["k"], "")
            null = "" if col["nullable"] == "YES" else "NOT NULL"
            print(f"  {col['c']:18s} {col['type']:14s} {key:6s} {null:8s} {ref.get((table, col['c']), '')}".rstrip())


if __name__ == "__main__":
    main()
