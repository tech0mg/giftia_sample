# ─────────────────────────────────────────────
# database.py — DB接続の抽象化
# 対応する要件定義書: 5章（データ設計）・7章（技術選定）・8章（移行性）
#
# USE_MYSQL 環境変数で SQLite / Azure Database for MySQL を切り替える
#   USE_MYSQL=false（デフォルト）→ SQLite（ローカル開発・配布の giftia.db）
#   USE_MYSQL=true               → Azure Database for MySQL（3周目以降）
#
# ★「DBが変わってもAPIは変わらない」設計のポイント★
# search.py などは get_connection() と sql() を使うだけで、
# 接続先がどちらでも同じコードが動く。
# ─────────────────────────────────────────────

import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()  # .env ファイルを読み込む

USE_MYSQL: bool = os.environ.get("USE_MYSQL", "false").lower() == "true"


def get_connection():
    """接続先を切り替えて返す。どちらも「行を dict のように扱える」接続にしてある。"""
    return _get_mysql_connection() if USE_MYSQL else _get_sqlite_connection()


def sql(query: str) -> str:
    """プレースホルダーをそろえる。SQLite は ?、MySQL（pymysql）は %s。"""
    return query.replace("?", "%s") if USE_MYSQL else query


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """SELECT を実行して、行を dict のリストで返す（JSON にそのまま変換できる形）。"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql(query), params)
        return [{k: _plain(v) for k, v in dict(row).items()} for row in cur.fetchall()]
    finally:
        conn.close()


def _plain(value):
    """MySQL の DECIMAL（Decimal）・DATE/DATETIME（date/datetime）を、SQLite と同じ float・文字列にそろえる。"""
    import datetime
    import decimal
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def _get_sqlite_connection() -> sqlite3.Connection:
    db_path = os.environ.get("SQLITE_PATH", "giftia.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"SQLite のファイルが見つかりません: {db_path}\n"
            "配布された giftia.db を backend/ に置くか、.env の SQLITE_PATH を直してください。"
        )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # カラム名でアクセスできるようにする
    return conn


def _get_mysql_connection():
    try:
        import pymysql
    except ImportError:
        raise ImportError("pymysql が見つかりません。'pip install pymysql' を実行してください。")

    required = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise EnvironmentError(f"以下の環境変数が設定されていません: {', '.join(missing)}")

    options = dict(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )
    # Azure Database for MySQL は SSL 必須。ローカルの MySQL で試すときだけ DB_SSL=false にする
    if os.environ.get("DB_SSL", "true").lower() == "true":
        options["ssl"] = {"ssl_disabled": False}
    return pymysql.connect(**options)


def get_db_type() -> str:
    """現在の接続先を返す（ヘルスチェック・ログ用）"""
    return "MySQL" if USE_MYSQL else "SQLite"
