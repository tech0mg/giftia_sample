// API の返す形（backend/main.py と対応）。チームで項目を足したら、ここも足す

export type Product = {
  product_id: string;
  product_name: string;
  category: string;
  price: number;
  brand: string;
  size: string | null;
  delivery_days: number;
  gift_wrap: number;
  message_card: number;
  rating: number | null;
  review_count: number;
  sales_count: number;
  stock: number;
  registered_at: string;
  score: number;   // 順位付けに使った値（rank() が付ける）
  reason: string;  // 推薦理由（make_reason() か LLM が付ける）
  // 取引先へのお礼の版だけ付く（product_facts から。書かれていない事実は null）
  room_temp?: number | null;
  indiv_wrap?: number | null;
  shelf_life_days?: number | null;
  office_orders?: number | null;
};

export type SearchResponse = {
  total_candidates: number;
  results: Product[];
  reason_source: "template" | "llm";
  mode: "standard" | "business";
};

export type Meta = {
  categories: string[];
  scenes: string[];
  sorts: Record<string, string>;
  modes: Record<string, string>;
  llm: boolean;
};
