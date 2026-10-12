# Giftia ギフト検索 — サンプルコード

Tech0 Step3-1 Giftia ケースの完成品サンプルです。講座と同じ構成で、**2つの検索を切り替えられる**ようにしてあります。

| モード | 中身 | ファイル |
| --- | --- | --- |
| **いまの検索** | Exhibit 3 の再現。キーワード・カテゴリー・価格帯・贈るシーンで絞り、キーワード一致度＋販売実績＋レビュー評価で並べる | `backend/search.py` |
| **取引先へのお礼** | ヒアリングCのJobを解いた実例。説明文で確かめられる商品（常温・個包装・賞味期限）だけを出し、「外さない」順に並べ、確かめた事実と出どころを理由に書く | `backend/search_business.py` |

どちらも、**ユーザーの入力を受ける → 候補を取る → 順位を付ける → 理由を付けて返す**（Exhibit 5 の必須処理）という同じ形で、**候補取得・順位付け・理由生成の3つの関数**だけが違います。

**これは答えではありません。** 「取引先へのお礼」はCのJobの一例です。同じ顧客を選ぶチームも、順位の付け方と理由の書き方は自分たちで決めてください。自分たちのJobに合わせて、3つの関数を差し替えるのがこのサンプルの使い方です。

```
ブラウザ ─┬─ Next.js（画面のアプリ）     画面のファイルを受け取る
          └─ FastAPI（API のアプリ） ─┬─ SQLite（ローカル）
             ブラウザから直接呼ぶ      ├─ Azure Database for MySQL（3周目以降）
                                       └─ OpenAI API（任意・4周目）
Azure では、どちらも App Service の Web アプリ（チームごとに画面1つ・API 1つ）
```

**ログインと会員の機能はありません。** 配布データの会員（`users`）は年代・性別・登録日だけを持つ分析用のデータで、名前・メールアドレス・パスワードはどこにもありません。会員の注文履歴（ヒアリングEの「毎年同じ贈りもの」など）は、画面ではなく DB を直接調べて分析します。

## フォルダ構成

```
backend/
  main.py           API の入口（エンドポイント一覧。mode で2つの検索を切り替える）
  search.py         ★いまの検索：候補取得 find_candidates()／順位付け rank()／理由生成 make_reason()
  search_business.py ★取引先へのお礼：同じ3関数を、Cの Job に合わせて書き換えたもの
  llm.py            推薦理由を LLM で作る（任意）
  database.py       SQLite／MySQL の切り替え
  tools/            MySQL へ移す（schema_mysql.sql・load_to_mysql.py）・テーブルの一覧を出す（show_schema.py）（3周目）
                    説明文と注文データから事実を集めて product_facts を作る（extract_facts.py）
  tests/            pytest
frontend/
  app/page.tsx      画面
  app/components/   検索フォーム・結果カード
  lib/api.ts        API を呼ぶ関数
  public/placeholders/  カテゴリー別の仮画像（商品画像は配布DBに含まれない）
```

## 週ごとの使い方

| 周 | 使うところ |
| --- | --- |
| 2周目 | `backend/` を SQLite で動かし、`frontend/` から直接呼ぶ（CORS が必要な構成。Azure に載せても同じ形） |
| 3周目 | `backend/tools/` で MySQL に移し、`USE_MYSQL=true` で同じ API が動くことを確かめる。自チームのテーブルは `schema_mysql.sql` の後ろに足す。`load_to_mysql.py` は DB のテーブルをすべて消して作り直すので、MySQL で `product_facts` を使うときは続けて `extract_facts.py` を流す |
| 4周目 | 3関数を、自チームのランキング・推薦理由に差し替える（`search.py` と `search_business.py` の違いが見本）。LLM を使うなら `llm.py` |
| 5周目 | 画面と API を、それぞれ App Service の Web アプリにデプロイする（下の「Azure に載せる」） |

## ローカルで動かす

