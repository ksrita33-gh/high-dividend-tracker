#!/usr/bin/env python3
"""
translate_names.py
stocks_list.csv から NAME_JA dict を生成し、
data/stocks.json の name / sector を日本語化する。
"""
import os
import csv
import json

SECTOR_JA = {
    "Financial Services": "金融サービス",
    "Basic Materials": "素材",
    "Energy": "エネルギー",
    "Industrials": "資本財・サービス",
    "Consumer Cyclical": "一般消費財・サービス",
    "Consumer Defensive": "生活必需品",
    "Healthcare": "ヘルスケア",
    "Technology": "情報技術",
    "Communication Services": "通信サービス",
    "Utilities": "公共事業",
    "Real Estate": "不動産",
    "Financial": "金融",
    "Transportation": "輸送",
    "Services": "サービス",
    "Manufacturing": "製造業",
    "Retail": "小売",
    "Construction": "建設",
    "Food & Beverages": "食品・飲料",
    "Chemicals": "化学",
    "Steel": "鉄鋼",
    "Shipping": "海運",
    "Trading Companies": "商社",
    "Banking": "銀行",
    "Insurance": "保険",
    "Automobiles": "自動車",
    "Machinery": "機械",
    "Pharmaceuticals": "医薬品",
    "Electric Power": "電力",
    "Gas": "ガス",
}


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "stocks_list.csv")
    json_path = os.path.join(base_dir, "data", "stocks.json")

    # NAME_JA dict を構築
    name_ja: dict[str, str] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            row = [c.strip() for c in row]
            if len(row) >= 2 and row[0]:
                name_ja[row[0]] = row[1]

    print("NAME_JA =", json.dumps(name_ja, ensure_ascii=False, indent=2))

    # stocks.json を更新
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for stock in data.get("stocks", []):
        code = stock.get("code", "")
        if code in name_ja:
            stock["name"] = name_ja[code]
            updated += 1
        raw_sector = stock.get("sector", "")
        if raw_sector in SECTOR_JA:
            stock["sector"] = SECTOR_JA[raw_sector]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{updated} 銘柄の名前を日本語化しました → {json_path}")


if __name__ == "__main__":
    main()
