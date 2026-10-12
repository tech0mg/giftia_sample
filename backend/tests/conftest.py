# テストは配布データ（giftia.db）を読み取るだけ。書き込みはしない。
# giftia.db の場所は環境変数 SQLITE_PATH で指定する（既定：backend/giftia.db）
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
# 配布の giftia.db は変えない。一時フォルダに写して、Cの版が使う product_facts を作ってからテストする
if os.environ.get("USE_MYSQL", "false").lower() != "true":
    import shutil
    import subprocess
    import tempfile
    src = os.environ.get("SQLITE_PATH", str(HERE.parent / "giftia.db"))
    tmp = os.path.join(tempfile.mkdtemp(), "giftia_test.db")
    shutil.copy(src, tmp)
    os.environ["SQLITE_PATH"] = tmp
    subprocess.run([sys.executable, str(HERE.parent / "tools" / "extract_facts.py")], check=True, capture_output=True,
                   env={**os.environ, "USE_MYSQL": "false"})
os.environ.setdefault("USE_MYSQL", "false")  # USE_MYSQL=true pytest で、MySQL に移したあとの同じテストを流せる
os.environ.pop("OPENAI_API_KEY", None)
