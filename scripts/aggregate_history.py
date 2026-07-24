#!/usr/bin/env python3
"""Aggregate 1-6 months of sales data into historical_data.json for the dashboard history tab."""

import pandas as pd
import json
import sys
import argparse
from pathlib import Path

EXCLUDE_CATS = {'服务', '手机配件', '家电', '健康美容', '电脑数码', 'solar system', '照明', '不需要'}

def clean_store_name(name):
    """Normalize store names like process_data.py does."""
    if not isinstance(name, str):
        return None
    name = name.strip()
    name = name.replace('\xa0', ' ')
    if name.startswith('D_'):
        name = name[2:]
    return name

def main():
    parser = argparse.ArgumentParser(description='Aggregate monthly sales data into historical_data.json')
    parser.add_argument('files', nargs='+', help='Monthly Excel files (e.g. 2026-1.xlsx 2026-2.xlsx ...)')
    parser.add_argument('--out', default='historical_data.json', help='Output JSON path')
    args = parser.parse_args()
    
    files = args.files
    out_path = args.out
    
    phone_sales = {}   # store -> { 'YYYY-MM': qty }
    revenue = {}       # store -> { 'YYYY-MM': amount }
    gross_profit = {}  # store -> { 'YYYY-MM': amount }
    brand_sales = {}    # brand -> { 'YYYY-MM': qty }
    
    for fpath in files:
        fname = Path(fpath).stem
        # Extract year-month from filename like "2026-1", "2026-6"
        parts = fname.split('-')
        if len(parts) >= 2:
            year, month = parts[0], parts[1].zfill(2)
        else:
            print(f"⚠ Skipping {fpath}: cannot parse YYYY-M from filename")
            continue
        
        ym = f"{year}-{month}"
        print(f"Processing {ym}: {fpath}")
        
        try:
            df = pd.read_excel(fpath)
        except Exception as e:
            print(f"  ❌ Error reading: {e}")
            continue
        
        # Filter: SMART + TABLET only, exclude non-phone categories
        df = df[df['统计分类'].isin(['智能机', '平板电脑'])]
        df = df[~df['统计分类'].isin(EXCLUDE_CATS)]
        df = df[df['销售数量'] > 0]
        
        # Clean store names
        df['store'] = df['销售部门'].apply(clean_store_name)
        df = df.dropna(subset=['store'])
        df = df[df['store'] != '']
        
        # Aggregate by store
        store_agg = df.groupby('store').agg(
            qty=('销售数量', 'sum'),
            rev=('零售金额', 'sum'),
            profit=('毛利', 'sum')
        )
        
        for store, row in store_agg.iterrows():
            phone_sales.setdefault(store, {})[ym] = float(row['qty'])
            revenue.setdefault(store, {})[ym] = float(row['rev'])
            gross_profit.setdefault(store, {})[ym] = float(row['profit'])
        
        # Aggregate by brand
        brand_agg = df.groupby('品牌').agg(qty=('销售数量', 'sum'))
        for brand, row in brand_agg.iterrows():
            if pd.isna(brand) or not isinstance(brand, str):
                continue
            b = brand.strip()
            if not b or b in ('SERVICE', 'nan'):
                continue
            brand_sales.setdefault(b, {})[ym] = float(row['qty'])
        
        total_qty = store_agg['qty'].sum()
        total_rev = store_agg['rev'].sum()
        total_profit = store_agg['profit'].sum()
        print(f"  ✅ {ym}: {total_qty:,.0f}台, ₦{total_rev/1e6:.1f}M 营收, ₦{total_profit/1e6:.1f}M 毛利, {len(store_agg)}门店, {len(brand_agg)}品牌")
    
    # Build monthly totals
    monthly_total_phone_sales = {}
    for store_months in phone_sales.values():
        for m, v in store_months.items():
            monthly_total_phone_sales[m] = monthly_total_phone_sales.get(m, 0) + v
    
    # YoY growth rates (compare 2026 vs 2025 if we have 2025 data, else None)
    yoy_growth_rates = {}
    sorted_months = sorted(monthly_total_phone_sales.keys())
    for m in sorted_months:
        parts = m.split('-')
        prev_m = f"{int(parts[0])-1}-{parts[1]}"
        prev_val = monthly_total_phone_sales.get(prev_m, 0)
        cur_val = monthly_total_phone_sales[m]
        if prev_val > 0:
            yoy_growth_rates[m] = round(((cur_val - prev_val) / prev_val) * 100, 1)
    
    # Build brand data by year
    brand_data = {}
    for brand, months in brand_sales.items():
        for m, v in months.items():
            year = m.split('-')[0]
            brand_data.setdefault(year, {}).setdefault(brand, {})[m] = v
    
    # Assemble output
    output = {
        "data": {
            "phone_sales": phone_sales,
            "revenue": revenue,
            "gross_profit": gross_profit,
        },
        "summaries": {
            "monthly_total_phone_sales": monthly_total_phone_sales,
            "yoy_growth_rates": yoy_growth_rates,
        },
        "brand_data": brand_data,
    }
    
    with open(out_path, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # Summary
    print(f"\n📊 历史数据已生成: {out_path}")
    print(f"   月份: {', '.join(sorted_months)}")
    print(f"   门店数: {len(phone_sales)}")
    print(f"   品牌数: {len(brand_sales)}")
    for m in sorted_months:
        total = monthly_total_phone_sales[m]
        yoy = yoy_growth_rates.get(m, 'N/A')
        print(f"   {m}: {total:,.0f}台 (YoY: {yoy}%)")

if __name__ == '__main__':
    main()
