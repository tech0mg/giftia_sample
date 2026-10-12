-- ─────────────────────────────────────────────
-- schema_mysql.sql — 配布データ（giftia.db）の基本テーブルを MySQL で作る（3周目）
-- 対応する要件定義書: 5章（データ設計）・8章（移行性）
--
-- 配布の schema.sql（SQLite）を MySQL の型に置き換えたもの。
-- チームで足すテーブル・カラム・索引は、このファイルの後ろに自分たちで書き足す。
-- 文字コードは utf8mb4（日本語・絵文字を扱える）。
-- 照合順序（文字の比べ方）は utf8mb4_ja_0900_as_cs（日本語用）に固定する。環境の既定に任せると、ローカルと Azure で検索結果が変わりうるため。
--   ひらがな／カタカナは同じと見る（「たおる」でも「タオル」が見つかる）。濁点・半濁点は区別する（「パン」で「ハンカチ」は見つからない）。
--   英字の大文字・小文字は区別する（「lino」では「Lino」が見つからない）。
--   MySQL の既定（utf8mb4_0900_ai_ci）は濁点まで同じと見るので、「パン」の検索に「ハンドクリーム」が混ざる。
--   SQLite の LIKE は書かれた文字どおりに比べる（英字の大文字・小文字だけは同じと見る）。どの比べ方を望むかは、要件定義書 8章に書く。
-- ─────────────────────────────────────────────

CREATE TABLE products (
    product_id    VARCHAR(10)  PRIMARY KEY,
    product_name  VARCHAR(100) NOT NULL,
    category      VARCHAR(30)  NOT NULL,
    price         INT          NOT NULL,
    brand         VARCHAR(50)  NOT NULL,
    description   TEXT         NOT NULL,
    size          VARCHAR(100),
    delivery_days INT          NOT NULL,
    gift_wrap     TINYINT(1)   NOT NULL,
    message_card  TINYINT(1)   NOT NULL,
    rating        DECIMAL(2,1),                -- レビューがなければ NULL
    review_count  INT          NOT NULL,
    sales_count   INT          NOT NULL,       -- 直近1年の販売個数
    stock         INT          NOT NULL,
    registered_at DATE         NOT NULL
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

CREATE TABLE product_scenes (
    product_id VARCHAR(10) NOT NULL,
    scene_tag  VARCHAR(20) NOT NULL,
    PRIMARY KEY (product_id, scene_tag),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

CREATE TABLE users (
    user_id       VARCHAR(20) PRIMARY KEY,
    age_group     VARCHAR(10) NOT NULL,
    gender        VARCHAR(10) NOT NULL,
    registered_at DATE        NOT NULL
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

CREATE TABLE orders (
    order_id        VARCHAR(12) PRIMARY KEY,
    user_id         VARCHAR(20) NOT NULL,
    ordered_at      DATETIME    NOT NULL,
    gift_purpose    VARCHAR(20),               -- 未選択は NULL
    estimated_scene VARCHAR(20) NOT NULL,
    recipient_key   VARCHAR(16) NOT NULL,
    ship_to_type    VARCHAR(10) NOT NULL,
    total_amount    INT         NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

CREATE TABLE order_items (
    order_id   VARCHAR(12) NOT NULL,
    line_no    INT         NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    quantity   INT         NOT NULL,
    unit_price INT         NOT NULL,
    PRIMARY KEY (order_id, line_no),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;

CREATE TABLE reviews (
    review_id  VARCHAR(12) PRIMARY KEY,
    product_id VARCHAR(10) NOT NULL,
    user_id    VARCHAR(20) NOT NULL,
    rating     INT         NOT NULL,
    comment    TEXT,                           -- 星だけのレビューは NULL
    posted_at  DATE        NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_ja_0900_as_cs;