### 1. バックエンド（FastAPI）

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
cp /どこか/配布データ/giftia.db .       # 配布された giftia.db を置く（62MB。GitHub にコミットしない）
python tools/extract_facts.py           # 「取引先へのお礼」が使う product_facts を作る（配布DBには入っていない）
uvicorn main:app --reload
```

`giftia.db` はリポジトリの外に置いてもかまいません。そのときは `.env` に `SQLITE_PATH=/どこか/giftia.db` と書きます（テストを流すときは `SQLITE_PATH=/どこか/giftia.db pytest -q`）。

http://localhost:8000/docs で API を試せます。

### 2. フロントエンド（Next.js）

```bash
cd frontend
npm install
cp .env.local.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

http://localhost:3000 を開きます。

### 3. 本番と同じ起動方法で試す（任意）

Azure では `next dev` ではなく、ビルドしてから `next start` で動かします。手元で同じ形を試すときは次のとおりです。

```bash
cd frontend
npm run build                           # このとき .env.local の NEXT_PUBLIC_API_URL が画面のコードに埋め込まれる
npm start                               # http://localhost:3000
```

## Azure に載せる（5周目）

チームごとに、App Service の Web アプリを2つ作ります。App Service プラン（仮想マシン）は講師が用意したものを、いくつかのチームで共有します。

| アプリ | 名前の例 | ランタイム | 起動のしかた |
| --- | --- | --- | --- |
| 画面 | `team01-web` | Node.js 22 LTS | `npm start`（`next start`。既定のまま） |
| API | `team01-api` | Python 3.12 | スタートアップコマンドに `gunicorn -w 2 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0 --timeout 120 main:app` |

それぞれのアプリの「環境変数（アプリ設定）」に、次の値を入れます。**`.env` や `.env.local` はアップロードしません。**

| アプリ | 名前 | 値 |
| --- | --- | --- |
| 画面 | `NEXT_PUBLIC_API_URL` | API の URL（`https://team01-api.azurewebsites.net`）。**ビルドのときに読まれる**ので、デプロイより先に入れる |
| 画面・API | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true`（Azure 側で `npm install`・`npm run build`／`pip install` をさせる） |
| API | `CORS_ORIGINS` | 画面の URL（`https://team01-web.azurewebsites.net`）。入れないと、画面から API を呼べない |
| API | `USE_MYSQL`・`DB_HOST`・`DB_USER`・`DB_PASSWORD`・`DB_NAME` | 3周目に使ったクラスの MySQL の接続情報（`USE_MYSQL=true`） |
| API | `OPENAI_API_KEY`・`OPENAI_MODEL` | LLM を使うときだけ |

確かめること：

- `https://team01-api.azurewebsites.net/api/health` が `"db": "MySQL"` を返す
- `https://team01-web.azurewebsites.net` で検索すると結果が出る（出ないときは、ブラウザの開発者ツールのコンソールで CORS のエラーが出ていないかを見る）

## テスト

```bash
cd backend
pytest -q                                # SQLite（giftia.db）で確かめる
USE_MYSQL=true pytest -q                 # MySQL に移したあと、同じテストを流す（.env に接続情報）
```

テストは、Exhibit 3 の検索件数（約180件・約70件）や、ヒアリングの A（送別ランキング1位・2位）・C（購入した焼き菓子が候補に出る）が API から見えること、E（毎年同じ贈りもの）が DB に入っていることも確かめています。

## 「取引先へのお礼」のデータ設計（`product_facts`）

Cが確かめたかったこと（常温・個包装・賞味期限）は、`products` に列がありません。説明文の末尾の仕様欄に、書き方ばらばらで、一部の商品にだけ書かれています。

```
【保存方法】直射日光・高温多湿を避けて常温で保存
【賞味期限】製造日より90日
【包装】1個ずつ小袋入り
```

`tools/extract_facts.py` は、ここから事実を取り出して別テーブルに入れます。

