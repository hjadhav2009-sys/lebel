export type Product = {
  id: string;
  marketplace: "Amazon" | "Flipkart";
  account: string;
  sku: string;
  asin?: string;
  fnsku?: string;
  fsn?: string;
  title: string;
  brand: string;
  mrp?: number;
  category: string;
  image?: string;
  updated: string;
  source: string;
};