```
product_facts(product_id, fact, value, source)
  fact   : room_temp / indiv_wrap / shelf_life_days / office_orders
  source : description_rule（説明文からルールで抽出）／orders（注文データから集計）
```

- **書かれていない事実は行を作りません。**「いいえ」と「分からない」を区別するためです。検索では、確かめられた商品だけを出し（既定）、理由には「記載なし」と正直に書きます
- **`products` は変えません。** 新商品が入ったら、このスクリプトを流し直します（データ供給計画）
- 会社宛ての注文数は説明文になく、注文データから数えています。出どころを `source` に残すと、「誰が・どうやって付けたか」を後から説明できます

## 守ること（セキュリティ）

- **キーとパスワードを GitHub にコミットしない。** `.env`・`.env.local` は `.gitignore` 済み。本番の値は Azure のアプリ設定に置く
- **`NEXT_PUBLIC_` の値はブラウザに配られる。** API キーを置かない。OpenAI API は FastAPI 側からだけ呼ぶ
- **API はインターネットの誰からでも呼べる。** 画面を通さずに直接呼ばれても困らないものだけを返す（いまは商品の公開情報だけ）。LLM を使う検索は呼ばれるたびに料金がかかるので、キーには利用額の上限を付ける
- **会員の個人情報は持たない・送らない。** LLM に送るのは検索条件と商品の公開情報だけ

## 講師向けメモ

- 2026-10-12：新企画 2 から作り直し。**ログイン（SWA の組み込み認証）と会員の API（`/api/me`・`/api/me/orders`）を外し、Static Web Apps＋Functions から App Service の Web アプリ2つ（画面・API）に変更**（講義設計書 決定#37）。外したファイル：`auth.py`・`function_app.py`・`host.json`・`.funcignore`・`local.settings.json.example`・`LoginBar.tsx`・`OrderHistory.tsx`・`staticwebapp.config.json`。ヒアリングEのテストは API ではなく DB を直接確かめる形に変更
- 動作確認済み（2026-10-12）：pytest 17件（SQLite）、`next build`＋`next start` と `uvicorn` を別ポートで起動し、画面から API を呼べること（CORS で画面のオリジンだけ許可されること）、`/api/me` が 404 になること
- **未確認：Azure 上での App Service へのデプロイ一式**（`SCM_DO_BUILD_DURING_DEPLOYMENT` でのビルド、ビルド時に `NEXT_PUBLIC_API_URL` がアプリ設定から読まれること、gunicorn での起動）。MySQL 8.4 でのテストも新企画 3 では未実施
- **開講前の作業：** 講師側で動作確認した環境で `pip freeze` を取り、`backend/requirements.txt` を `==` 指定に書き換えて固める（決定ログ 仮8）
- 抽出ルールの精度は `新企画/_講師専用/data_design/check_extractor.py` で確認できる（2026-09-23：常温・個包装・日持ちとも、抽出できたものの正しさ100%。正解に値がある商品のうち抽出できたのは 56%・46%・30%）。残りは説明文に書かれていない分で、ここをどう埋めるかがチームのデータ供給計画の論点
- 2026-09-30：`tools/` の4ファイル（`schema_mysql.sql`・`load_to_mysql.py`・`extract_facts.py`・`show_schema.py`）は、3周目の手順書モジュールの配布コードの**正**。直したら `python3 _講師専用/sync_module_code.py` で手順書側に写す（`--check` でずれを確かめられる）
- 2026-09-30：照合順序を `utf8mb4_ja_0900_as_cs` に固定（決定#34）。`load_to_mysql.py` を「DB のテーブルをすべて消して作り直す」形に変更（DDL にないテーブルが `products` を参照していると作り直せなかったため）。pytest 19件を MySQL 8.4・SQLite の両方で再確認
- LLM は `OPENAI_API_KEY` と `OPENAI_MODEL` が両方あるときだけ動く。モデル名は講師がキーと一緒に配布する（既定値は置いていない）
