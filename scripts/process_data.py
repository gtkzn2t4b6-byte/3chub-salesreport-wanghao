#!/usr/bin/env python3
"""Sales Dashboard Data Processor - June 2026"""
import argparse
import pandas as pd
import json, warnings
warnings.filterwarnings('ignore')

# ========== 0. PARSE ARGUMENTS ==========
parser = argparse.ArgumentParser(description='Sales Dashboard Data Processor - June 2026')
parser.add_argument('--june', required=True, help='Path to June sales Excel file')
parser.add_argument('--may', required=True, help='Path to May sales Excel file')
parser.add_argument('--inventory', required=True, help='Path to inventory Excel file')
parser.add_argument('--targets', required=True, help='Path to targets Excel file (contains 手机 and 配件 sheets)')
parser.add_argument('--out', default='dashboard_full.json', help='Output JSON file path (default: dashboard_full.json)')
parser.add_argument('--mapping', default=None, help='Path to store-warehouse mapping Excel file (optional, auto-detected if omitted)')
parser.add_argument('--cost', default=None, help='Path to batch purchase cost Excel file (optional)')
parser.add_argument('--price-list', default=None, help='Path to retail price list Excel file (optional, for model price & price tier)')
parser.add_argument('--price-list-compare', default=None, help='Path to previous month retail price list Excel file (optional, for price change analysis)')
args = parser.parse_args()

# ========== HELPER: normalize non-breaking spaces ==========
def normalize_spaces(df):
    """Replace \xa0 (non-breaking space) with regular space in all object columns."""
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.replace('\xa0', ' ') if isinstance(x, str) else x)
    return df

# ========== 1. LOAD DATA ==========
print("Loading data...")
june_raw = pd.read_excel(args.june)
june = normalize_spaces(june_raw)

may_raw = pd.read_excel(args.may)
may = normalize_spaces(may_raw)

tgt_phone_raw = pd.read_excel(args.targets, sheet_name='手机')
tgt_phone = normalize_spaces(tgt_phone_raw)

tgt_acc_raw = pd.read_excel(args.targets, sheet_name='配件')
tgt_acc = normalize_spaces(tgt_acc_raw)

inv_raw = pd.read_excel(args.inventory)
# Auto-detect the correct sheet if first sheet lacks '仓库' column
if '仓库' not in inv_raw.columns:
    xl = pd.ExcelFile(args.inventory)
    for sheet in xl.sheet_names:
        tmp = pd.read_excel(xl, sheet)
        if '仓库' in tmp.columns:
            inv_raw = tmp
            break
inv = normalize_spaces(inv_raw)

# Clean inventory: remove total rows (NaN warehouse)
inv = inv.dropna(subset=['仓库'])
# 可卖数 = sellable stock (original column from inventory file)
# 三级账 = total stock (sellable + in-transit)
# 在途 = 三级账 - 可卖数 (in-transit / not yet received)
inv['可卖数'] = inv['可卖数'].fillna(0)
inv['三级账'] = inv['三级账'].fillna(0)
inv['在途'] = inv['三级账'] - inv['可卖数']

# ========== 1b. LOAD COST DATA (batch purchase costs) ==========
if args.cost:
    print("Loading cost data...")
    cost_raw = pd.read_excel(args.cost)
    cost = normalize_spaces(cost_raw)
    cost['进货日期'] = pd.to_datetime(cost['进货日期'], errors='coerce')
    cost['结存数量'] = cost['结存数量'].fillna(0)
    cost['含税进货单价'] = cost['含税进货单价'].fillna(0)
    cost['无税进货单价'] = cost['无税进货单价'].fillna(0)
else:
    cost = None

# Clean dates
june['记账日期'] = pd.to_datetime(june['记账日期'])
may['记账日期'] = pd.to_datetime(may['记账日期'])

# ========== 2. STORE MAPPING ==========
# Build mapping from sales dept -> short name -> inventory warehouse
store_map = dict(zip(tgt_acc['销售部门'], tgt_acc['SHOP']))

# Manual fixes for unmatched stores
manual_map = {
    'D_NEW AWOLOWO-IKEJA- LAGOS': 'NEW AWOLOWO',
    'D_IKORODU2-IKORODU GARAGE-LAGOS': 'IKORODU2',
    'D_ONITSHA-MAIN MARKET RD-ONITSHA ANAMBRA STATE': 'ONITSHA',
    'D_NNEWI-ONITSHA-ANAMBRA': 'ONITSHA',
    'D_IKOTUN3-IKOTUN-IDIMU ROAD IKOTUN LAGOS STATE': 'IKOTUN3',
    'D_MSL AWKA-ZIK AVENUE-DIKE PARK-AWKA ANAMBRA STATE': 'MSL AWKA',
    'D_ABA-ST. MICHAEL ROAD OFF ASA- ABA-ABIASTATE': 'ABA',
    'D_AGEGE-OBAOGUNJI RD PENCINIMA-AGEGE-LAGOS': 'AGEGE',
    'D_OJUORE-IDI-IROKO ROAD-OTA OGUN STATE': 'OJUORE',
    'D_PALMPAY/3CHUB-OLD YABA RD-EBUTE METTA LAGOS': 'PALMPAY/3CHUB',
    # Fix target file typos - SABO misspelled as SABA in target SHOP column
    'D_SABO-COMMERCIAL-YABA-LAGOS': 'SABO',
    'D_MSL SABO-COMMERCIAL-YABA-LAGOS': 'MSL SABO',
}
store_map.update(manual_map)

# Load authoritative store-warehouse mapping from reference file
# This is the SINGLE SOURCE OF TRUTH for sales dept <-> warehouse mapping
# Pattern: sales dept "D_XXX-..." -> warehouse "XXX-PHONES"
print("Loading store-warehouse mapping file...")
DEPT_TO_WAREHOUSE = {}  # sales dept -> PHONES warehouse name
try:
    map_df = pd.read_excel(args.mapping if args.mapping else '/Users/wanghao/Desktop/店名和仓库名.xlsx')
    map_df = normalize_spaces(map_df)
    phones_map = map_df[map_df['仓库名称'].str.contains('PHONES', na=False)].copy()
    for _, r in phones_map.iterrows():
        dept = r['销售部门']
        wh = r['仓库名称']
        if pd.notna(dept) and dept not in DEPT_TO_WAREHOUSE:
            DEPT_TO_WAREHOUSE[dept] = wh
    WAREHOUSE_TO_DEPT = {wh: dept for dept, wh in DEPT_TO_WAREHOUSE.items()}
    # Fallback for known warehouses not in mapping file
    WAREHOUSE_FALLBACK = {
        'ILORIN-PHONES': 'D_ILORIN2-IBRAHIM TAIWO RD-KWARA',
        'PALMPAY/3CHUB-PHONES': 'D_PALMPAY/3CHUB-OLD YABA RD-EBUTE METTA LAGOS',
    }
    WAREHOUSE_TO_DEPT.update(WAREHOUSE_FALLBACK)
    print(f"  Loaded {len(DEPT_TO_WAREHOUSE)} dept-warehouse mappings from file")
except Exception as e:
    print(f"  Warning: could not load mapping file: {e}")
    DEPT_TO_WAREHOUSE = {}
    WAREHOUSE_TO_DEPT = {}

# Phone target: store -> target
phone_target = {}
for _, r in tgt_phone.iterrows():
    if r['门店'] == '合计':
        continue
    phone_target[r['门店']] = r['任务']
TOTAL_TARGET = tgt_phone.iloc[0]['任务']  # 合计 row

# ========== 3. FILTER RELEVANT CATEGORIES ==========
# Statistical categories
CAT_SMART = '智能机'
CAT_TABLET = '平板电脑'
CAT_FEATURE = '功能机'

def filter_cat(df, cats):
    return df[df['统计分类'].isin(cats)]

june_smart = june[june['统计分类'] == CAT_SMART]
june_tablet = june[june['统计分类'] == CAT_TABLET]
june_feature = june[june['统计分类'] == CAT_FEATURE]
june_smart_combo = filter_cat(june, [CAT_SMART, CAT_TABLET])  # 智能机合计

# Determine current month dynamically from the data
june_max_date = june['记账日期'].max()
curr_month = june_max_date.month
curr_year = 2026
curr_start = pd.Timestamp(year=curr_year, month=curr_month, day=1)
curr_end = curr_start + pd.offsets.MonthEnd(0)

# Comparison month (from --may file)
may_max_date = may['记账日期'].max()
compare_month = may_max_date.month
compare_start = pd.Timestamp(year=curr_year, month=compare_month, day=1)
compare_end = compare_start + pd.offsets.MonthEnd(0)

# May comparison month: filter to full month
may_full = may[(may['记账日期'] >= compare_start) & (may['记账日期'] <= compare_end)]
may_smart = may_full[may_full['统计分类'] == CAT_SMART]
may_tablet = may_full[may_full['统计分类'] == CAT_TABLET]
may_smart_combo = filter_cat(may_full, [CAT_SMART, CAT_TABLET])

# ========== 4. CORE METRICS ==========
# Business days calculation (exclude Sundays)
june_all_dates = pd.date_range(curr_start, curr_end)
june_biz_dates = [d for d in june_all_dates if d.weekday() != 6]
JUNE_ELAPSED_BIZ = len([d for d in june_biz_dates if d <= june_max_date])
JUNE_REMAINING_BIZ = len([d for d in june_biz_dates if d > june_max_date])
TOTAL_BIZ_DAYS = len(june_biz_dates)  # Actual business days in current month

may_all_dates = pd.date_range(compare_start, compare_end)
may_biz_dates = [d for d in may_all_dates if d.weekday() != 6]
# Comparison: match same number of business days as current month elapsed
may_biz_compare = may_biz_dates[:JUNE_ELAPSED_BIZ]
may_smart_qty_biz = may_smart_combo[may_smart_combo['记账日期'].isin(may_biz_compare)]['销售数量'].sum()

TOTAL_DAYS_IN_MONTH = TOTAL_BIZ_DAYS  # Actual business days in current month
ELAPSED_DAYS = JUNE_ELAPSED_BIZ
REMAINING_DAYS = JUNE_REMAINING_BIZ

june_smart_qty = june_smart_combo['销售数量'].sum()
june_feature_qty = june_feature['销售数量'].sum()
june_all_qty = june_smart_qty + june_feature_qty
june_total_revenue = june['零售金额'].sum()
june_total_profit = june['毛利'].sum()

may_smart_qty = may_smart_combo['销售数量'].sum()
may_feature_qty = may_full[may_full['统计分类'] == CAT_FEATURE]['销售数量'].sum()

# Daily stats
daily = june.groupby('记账日期').agg(
    smart_qty=('销售数量', lambda x: x[june.loc[x.index, '统计分类'].isin([CAT_SMART, CAT_TABLET])].sum()),
    feature_qty=('销售数量', lambda x: x[june.loc[x.index, '统计分类'] == CAT_FEATURE].sum()),
    revenue=('零售金额', 'sum'),
    profit=('毛利', 'sum'),
    orders=('商品名称', 'count')
).reset_index().sort_values('记账日期')
daily['total_qty'] = daily['smart_qty'] + daily['feature_qty']
daily['date_str'] = daily['记账日期'].dt.strftime('%m-%d')

# May daily for comparison
may_daily = may_full.groupby('记账日期').agg(
    smart_qty=('销售数量', lambda x: x[may_full.loc[x.index, '统计分类'].isin([CAT_SMART, CAT_TABLET])].sum()),
    total_qty=('销售数量', 'sum')
).reset_index().sort_values('记账日期')

print(f"June smart combo qty: {june_smart_qty:.0f}, Feature: {june_feature_qty:.0f}")
print(f"May smart combo qty (full month): {may_smart_qty:.0f}")
print(f"Total target: {TOTAL_TARGET:.0f}")

# ========== MODULE 1: STORE SMART PHONE TARGET COMPLETION ==========
print("\nModule 1: Store target completion...")
store_perf = []
for dept, target in phone_target.items():
    s_data = june_smart_combo[june_smart_combo['销售部门'] == dept]
    qty = s_data['销售数量'].sum()
    rate = qty / target * 100 if target > 0 else 0
    remaining = max(0, target - qty)
    daily_need = remaining / REMAINING_DAYS if REMAINING_DAYS > 0 else 0

    # Comparison month (same business days)
    may_data_biz = may_smart_combo[may_smart_combo['记账日期'].isin(may_biz_compare)]
    m_data = may_data_biz[may_data_biz['销售部门'] == dept]
    may_qty = m_data['销售数量'].sum()
    may_rate = may_qty / target * 100 if target > 0 else 0
    mom_change = rate - may_rate

    store_perf.append({
        'dept': dept, 'short': store_map.get(dept, dept.split('-')[1][:15] if '-' in dept else dept[:15]),
        'target': round(target, 1), 'qty': round(qty, 1),
        'rate': round(rate, 1), 'remaining': round(remaining, 1),
        'daily_need': round(daily_need, 1),
        'may_rate': round(may_rate, 1), 'mom': round(mom_change, 1)
    })

store_perf.sort(key=lambda x: x['rate'], reverse=True)

# Tier classification (time-progress-aware)
# Expected completion rate at current time: elapsed / total business days
time_progress = JUNE_ELAPSED_BIZ / TOTAL_BIZ_DAYS if TOTAL_BIZ_DAYS > 0 else 0
expected_rate = time_progress * 100
for s in store_perf:
    if s['rate'] >= expected_rate * 1.1:
        s['tier'] = '超额'
        s['tier_color'] = '#22c55e'
    elif s['rate'] >= expected_rate * 0.75:
        s['tier'] = '达标'
        s['tier_color'] = '#3b82f6'
    elif s['rate'] >= expected_rate * 0.5:
        s['tier'] = '预警'
        s['tier_color'] = '#f59e0b'
    else:
        s['tier'] = '严重滞后'
        s['tier_color'] = '#ef4444'

# Tier summary for report cards
tier_order = ['超额', '达标', '预警', '严重滞后']
m1_tier_summary = []
for tier_name in tier_order:
    stores_in_tier = [s for s in store_perf if s['tier'] == tier_name]
    if not stores_in_tier:
        continue
    total_qty = sum(s['qty'] for s in stores_in_tier)
    total_target = sum(s['target'] for s in stores_in_tier)
    avg_rate = round(total_qty / total_target * 100, 1) if total_target > 0 else 0
    m1_tier_summary.append({
        'tier': tier_name,
        'count': len(stores_in_tier),
        'total_qty': round(total_qty, 0),
        'total_target': round(total_target, 0),
        'avg_rate': avg_rate,
        'color': stores_in_tier[0]['tier_color'],
        'stores': [s['short'] for s in stores_in_tier]
    })

tier_info = ', '.join(f'{t["tier"]}{t["count"]}家' for t in m1_tier_summary)
print(f"  Tier summary: {tier_info}")

# ========== MODULE 2: STORE TOTAL CATEGORY SALES ==========
print("Module 2: Store total category sales...")
store_cat = []
for dept in june['销售部门'].dropna().unique():
    sd = june[june['销售部门'] == dept]
    sq = sd[sd['统计分类'].isin([CAT_SMART, CAT_TABLET])]['销售数量'].sum()
    fq = sd[sd['统计分类'] == CAT_FEATURE]['销售数量'].sum()
    total = sq + fq
    if total > 0:
        store_cat.append({
            'dept': dept,
            'short': store_map.get(dept, dept.split('-')[1][:15] if '-' in dept else dept[:15]),
            'smart_qty': round(sq, 1), 'feature_qty': round(fq, 1),
            'total_qty': round(total, 1),
            'smart_pct': round(sq/total*100, 1) if total > 0 else 0
        })
store_cat.sort(key=lambda x: x['total_qty'], reverse=True)

# ========== MODULE 3: BRAND ANALYSIS ==========
print("Module 3: Brand analysis...")
june_brands = june_smart_combo.groupby('品牌').agg(
    qty=('销售数量', 'sum'), revenue=('零售金额', 'sum'), profit=('毛利', 'sum')
).reset_index().sort_values('qty', ascending=False)
# Brand profit rate & avg price & unit profit
june_brands['profit_rate'] = (june_brands['profit'] / june_brands['revenue'] * 100).round(1)
june_brands['profit_rate'] = june_brands['profit_rate'].fillna(0)
june_brands['avg_price'] = (june_brands['revenue'] / june_brands['qty']).round(0)
june_brands['avg_price'] = june_brands['avg_price'].fillna(0)
june_brands['unit_profit'] = (june_brands['profit'] / june_brands['qty']).round(0)
june_brands['unit_profit'] = june_brands['unit_profit'].fillna(0)

may_brands = may_smart_combo[may_smart_combo['记账日期'].isin(may_biz_compare)].groupby('品牌').agg(qty=('销售数量', 'sum')).reset_index()
may_brands.columns = ['品牌', 'may_qty']

june_brands = june_brands.merge(may_brands, on='品牌', how='left')
june_brands['may_qty'] = june_brands['may_qty'].fillna(0)
june_brands['mom_pct'] = ((june_brands['qty'] - june_brands['may_qty']) / june_brands['may_qty'] * 100).round(1)
june_brands['mom_pct'] = june_brands['mom_pct'].replace([float('inf'), float('-inf')], 9999)

# ========== MODULE 4: STORE DAILY DETAIL (TODAY = last date in data) ==========
print("Module 4: Store daily detail...")
today = june['记账日期'].max()
today_str = today.strftime('%Y-%m-%d')
# Find previous available date (not just -1 day, since data may skip dates)
all_dates = sorted(june['记账日期'].dropna().unique())
yesterday = all_dates[all_dates.index(today) - 1] if today in all_dates and all_dates.index(today) > 0 else None

today_data = june[june['记账日期'] == today]
store_daily = []
for dept in today_data['销售部门'].dropna().unique():
    sd = today_data[today_data['销售部门'] == dept]
    sq = sd[sd['统计分类'].isin([CAT_SMART, CAT_TABLET])]['销售数量'].sum()
    tq = sd[sd['统计分类'] == CAT_TABLET]['销售数量'].sum()
    fq = sd[sd['统计分类'] == CAT_FEATURE]['销售数量'].sum()
    total = sq + fq

    # Daily target = monthly target / 30
    tgt = phone_target.get(dept, 0)
    daily_tgt = tgt / TOTAL_DAYS_IN_MONTH
    daily_tgt_int = round(daily_tgt)  # 四舍五入取整数，避免浮点比较误差

    # Yesterday comparison (use previous available date)
    yd_sq = 0
    if yesterday is not None:
        yd_data = june[(june['记账日期'] == yesterday) & (june['销售部门'] == dept)]
        yd_sq = yd_data[yd_data['统计分类'].isin([CAT_SMART, CAT_TABLET])]['销售数量'].sum() if len(yd_data) > 0 else 0
    change = sq - yd_sq

    store_daily.append({
        'dept': dept,
        'short': store_map.get(dept, dept.split('-')[1][:15] if '-' in dept else dept[:15]),
        'smart_qty': round(sq, 1), 'tablet_qty': round(tq, 1), 'feature_qty': round(fq, 1),
        'total': round(total, 1), 'daily_target': daily_tgt_int,
        'target_met': 'Y' if sq >= daily_tgt_int else 'N',
        'yesterday_smart': round(yd_sq, 1), 'day_change': round(change, 1)
    })

store_daily.sort(key=lambda x: x['smart_qty'], reverse=True)

# ========== MODULE 5: COMPANY DAILY SUMMARY ==========
print("Module 5: Company daily summary...")
# Build business-day-aware May daily lookup
# June business days (actual sales dates, exclude Sundays)
june_sales_dates = sorted(june['记账日期'].unique())
june_biz_seq = [d for d in june_sales_dates if d.weekday() != 6]  # Exclude Sunday
# May business days (all possible sales dates, exclude Sundays)
may_sales_dates_all = sorted(may['记账日期'].unique())
may_biz_seq_all = [d for d in may_sales_dates_all if d.weekday() != 6]
# Match: June's Nth business day vs May's Nth business day
may_biz_lookup = {}  # june_biz_index (0-based) -> may_date
for i, jd in enumerate(june_biz_seq):
    if i < len(may_biz_seq_all):
        may_biz_lookup[i] = may_biz_seq_all[i]

company_daily = []
for i, (_, r) in enumerate(daily.iterrows()):
    d = r['记账日期']
    # Skip Sundays in chart data
    if d.weekday() == 6:
        continue
    # May comparison by business day sequence
    biz_idx = len([x for x in june_biz_seq if x <= d]) - 1  # 0-based index
    may_sq = 0
    if biz_idx in may_biz_lookup:
        may_d = may[may['记账日期'] == may_biz_lookup[biz_idx]]
        may_sq = may_d[may_d['统计分类'].isin([CAT_SMART, CAT_TABLET])]['销售数量'].sum()
    # Daily profit rate
    profit_rate = round(r['profit'] / r['revenue'] * 100, 1) if r['revenue'] > 0 else 0
    company_daily.append({
        'date': d.strftime('%m-%d'),
        'smart_qty': round(r['smart_qty'], 0), 'feature_qty': round(r['feature_qty'], 0),
        'total_qty': round(r['total_qty'], 0),
        'revenue': round(r['revenue'], 0), 'profit': round(r['profit'], 0),
        'orders': int(r['orders']),
        'may_smart': round(may_sq, 0),
        'profit_rate': profit_rate
    })

# 7-day trend analysis
last7 = company_daily[-7:] if len(company_daily) >= 7 else company_daily
avg7_smart = sum(d['smart_qty'] for d in last7) / len(last7)

# ========== MODULE 6: INVENTORY ==========
print("Module 6: Inventory...")
# Filter to PHONES only (main sellable inventory)
inv_phones = inv[inv['仓库'].str.contains('PHONES', na=False)].copy()
# Remove BRAND SAMPLE, FAULTY, REJECT
inv_phones = inv_phones[~inv_phones['仓库'].str.contains('SAMPLE|FAULTY|REJECT|CARLCARE|E-COMMERCE|OS_', na=False)]

# Extract store short name from warehouse
inv_phones['inv_store'] = inv_phones['仓库'].str.replace('-PHONES', '', regex=False).str.strip()

# Map inventory warehouse to sales department using authoritative mapping
# Override inv_store with the full sales department name for accurate matching
print("  Mapping inventory warehouses to sales departments...")
mapped_count = 0
unmapped_wh = set()
for idx, row in inv_phones.iterrows():
    wh = row['仓库']
    if wh in WAREHOUSE_TO_DEPT:
        inv_phones.at[idx, 'inv_store'] = WAREHOUSE_TO_DEPT[wh]
        mapped_count += 1
    else:
        unmapped_wh.add(wh)
if len(unmapped_wh) > 0:
    print(f"  Warning: {len(unmapped_wh)} warehouses not in mapping file: {list(unmapped_wh)[:5]}")
print(f"  Mapped {mapped_count} rows to sales departments")

# Build reverse map for unmatched (fallback)
rev_map = {v: k for k, v in store_map.items()}

# Categorize
inv_phones['cat_type'] = inv_phones['二级分类名称'].map({
    'SMART PHONE': 'smart', 'FEATURE PHONE': 'feature', 'TABLET TYPE': 'tablet'
}).fillna('other')

# ===== DEDUPLICATE by (warehouse, model) — merge batch rows =====
# Inventory has multiple batch rows per store+model. Aggregate before all calculations.
print(f"  Before dedup: {len(inv_phones)} rows")
inv_phones = inv_phones.groupby(['仓库', '商品型号'], as_index=False).agg(
    可卖数=('可卖数', 'sum'),
    三级账=('三级账', 'sum'),
    近1月销量=('近1月销量', 'first'),
    近3月销量=('近3月销量', 'first'),
    近1周销量=('近1周销量', 'sum'),
    品牌=('品牌', 'first'),
    商品名称=('商品名称', 'first'),
    inv_store=('inv_store', 'first'),
    cat_type=('cat_type', 'first'),
    二级分类名称=('二级分类名称', 'first'),
    平均单价=('平均单价', 'first'),
    门店库龄=('门店库龄', 'min'),
    最后入库日期=('最后入库日期', 'first'),
)
# Recalculate 在途 = 三级账 - 可卖数
inv_phones['在途'] = inv_phones['三级账'] - inv_phones['可卖数']
print(f"  After dedup: {len(inv_phones)} rows")

# ===== Turnover calculation by actual sales days per model per store =====
# Build sales velocity: for each (store, model), count actual days with sales & total qty
# Sales data uses '型号', inventory uses '商品型号'
store_model_sales = june_smart_combo.groupby(['销售部门', '型号']).agg(
    total_qty=('销售数量', 'sum'),
    sales_days=('记账日期', 'nunique')
).reset_index()
store_model_sales.columns = ['dept', 'model', 'sales_qty', 'sales_days']
store_model_sales['daily_avg'] = store_model_sales['sales_qty'] / store_model_sales['sales_days']

# Map store short names to sales dept for matching
dept_to_short = store_map.copy()

# For each inventory item, match to sales velocity by (inv_store, model)
# inv_store is now the full sales dept name (from WAREHOUSE_TO_DEPT mapping)
def get_turnover(row):
    dept = row['inv_store']
    model = row['商品型号']
    if dept is None:
        return None, None, None, None
    match = store_model_sales[(store_model_sales['dept'] == dept) & (store_model_sales['model'] == model)]
    if len(match) > 0:
        sales_qty = match.iloc[0]['sales_qty']
        sales_days = match.iloc[0]['sales_days']
        daily_avg = match.iloc[0]['daily_avg']
        turnover_days = row['可卖数'] / daily_avg if daily_avg > 0 else 9999
        return round(sales_qty, 1), int(sales_days), round(daily_avg, 1), round(turnover_days, 1)
    return None, None, None, 0

print("  Calculating turnover by actual sales days...")
inv_phones[['model_sales_qty', 'model_sales_days', 'model_daily_avg', 'turnover_days']] = inv_phones.apply(
    lambda row: pd.Series(get_turnover(row)), axis=1
)

# ===== TURNOVER SUBSET: Smartphones + Tablets only, exclude GENERAL (central warehouse) =====
# Turnover calculates only for sellable phones & tablets in store warehouses
inv_turnover = inv_phones[
    inv_phones['cat_type'].isin(['smart', 'tablet']) &
    ~inv_phones['仓库'].str.contains('GENERAL', na=False)
].copy()
print(f"  Turnover inventory (smart+tablet, excl GENERAL): {len(inv_turnover)} rows")

# Simplified inventory risk: 近1月销量 is company-wide
# Dead stock = stock > 0 but zero company-wide monthly sales
# Low stock = popular brand, stock <= 3, company monthly > 0
inv_phones['is_dead'] = (inv_phones['可卖数'] > 0) & (inv_phones['近1月销量'] == 0)
# is_low: popular brand with sales, stock<=3 (including 0=already out of stock) OR turnover_days<4
inv_phones['is_low'] = (
    (inv_phones['可卖数'] >= 0) &
    (
        (inv_phones['可卖数'] <= 3) |
        ((inv_phones['turnover_days'] < 4) & (inv_phones['turnover_days'] >= 0) & (inv_phones['turnover_days'] != 9999))
    ) &
    (inv_phones['近1月销量'] > 0) &
    (inv_phones['品牌'].isin(['TECNO','INFINIX','XIAOMI','ITEL','SAMSUNG','VIVO','OPPO','HONOR']))
)

# Overstock: store-level items with stock > 3 and zero sales (per-store per-model, not aggregated)
# Threshold lowered from 10 to 3 — stores rarely hold >10 units of dead stock
store_overstock = inv_phones[(inv_phones['is_dead']) & (inv_phones['可卖数'] > 3) & (~inv_phones['仓库'].str.contains('GENERAL', na=False))]
store_overstock['资金占用'] = (store_overstock['可卖数'] * store_overstock['平均单价']).round(0)
store_overstock_top = store_overstock.nlargest(10, '可卖数')[
    ['仓库', '商品名称', '品牌', '商品型号', '可卖数', '平均单价', '资金占用']
].to_dict('records')

# Central warehouse dead stock (GENERAL-PHONES)
general_dead = inv_phones[(inv_phones['仓库'].str.contains('GENERAL-PHONES', na=False)) & (inv_phones['is_dead']) & (inv_phones['可卖数'] > 5)]
general_dead = general_dead.nlargest(10, '可卖数')[['商品名称','品牌','商品型号','可卖数','平均单价']].copy()
general_dead['资金占用'] = (general_dead['可卖数'] * general_dead['平均单价']).round(0)
general_dead = general_dead.to_dict('records')

# Low stock popular items at stores - prioritize 0-stock items, then by sales volume
low_items = inv_phones[(inv_phones['is_low']) & (~inv_phones['仓库'].str.contains('GENERAL', na=False))]
# Sort: 0-stock first (most urgent), then by 近1月销量 descending
low_items = low_items.sort_values(['可卖数', '近1月销量'], ascending=[True, False])
lowstock_top = low_items.head(40)[['仓库','商品名称','品牌','商品型号','可卖数','近1月销量','turnover_days']].to_dict('records')

# Build general warehouse stock lookup for lowstock items
general_stock_lookup = inv_phones[
    inv_phones['仓库'].str.contains('GENERAL-PHONES', na=False)
][['商品型号','可卖数']].groupby('商品型号')['可卖数'].sum().to_dict()

for item in lowstock_top:
    item['总仓库存'] = int(general_stock_lookup.get(item['商品型号'], 0))

# ========== Store-level turnover：门店总可卖数 / 门店日均销量 ==========
# Formula: 周转天数 = Σ(该店所有smart+tablet可卖数) / (该店smart+tablet总销量÷该店有销售的天数)
store_sales_velocity = june_smart_combo.groupby('销售部门').agg(
    store_total_sales_qty=('销售数量', 'sum'),
    store_sales_days=('记账日期', 'nunique')
).reset_index()
store_sales_velocity['store_daily_avg'] = round(
    store_sales_velocity['store_total_sales_qty'] / store_sales_velocity['store_sales_days'], 1
)
store_sales_velocity.columns = ['dept', 'store_total_sales_qty', 'store_sales_days', 'store_daily_avg']

# Store total sellable (smart+tablet, excl GENERAL)
store_total_sellable = inv_turnover.groupby('inv_store').agg(
    total_sellable=('可卖数', 'sum')
).reset_index()

# Merge sales velocity and compute turnover_days
store_turnover = store_total_sellable.merge(
    store_sales_velocity, left_on='inv_store', right_on='dept', how='left'
)
store_turnover['turnover_days'] = store_turnover.apply(
    lambda row: round(row['total_sellable'] / row['store_daily_avg'], 1)
    if row.get('store_daily_avg', 0) > 0 else 9999,
    axis=1
)
store_turnover['store_daily_avg'] = store_turnover['store_daily_avg'].fillna(0)
store_turnover['store_total_sales_qty'] = store_turnover['store_total_sales_qty'].fillna(0)
store_turnover['store_sales_days'] = store_turnover['store_sales_days'].fillna(0)

# Turnover summary stats
valid_turnover = store_turnover[store_turnover['turnover_days'] < 9999]
all_dead_stores = store_turnover[store_turnover['turnover_days'] >= 9999]['inv_store'].tolist()
turnover_summary = {
    'avg_days': round(valid_turnover['turnover_days'].mean(), 1) if len(valid_turnover) > 0 else 0,
    'median_days': round(valid_turnover['turnover_days'].median(), 1) if len(valid_turnover) > 0 else 0,
    # New rating bands
    'warning': int((valid_turnover['turnover_days'] < 4).sum()),           # 缺货预警
    'excellent': int(((valid_turnover['turnover_days'] >= 4) & (valid_turnover['turnover_days'] < 15)).sum()),
    'good': int(((valid_turnover['turnover_days'] >= 15) & (valid_turnover['turnover_days'] <= 21)).sum()),
    'risk': int(((valid_turnover['turnover_days'] > 21) & (valid_turnover['turnover_days'] <= 60)).sum()),  # 积压风险
    'critical': int((valid_turnover['turnover_days'] > 60).sum()) + len(all_dead_stores),
    # Backward-compatible aliases (old KPI reads these)
    'excellent_old': int((valid_turnover['turnover_days'] < 15).sum()),  # old "优秀" (<15)
    'slow_old': int(((valid_turnover['turnover_days'] >= 30) & (valid_turnover['turnover_days'] < 60)).sum()),  # old "偏慢"
    'all_dead_count': len(all_dead_stores),
    'all_dead_count': len(all_dead_stores),
    'all_dead_stores': all_dead_stores[:5],
    'best_store': valid_turnover.loc[valid_turnover['turnover_days'].idxmin(), 'inv_store'] if len(valid_turnover) > 0 else '-',
    'best_days': round(valid_turnover['turnover_days'].min(), 1) if len(valid_turnover) > 0 else 0,
    'worst_store': valid_turnover.loc[valid_turnover['turnover_days'].idxmax(), 'inv_store'] if len(valid_turnover) > 0 else '-',
    'worst_days': round(valid_turnover['turnover_days'].max(), 1) if len(valid_turnover) > 0 else 0,
    'total_stores': len(store_turnover),
}
print(f"  Turnover summary (smart+tablet, excl GENERAL): avg={turnover_summary['avg_days']}d, excellent={turnover_summary['excellent']}, critical={turnover_summary['critical']}")

# Build inv_store_agg with turnover data
store_inv = inv_turnover.copy()
inv_store_agg = store_inv.groupby('inv_store').agg(
    total_stock=('可卖数', 'sum'),
    smart_stock=('可卖数', lambda x: x[store_inv.loc[x.index, 'cat_type'] == 'smart'].sum()),
    tablet_stock=('可卖数', lambda x: x[store_inv.loc[x.index, 'cat_type'] == 'tablet'].sum()),
    in_transit=('在途', 'sum'),
    fund_tied=('可卖数', lambda x: (x * store_inv.loc[x.index, '平均单价']).sum())
).reset_index()
inv_store_agg['feature_stock'] = 0
inv_store_agg['dead_count'] = 0
inv_store_agg['low_count'] = 0
inv_store_agg = inv_store_agg.merge(
    store_turnover[['inv_store', 'turnover_days', 'store_daily_avg', 'store_total_sales_qty']],
    on='inv_store', how='left'
)
inv_store_agg['daily_avg_sales'] = inv_store_agg['store_daily_avg'].fillna(0)
inv_store_agg = inv_store_agg.to_dict('records')

# ========== Brand-level turnover：品牌门店总可卖数（不含总仓）/ 品牌日均销量 ==========
print("  Computing brand-level turnover (smart+tablet, excl GENERAL)...")
# Brand store sellable (excl GENERAL)
brand_store_sellable = inv_turnover.groupby('品牌').agg(
    store_sellable=('可卖数', 'sum')
).reset_index()
# Brand GENERAL (central warehouse) sellable
brand_general = inv_phones[
    inv_phones['仓库'].str.contains('GENERAL', na=False) &
    inv_phones['cat_type'].isin(['smart', 'tablet'])
].groupby('品牌').agg(
    general_sellable=('可卖数', 'sum')
).reset_index()
# Brand daily avg sales
brand_sales = june_smart_combo.groupby('品牌').agg(
    brand_total_sales_qty=('销售数量', 'sum'),
    brand_sales_days=('记账日期', 'nunique')
).reset_index()
brand_sales['brand_daily_avg'] = round(
    brand_sales['brand_total_sales_qty'] / brand_sales['brand_sales_days'], 1
)

# Merge and compute brand turnover
brand_turnover_df = brand_store_sellable.merge(brand_general, on='品牌', how='left')
brand_turnover_df['general_sellable'] = brand_turnover_df['general_sellable'].fillna(0)
brand_turnover_df = brand_turnover_df.merge(brand_sales, on='品牌', how='left')
brand_turnover_df['turnover_days'] = brand_turnover_df.apply(
    lambda row: round(row['store_sellable'] / row['brand_daily_avg'], 1)
    if row.get('brand_daily_avg', 0) > 0 else 9999,
    axis=1
)
brand_turnover_df = brand_turnover_df.sort_values('turnover_days')
brand_turnover = brand_turnover_df.to_dict('records')

# ========== Model-level turnover：所有门店仓可卖数 / 型号日均销量，按日销降序 ==========
print("  Computing model-level turnover (all stores, excl GENERAL, sorted by daily sales)...")
# Model total sellable across all stores (excl GENERAL)
model_total_sellable = inv_turnover.groupby(['品牌', '商品型号']).agg(
    total_sellable=('可卖数', 'sum'),
    total_transit=('在途', 'sum'),
    avg_unit_price=('平均单价', 'first'),
    store_count=('仓库', 'nunique')
).reset_index()
# Model daily avg sales
model_sales = june_smart_combo.groupby('型号').agg(
    total_sales_qty=('销售数量', 'sum'),
    sales_days=('记账日期', 'nunique')
).reset_index()
model_sales['daily_avg_sales'] = round(
    model_sales['total_sales_qty'] / model_sales['sales_days'], 1
)
model_sales.columns = ['型号', 'total_sales_qty', 'total_sales_days', 'daily_avg_sales']

# Merge and compute model turnover
model_turnover_df = model_total_sellable.merge(
    model_sales, left_on='商品型号', right_on='型号', how='left'
)
model_turnover_df['turnover_days'] = model_turnover_df.apply(
    lambda row: round(row['total_sellable'] / row['daily_avg_sales'], 1)
    if row.get('daily_avg_sales', 0) > 0 else 9999,
    axis=1
)
# Filter out dead stock and sort: DESCENDING by daily sales
model_turnover_df = model_turnover_df[model_turnover_df['turnover_days'] < 9999]
model_turnover_df = model_turnover_df.sort_values('total_sales_qty', ascending=False)
model_turnover_df['资金占用'] = (model_turnover_df['total_sellable'] * model_turnover_df['avg_unit_price']).round(0)
model_turnover = model_turnover_df.to_dict('records')

# Store-model turnover: enhanced with category, brand, 可卖数, 在途, sorted by sales volume
print("  Computing store-model turnover with sales ranking...")
store_model_inv = inv_turnover[['仓库', 'inv_store', '二级分类名称', '品牌', '商品型号', '可卖数', '在途', 'turnover_days', '平均单价']].copy()
store_model_inv['资金占用'] = (store_model_inv['可卖数'] * store_model_inv['平均单价']).round(0)

# Join with sales data for sorting by volume
store_model_inv = store_model_inv.merge(
    store_model_sales,
    left_on=['inv_store', '商品型号'],
    right_on=['dept', 'model'],
    how='left'
)
store_model_inv['sales_qty'] = store_model_inv['sales_qty'].fillna(0)
store_model_inv['sales_days'] = store_model_inv['sales_days'].fillna(0)
store_model_inv['daily_avg'] = store_model_inv['daily_avg'].fillna(0)

# Merge duplicate (inv_store, 商品型号) records: sum inventory, recalc turnover
# Same store+model may have multiple inventory rows (different batches/locations)
print("  Merging duplicate (store+model) records...")
pre_merge_count = len(store_model_inv)
store_model_inv = store_model_inv.groupby(['inv_store', '商品型号']).agg({
    '仓库': 'first',
    '二级分类名称': 'first',
    '品牌': 'first',
    '可卖数': 'sum',
    '在途': 'sum',
    '平均单价': 'first',
    'sales_qty': 'first',
    'sales_days': 'first',
    'daily_avg': 'first',
}).reset_index()
# Recalculate turnover_days: sellable / daily_avg
store_model_inv['turnover_days'] = store_model_inv.apply(
    lambda row: round(row['可卖数'] / row['daily_avg'], 1) if row['daily_avg'] > 0 else 9999,
    axis=1
)
store_model_inv['资金占用'] = (store_model_inv['可卖数'] * store_model_inv['平均单价']).round(0)
print(f"  Merged: {pre_merge_count} -> {len(store_model_inv)} records")

# Add general warehouse (GENERAL-PHONES) stock per model
print("  Computing general warehouse stock per model...")
general_stock = inv_phones[
    inv_phones['仓库'].str.contains('GENERAL-PHONES', na=False)
].groupby('商品型号')['可卖数'].sum().reset_index()
general_stock.rename(columns={'可卖数': '总仓库存'}, inplace=True)
store_model_inv = store_model_inv.merge(general_stock, on='商品型号', how='left')
store_model_inv['总仓库存'] = store_model_inv['总仓库存'].fillna(0).astype(int)
print(f"  General stock merged, {len(general_stock)} models have central warehouse stock")

# Sort by sales volume descending within each store
store_model_inv = store_model_inv.sort_values(['inv_store', 'sales_qty'], ascending=[True, False])
store_model_turnover = store_model_inv[[
    '仓库', 'inv_store', '二级分类名称', '品牌', '商品型号',
    '可卖数', '在途', 'turnover_days', '资金占用', 'sales_qty', '总仓库存'
]].to_dict('records')

# Build store short-name mapping for dropdown
print("  Building store short-name mapping...")
store_short_names = {}
store_long_to_short = {}  # full dept name -> short name

# 1. From tgt_acc (all sales departments with SHOP column)
for _, r in tgt_acc.iterrows():
    dept = r['销售部门']
    short = r['SHOP']
    if pd.notna(dept) and pd.notna(short):
        store_long_to_short[dept] = short

# 2. From manual_map
store_long_to_short.update(manual_map)

# 3. For each dept in the mapping file, ensure it has a short name
for dept in DEPT_TO_WAREHOUSE:
    if dept not in store_long_to_short:
        # Try to extract short name from the DEPT_TO_WAREHOUSE key
        parts = dept.split('-')
        if len(parts) >= 3:
            short_candidate = parts[1].strip()
            store_long_to_short[dept] = short_candidate
        else:
            store_long_to_short[dept] = dept

# 4. Build store_short_names (all mapped dept -> short)
for dept, short in store_long_to_short.items():
    store_short_names[dept] = short

print(f"  Brand turnover: {len(brand_turnover)} brands")
print(f"  Model turnover: {len(model_turnover)} models")
print(f"  Store-model turnover: {len(store_model_turnover)} records")
print(f"  Store short names: {len(store_short_names)} mapped")

# Apply short names to inv_store_agg
for s in inv_store_agg:
    dept = s['inv_store']
    s['store_short'] = store_short_names.get(dept, dept.split('-')[1][:15] if '-' in dept else dept[:15])

# ========== MODULE 7: STAFF EFFICIENCY ==========
print("Module 7: Staff efficiency...")

# Salesperson-level aggregation (smart phone combo only)
sp_agg = june_smart_combo.groupby(['销售部门','营业员']).agg(
    smart_qty=('销售数量','sum'),
    revenue=('零售金额','sum'),
    profit=('毛利','sum')
).reset_index()
sp_agg = sp_agg[sp_agg['营业员'].notna() & (sp_agg['营业员'] != '')]

# Store-level staff efficiency
sp_store = sp_agg.groupby('销售部门').agg(
    staff_count=('营业员','nunique'),
    total_smart_qty=('smart_qty','sum'),
    total_revenue=('revenue','sum'),
    total_profit=('profit','sum')
).reset_index()

# Top salesperson per store
idx_max = sp_agg.groupby('销售部门')['smart_qty'].idxmax()
top_sp = sp_agg.loc[idx_max, ['销售部门','营业员','smart_qty']].rename(columns={'营业员':'top_sp_name','smart_qty':'top_sp_qty'})
sp_store = sp_store.merge(top_sp, on='销售部门', how='left')

# All categories staff efficiency
sp_all = june.groupby(['销售部门','营业员']).agg(
    total_qty=('销售数量','sum'),
    total_revenue=('零售金额','sum'),
    total_profit=('毛利','sum')
).reset_index()
sp_all = sp_all[sp_all['营业员'].notna() & (sp_all['营业员'] != '')]

sp_all_store = sp_all.groupby('销售部门').agg(
    total_all_qty=('total_qty','sum'),
    total_all_revenue=('total_revenue','sum'),
    total_all_profit=('total_profit','sum')
).reset_index()

sp_store = sp_store.merge(sp_all_store, on='销售部门', how='left')

sp_store['avg_smart_per_person'] = (sp_store['total_smart_qty'] / sp_store['staff_count']).round(1)
sp_store['avg_total_per_person'] = (sp_store['total_all_qty'] / sp_store['staff_count']).round(1)
sp_store['avg_revenue_per_person'] = (sp_store['total_all_revenue'] / sp_store['staff_count']).round(0)
sp_store['avg_profit_per_person'] = (sp_store['total_all_profit'] / sp_store['staff_count']).round(0)

# Map short names
sp_store['short'] = sp_store['销售部门'].map(lambda dept: store_map.get(dept, dept.split('-')[1][:15] if '-' in dept else dept[:15]))
sp_store = sp_store.sort_values('avg_smart_per_person', ascending=False)

# Overall company stats
total_staff = june['营业员'].dropna().nunique()
co_avg_smart = round(june_smart_qty / total_staff, 1) if total_staff > 0 else 0
co_avg_total = round(june_all_qty / total_staff, 1) if total_staff > 0 else 0
co_avg_profit = round(june_total_profit / total_staff, 0) if total_staff > 0 else 0

# Tier for store efficiency
for s in sp_store.to_dict('records'):
    pass  # Will tier in template

# Top salespersons (across all stores, smart phone only)
sp_rank = sp_agg.groupby('营业员').agg(
    smart_qty=('smart_qty','sum'),
    revenue=('revenue','sum'),
    profit=('profit','sum')
).reset_index()
sp_rank['profit_rate'] = (sp_rank['profit'] / sp_rank['revenue'] * 100).round(1)
sp_rank['profit_rate'] = sp_rank['profit_rate'].fillna(0)
sp_rank = sp_rank.sort_values('smart_qty', ascending=False)

# Efficiency bands
sp_eff_records = sp_store.to_dict('records')
for s in sp_eff_records:
    if s['avg_smart_per_person'] >= co_avg_smart * 1.5:
        s['eff_tier'] = '高绩效'
        s['eff_color'] = '#22c55e'
    elif s['avg_smart_per_person'] >= co_avg_smart * 0.7:
        s['eff_tier'] = '平均'
        s['eff_color'] = '#3b82f6'
    else:
        s['eff_tier'] = '低效'
        s['eff_color'] = '#ef4444'

print(f"  Total staff: {total_staff}, Co avg smart/person: {co_avg_smart}")
print(f"  Top store efficiency: {sp_eff_records[0]['short']} ({sp_eff_records[0]['avg_smart_per_person']}台/人)")
print(f"  Bottom store efficiency: {sp_eff_records[-1]['short']} ({sp_eff_records[-1]['avg_smart_per_person']}台/人)")

# ========== MODULE 8: GAP CATCH-UP ==========
print("Module 8: Gap catch-up plan...")
total_gap = max(0, TOTAL_TARGET - june_smart_qty)
daily_needed_total = total_gap / REMAINING_DAYS if REMAINING_DAYS > 0 else 0

lagging_stores = [s for s in store_perf if s['rate'] < expected_rate * 0.75]
lagging_stores.sort(key=lambda x: x['remaining'], reverse=True)

# ========== MODULE 9: DAILY ISSUES ==========
print("Module 9: Daily issues...")
m9_issues = []

# 1. 未达日目标门店 (from store_daily)
for s in store_daily:
    if s['target_met'] == 'N' and s['smart_qty'] > 0:
        m9_issues.append({
            'type': '未达日目标',
            'store': s['short'],
            'detail': f"当日智能机{s['smart_qty']:.0f}台，目标{s['daily_target']:.0f}台，缺口{s['daily_target']-s['smart_qty']:.0f}台",
            'action': f"次日加大主推力度，确保达成日目标"
        })

# 2. 月度严重滞后门店 (completion rate < 30%)
for s in store_perf:
    if s['tier'] == '严重滞后':
        m9_issues.append({
            'type': '月度严重滞后',
            'store': s['short'],
            'detail': f"累计{s['qty']:.0f}台/目标{s['target']:.0f}台，完成率{s['rate']:.1f}%，缺口{s['remaining']:.0f}台",
            'action': f"安排区域经理驻店帮扶，分析客流/人员/备货问题，日均需达成{s['daily_need']:.0f}台"
        })

# 3. 缺货预警 (top 5 from inventory low stock, prioritize 0-stock)
for l in lowstock_top[:5]:
    store_short = l['仓库'].replace('-PHONES', '')
    gen_stock = l.get('总仓库存', 0)
    stock_qty = l['可卖数']
    if stock_qty == 0:
        detail = f"{l['品牌']} {l['商品型号']}，门店已缺货(0台)！总仓库存{gen_stock:.0f}台，全公司月销{l['近1月销量']:.0f}台"
    else:
        detail = f"{l['品牌']} {l['商品型号']}，门店库存仅{stock_qty:.0f}台，总仓库存{gen_stock:.0f}台，全公司月销{l['近1月销量']:.0f}台"
    m9_issues.append({
        'type': '缺货预警',
        'store': store_short,
        'detail': detail,
        'action': f"紧急从总仓调拨{l['品牌']} {l['商品型号']}至{store_short}"
    })

# 4. 库存积压 (top 5 overstock)
for o in store_overstock_top[:5]:
    store_short = o['仓库'].replace('-PHONES', '')
    m9_issues.append({
        'type': '库存积压',
        'store': store_short,
        'detail': f"{o['品牌']} {o['商品型号']}，库存{o['可卖数']:.0f}台，月销为0，占资₦{o['资金占用']/1e3:.0f}K",
        'action': f"促销清库/跨店调拨，释放资金约₦{o['资金占用']/1e3:.0f}K"
    })

# 5. 品牌销量下滑 (mom_pct < -5%)
for b in june_brands.to_dict('records'):
    if b.get('mom_pct', 0) < -5 and b.get('mom_pct', 0) < 500:  # exclude 9999 sentinel
        m9_issues.append({
            'type': '品牌销量下滑',
            'store': b['品牌'],
            'detail': f"本月{b['qty']:.0f}台 vs 上月同期{b.get('may_qty',0):.0f}台，环比{b['mom_pct']:.1f}%",
            'action': f"检查{b['品牌']}主推机型库存及导购话术，加大促销力度"
        })

# 6. 当日零销量门店
for s in store_daily:
    if s['smart_qty'] == 0 and s['feature_qty'] == 0 and s['tablet_qty'] == 0:
        m9_issues.append({
            'type': '当日零销量',
            'store': s['short'],
            'detail': f"当日智能机/平板/功能机均为零销量",
            'action': f"排查门店运营状态，确认是否正常营业及库存情况"
        })

print(f"  Generated {len(m9_issues)} issues")

# ========== MODULE 12: STORE DAILY SALES VOLATILITY ==========
print("Module 12: Store daily sales volatility...")
import numpy as np

# Build per-store daily smart combo quantities for current month
june_smart_daily = june_smart_combo.groupby(['销售部门', '记账日期'])['销售数量'].sum().reset_index()
june_smart_daily.columns = ['dept', 'date', 'qty']

# Business days (exclude Sundays) from current month, sorted
curr_biz_dates = sorted([d for d in june_smart_daily['date'].unique() if d.weekday() != 6])

# Build per-store daily series aligned to business days
store_volatility = []
for dept in june['销售部门'].dropna().unique():
    sd = june_smart_daily[june_smart_daily['dept'] == dept]
    if sd.empty:
        continue
    # Build daily series aligned to business days
    daily_series = []
    for bd in curr_biz_dates:
        q = sd[sd['date'] == bd]['qty'].sum()
        daily_series.append(round(float(q), 1))

    if not daily_series:
        continue

    arr = np.array(daily_series, dtype=float)
    n = len(arr)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    cv_val = (std_val / mean_val * 100) if mean_val > 0 else 0.0
    max_val = float(np.max(arr))
    min_val = float(np.min(arr))
    range_val = max_val - min_val
    zero_days = int(np.sum(arr == 0))

    # Linear trend slope (simple regression)
    if n > 1:
        x = np.arange(n, dtype=float)
        slope = float(np.polyfit(x, arr, 1)[0]) if np.std(x) > 0 else 0.0
    else:
        slope = 0.0

    # Previous month comparison: same number of business days
    may_dept_daily = may_smart_combo[may_smart_combo['销售部门'] == dept]
    may_daily_series = []
    may_biz_dates_compare = may_biz_seq_all[:n]  # First N business days of previous month
    for bd in may_biz_dates_compare:
        q = may_dept_daily[may_dept_daily['记账日期'] == bd]['销售数量'].sum()
        may_daily_series.append(round(float(q), 1))

    may_cv = 0.0
    may_mean = 0.0
    if may_daily_series and sum(may_daily_series) > 0:
        may_arr = np.array(may_daily_series, dtype=float)
        may_mean = float(np.mean(may_arr))
        may_std = float(np.std(may_arr, ddof=1)) if len(may_arr) > 1 else 0.0
        may_cv = (may_std / may_mean * 100) if may_mean > 0 else 0.0

    cv_change = round(cv_val - may_cv, 1)

    # Volatility rating
    if mean_val == 0:
        rating = '停业'
        rating_color = '#6b7280'
    elif cv_val <= 25:
        rating = '稳定'
        rating_color = '#22c55e'
    elif cv_val <= 40:
        rating = '正常'
        rating_color = '#3b82f6'
    elif cv_val <= 60:
        rating = '波动较大'
        rating_color = '#f59e0b'
    else:
        rating = '剧烈波动'
        rating_color = '#ef4444'

    # Trend direction
    if slope > mean_val * 0.05:
        trend_dir = '↑上升'
        trend_color = '#22c55e'
    elif slope < -mean_val * 0.05:
        trend_dir = '↓下降'
        trend_color = '#ef4444'
    else:
        trend_dir = '→平稳'
        trend_color = '#6b7280'

    short_name = store_map.get(dept, dept.split('-')[1][:15] if '-' in dept else dept[:15])

    # Brand breakdown for this store
    store_brand = june_smart_combo[june_smart_combo['销售部门'] == dept].groupby('品牌')['销售数量'].sum().sort_values(ascending=False)
    brands_list = [{'brand': b, 'qty': int(q), 'pct': round(float(q) / float(store_brand.sum()) * 100, 1)} for b, q in store_brand.items() if q > 0]

    # Top 5 models for this store
    store_models = june_smart_combo[june_smart_combo['销售部门'] == dept].groupby('型号')['销售数量'].sum().sort_values(ascending=False).head(10)
    top_models = [{'model': m, 'qty': int(q)} for m, q in store_models.items() if q > 0]

    store_volatility.append({
        'dept': dept,
        'short': short_name,
        'daily_series': daily_series,
        'may_daily_series': may_daily_series,
        'biz_dates': [d.strftime('%m-%d') for d in curr_biz_dates],
        'mean': round(mean_val, 1),
        'std': round(std_val, 1),
        'cv': round(cv_val, 1),
        'max': round(max_val, 1),
        'min': round(min_val, 1),
        'range': round(range_val, 1),
        'zero_days': zero_days,
        'slope': round(slope, 2),
        'trend_dir': trend_dir,
        'trend_color': trend_color,
        'may_cv': round(may_cv, 1),
        'may_mean': round(may_mean, 1),
        'cv_change': cv_change,
        'rating': rating,
        'rating_color': rating_color,
        'total_qty': round(float(arr.sum()), 1),
        'brands': brands_list,
        'top_models': top_models,
    })

# Sort by CV descending (most volatile first)
store_volatility.sort(key=lambda x: x['cv'], reverse=True)

# Summary stats
vol_stores = [s for s in store_volatility if s['mean'] > 0]
vol_avg_cv = round(float(np.mean([s['cv'] for s in vol_stores])), 1) if vol_stores else 0
vol_most_stable = min(vol_stores, key=lambda x: x['cv']) if vol_stores else None
vol_most_volatile = max(vol_stores, key=lambda x: x['cv']) if vol_stores else None
vol_zero_day_stores = [s for s in store_volatility if s['zero_days'] > 0]
vol_declining = [s for s in vol_stores if s['trend_dir'] == '↓下降']

m12_summary = {
    'total_stores': len(store_volatility),
    'active_stores': len(vol_stores),
    'avg_cv': vol_avg_cv,
    'most_stable': vol_most_stable['short'] if vol_most_stable else '-',
    'most_stable_cv': vol_most_stable['cv'] if vol_most_stable else 0,
    'most_volatile': vol_most_volatile['short'] if vol_most_volatile else '-',
    'most_volatile_cv': vol_most_volatile['cv'] if vol_most_volatile else 0,
    'zero_day_count': len(vol_zero_day_stores),
    'declining_count': len(vol_declining),
    'rating_dist': {
        '稳定': len([s for s in vol_stores if s['rating'] == '稳定']),
        '正常': len([s for s in vol_stores if s['rating'] == '正常']),
        '波动较大': len([s for s in vol_stores if s['rating'] == '波动较大']),
        '剧烈波动': len([s for s in vol_stores if s['rating'] == '剧烈波动']),
        '停业': len([s for s in store_volatility if s['rating'] == '停业']),
    }
}

print(f"  Stores analyzed: {len(store_volatility)}, Avg CV: {vol_avg_cv}%")
print(f"  Most stable: {m12_summary['most_stable']} ({m12_summary['most_stable_cv']}%)")
print(f"  Most volatile: {m12_summary['most_volatile']} ({m12_summary['most_volatile_cv']}%)")
print(f"  Zero-day stores: {len(vol_zero_day_stores)}, Declining: {len(vol_declining)}")

# ========== MODULE 10: MODEL SALES ANALYSIS ==========
print("\nModule 10: Model sales analysis...")
m10_model_analysis = []

# Load price list if provided
price_map = {}  # model name (upper, no space) -> (price, price_source)
brand_map = {}  # model name (upper, no space) -> brand

if args.price_list:
    print("  Loading price list...")
    try:
        pl_raw = pd.read_excel(args.price_list)
    except Exception as e:
        # Try with openpyxl engine
        pl_raw = pd.read_excel(args.price_list, engine='openpyxl')
    pl = normalize_spaces(pl_raw)

    # Build price mapping: SYSTEM MODEL NAME -> resolved price
    # Priority: discount price > RRP WITH VAT > 3C HUB
    def safe_float(val):
        """Safely convert to float, returning NaN for empty/invalid values."""
        if pd.isna(val):
            return float('nan')
        try:
            return float(str(val).strip())
        except (ValueError, TypeError):
            return float('nan')

    def resolve_price(row):
        promo = safe_float(row.get('PROMO PRICE'))
        rrp = safe_float(row.get('RRP WITH VAT '))
        hub = safe_float(row.get('3C HUB'))
        # Priority: PROMO PRICE > RRP WITH VAT > 3C HUB
        if not pd.isna(promo) and promo > 0:
            return promo, 'PROMO PRICE'
        elif not pd.isna(rrp) and rrp > 0:
            return rrp, 'RRP WITH VAT'
        else:
            return hub, '3C HUB'

    for _, r in pl.iterrows():
        mdl = str(r['SYSTEM MODEL NAME']).strip().upper()
        mdl_ns = mdl.replace(' ', '')  # no space version for matching
        price, src = resolve_price(r)
        price_map[mdl_ns] = (price, src)
        brand_map[mdl_ns] = str(r.get('BRANDS', '')).strip()

    # Price tier function
    def get_price_tier(price):
        if pd.isna(price) or price == 0:
            return '未知'
        elif price < 100000:
            return '10w以下'
        elif price < 200000:
            return '10w'
        elif price < 300000:
            return '20w'
        elif price < 400000:
            return '30w'
        elif price < 500000:
            return '40w'
        elif price < 600000:
            return '50w'
        elif price < 1000000:
            return '50-100w'
        else:
            return '100w以上'
    print(f"  Loaded {len(price_map)} price records")
else:
    print("  No price list provided, price fields will be empty")
def get_price_tier(price):
    if price <= 0:
        return '未知'
    elif price < 100000:
        return '10w以下'
    elif price < 200000:
        return '10w'
    elif price < 300000:
        return '20w'
    elif price < 400000:
        return '30w'
    elif price < 500000:
        return '40w'
    elif price < 700000:
        return '50w'
    elif price < 1000000:
        return '50-100w'
    else:
        return '100w以上'

# Compute per-model sales (smart + tablet only)
june_model_sales = june_smart_combo.copy()
# Add normalized model name for matching
june_model_sales['model_upper'] = june_model_sales['型号'].astype(str).str.strip().str.upper()

# Group by model
model_stats = june_model_sales.groupby('model_upper').agg(
    total_qty=('销售数量', 'sum'),
    total_revenue=('零售金额', 'sum'),
    total_profit=('毛利', 'sum'),
    avg_price=('零售金额', lambda x: x.sum() / june_model_sales.loc[x.index, '销售数量'].sum() if june_model_sales.loc[x.index, '销售数量'].sum() > 0 else 0),
).reset_index()

# Also get brand from sales data (most common)
brand_from_sales = june_model_sales.groupby('model_upper')['品牌'].agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else '').to_dict()

# Precompute inventory model matching columns (once, not inside loop)
inv['_model_ns'] = inv['商品型号'].astype(str).str.strip().str.upper().str.replace(' ', '', regex=False)
inv['_name_ns'] = inv['商品名称'].astype(str).str.strip().str.upper().str.replace(' ', '', regex=False)

# Match to price list and compute metrics
for _, r in model_stats.iterrows():
    mdl_upper = r['model_upper']
    mdl_nospace = mdl_upper.replace(' ', '')
    qty = float(r['total_qty'])
    revenue = float(r['total_revenue'])
    profit = float(r['total_profit'])

    # Defaults
    price = 0
    price_tier = '未知'
    price_source = ''
    matched_brand = brand_from_sales.get(mdl_upper, '')

    # Match price (no-space keys)
    if mdl_nospace in price_map:
        price, price_source = price_map[mdl_nospace]
        price_tier = get_price_tier(price)
        if mdl_nospace in brand_map and brand_map[mdl_nospace]:
            matched_brand = brand_map[mdl_nospace]
    else:
        # Try partial match (remove spaces from both sides)
        for pl_mdl_ns, (p, src) in price_map.items():
            if mdl_nospace in pl_mdl_ns or pl_mdl_ns in mdl_nospace:
                price = p
                price_source = src + ' (partial match)'
                price_tier = get_price_tier(price)
                if pl_mdl_ns in brand_map and brand_map[pl_mdl_ns]:
                    matched_brand = brand_map[pl_mdl_ns]
                break

    # Daily avg sales
    daily_avg = qty / ELAPSED_DAYS if ELAPSED_DAYS > 0 else 0

    # Profit margin %
    profit_margin = (profit / revenue * 100) if revenue > 0 else 0

    # Total inventory: sum of 可卖数 across ALL warehouses for this model
    # Match priority: 商品型号 exact -> 商品型号 contains -> 商品名称 contains
    inv_model = pd.DataFrame()

    # 1. Exact match on 商品型号 (no-space) — most reliable column
    mask1 = inv['_model_ns'] == mdl_nospace
    if mask1.any():
        inv_model = inv[mask1]
    else:
        # 2. Contains match on 商品型号 (no-space), collect ALL rows
        match_indices = []
        for idx in inv.index:
            imodel_ns = inv.at[idx, '_model_ns']
            if isinstance(imodel_ns, str) and (mdl_nospace in imodel_ns or imodel_ns in mdl_nospace):
                match_indices.append(idx)
        if match_indices:
            inv_model = inv.loc[match_indices]
        else:
            # 3. Fallback: contains match on 商品名称 (no-space), collect ALL rows
            for idx in inv.index:
                iname_ns = inv.at[idx, '_name_ns']
                if isinstance(iname_ns, str) and mdl_nospace in iname_ns:
                    match_indices.append(idx)
            if match_indices:
                inv_model = inv.loc[match_indices]

    total_inventory = float(inv_model['可卖数'].sum()) if not inv_model.empty else 0

    # Turnover days
    turnover_days = round(total_inventory / daily_avg, 1) if daily_avg > 0 else 999

    m10_model_analysis.append({
        'model': r['model_upper'],  # original model name from sales
        'brand': matched_brand,
        'qty': int(qty),
        'daily_avg': round(daily_avg, 1),
        'price': int(price),
        'price_tier': price_tier,
        'price_source': price_source,
        'profit_margin': round(profit_margin, 1),
        'total_inventory': int(total_inventory),
        'turnover_days': turnover_days if turnover_days != 999 else '>999',
    })

# Cleanup temp columns
inv.drop(columns=['_model_ns', '_name_ns'], inplace=True, errors='ignore')

# Sort by qty desc, keep ALL models (no limit — pagination handled in frontend)
m10_model_analysis.sort(key=lambda x: x['qty'], reverse=True)
print(f"  Model analysis: {len(m10_model_analysis)} models (all)")

# Build model->(brand, price_tier) lookup from M10 for trend filtering
def norm_key(s):
    return str(s).upper().replace(' ', '')
model_attr_lookup = {norm_key(m['model']): (m['brand'], m['price_tier']) for m in m10_model_analysis}

# ========== MODEL DAILY SALES TRENDS (all smart+tablet models) ==========
print("  Computing model daily sales trends...")
model_daily_june = june_smart_combo.groupby(['型号', '记账日期'])['销售数量'].sum().reset_index()
model_daily_may = may_smart_combo.groupby(['型号', '记账日期'])['销售数量'].sum().reset_index()

# Build daily arrays for all biz days (use dynamic month ranges)
june_biz_range = june_biz_dates  # All business days in current month
may_biz_range = may_biz_dates    # All business days in comparison month

model_daily_trends = []
for model_name in sorted(model_daily_june['型号'].unique()):
    # June daily sales
    june_model = model_daily_june[model_daily_june['型号'] == model_name]
    june_quantities = []
    for d in june_biz_range:
        row = june_model[june_model['记账日期'] == d]
        june_quantities.append(int(row['销售数量'].iloc[0]) if len(row) > 0 else 0)
    
    june_dates = [d.strftime('%m-%d') for d in june_biz_range]
    
    # May daily sales (for comparison)
    may_model = model_daily_may[model_daily_may['型号'] == model_name]
    may_quantities = []
    for d in may_biz_range:
        row = may_model[may_model['记账日期'] == d]
        may_quantities.append(int(row['销售数量'].iloc[0]) if len(row) > 0 else 0)
    
    may_dates = [d.strftime('%m-%d') for d in may_biz_range]
    
    # Stats
    total = sum(june_quantities)
    n = len(june_quantities)
    mean_qty = total / n if n > 0 else 0
    variance = sum((q - mean_qty) ** 2 for q in june_quantities) / n if n > 0 else 0
    std_dev = variance ** 0.5
    cv = round(std_dev / mean_qty * 100, 1) if mean_qty > 0 else 0
    
    # Linear trend: simple regression on business day index
    if n > 1:
        xs = list(range(n))
        sum_x = sum(xs)
        sum_y = sum(june_quantities)
        sum_xy = sum(x * y for x, y in zip(xs, june_quantities))
        sum_xx = sum(x * x for x in xs)
        denom = n * sum_xx - sum_x * sum_x
        slope = round((n * sum_xy - sum_x * sum_y) / denom, 2) if denom != 0 else 0
    else:
        slope = 0
    
    max_qty = max(june_quantities)
    sales_days = sum(1 for q in june_quantities if q > 0)
    
    # Comparison M/M: match same number of business days
    may_total = sum(may_quantities[:JUNE_ELAPSED_BIZ])
    mom_change = round((total - may_total) / may_total * 100, 1) if may_total > 0 else None
    
    # Brand and price tier lookup
    nk = norm_key(model_name)
    model_brand, model_tier = model_attr_lookup.get(nk, ('', '未知'))
    
    model_daily_trends.append({
        'model': model_name,
        'brand': model_brand,
        'price_tier': model_tier,
        'june_dates': june_dates,
        'june_daily': june_quantities,
        'may_dates': may_dates,
        'may_daily': may_quantities,
        'total_june': total,
        'total_may': may_total,
        'avg_daily': round(mean_qty, 1),
        'max_daily': max_qty,
        'cv_pct': cv,  # coefficient of variation (volatility)
        'trend_slope': slope,  # linear trend slope
        'sales_days': sales_days,
        'mom_change': mom_change,  # month-over-month change %
    })

model_daily_trends.sort(key=lambda x: x['total_june'], reverse=True)
print(f"  Model daily trends: {len(model_daily_trends)} models computed")

# ========== BUILD JSON ==========
print("\nBuilding output JSON...")

# Category structure: ALL categories except "服务" and "不需要"
all_cat_colors = {
    '智能机': '#3b82f6', '平板电脑': '#8b5cf6', '功能机': '#f59e0b',
    '手机配件': '#22c55e', '家电': '#ec4899', '电脑数码': '#14b8a6',
    'solar system': '#f97316', '照明': '#a3e635',
    '文体礼品': '#06b6d4', '生活品': '#e11d48'
}
cat_structure = []
for cat_name in june['统计分类'].dropna().unique():
    if cat_name in ['服务', '不需要']:
        continue
    cd = june[june['统计分类'] == cat_name]
    cat_structure.append({
        'name': cat_name,
        'qty': round(cd['销售数量'].sum(), 0),
        'revenue': round(cd['零售金额'].sum(), 0),
        'profit': round(cd['毛利'].sum(), 0),
        'color': all_cat_colors.get(cat_name, '#64748b')
    })
# Sort by revenue desc
cat_structure.sort(key=lambda x: x['revenue'], reverse=True)

# ========== COST DATA PROCESSING ==========
cost_records = []
if cost is not None:
    print("Processing cost data...")
    cost_models = cost.groupby('商品名称')

    for model_name, grp in cost_models:
        grp = grp.sort_values('进货日期', ascending=False)
        batches = []
        total_stock = 0.0
        total_cost_value = 0.0

        for _, r in grp.iterrows():
            stock = max(0, float(r['结存数量']))
            unit_cost_tax = float(r['含税进货单价'])
            unit_cost_notax = float(r['无税进货单价'])
            batch_date = r['进货日期']
            aging = float(r.get('库龄天数', 0)) if pd.notna(r.get('库龄天数')) else 0
            rate = float(r.get('汇率', 1)) if pd.notna(r.get('汇率')) else 1

            batches.append({
                'date': batch_date.strftime('%Y-%m-%d') if pd.notna(batch_date) else '',
                'unit_cost_tax': round(unit_cost_tax, 2),
                'unit_cost_notax': round(unit_cost_notax, 2),
                'stock': int(stock),
                'aging_days': int(aging),
                'rate': round(rate, 2),
            })
            total_stock += stock
            total_cost_value += stock * unit_cost_tax

        if total_stock > 0:
            weighted_avg_cost_tax = round(total_cost_value / total_stock, 2)
        else:
            costs = [b['unit_cost_tax'] for b in batches if b['unit_cost_tax'] > 0]
            weighted_avg_cost_tax = round(sum(costs) / len(costs), 2) if costs else 0

        all_costs = [b['unit_cost_tax'] for b in batches if b['unit_cost_tax'] > 0]
        min_cost_tax = round(min(all_costs), 2) if all_costs else 0
        max_cost_tax = round(max(all_costs), 2) if all_costs else 0

        brand = grp.iloc[0].get('商品品牌', '')
        cat = grp.iloc[0].get('商品分类', '')

        cost_records.append({
            'model': model_name,
            'brand': str(brand) if pd.notna(brand) else '',
            'category': str(cat) if pd.notna(cat) else '',
            'total_stock': int(total_stock),
            'total_cost_value': round(total_cost_value, 2),
            'weighted_avg_cost_tax': weighted_avg_cost_tax,
            'min_cost_tax': min_cost_tax,
            'max_cost_tax': max_cost_tax,
            'batch_count': len(batches),
            'batches': batches,
            'cost_spread': round(max_cost_tax - min_cost_tax, 2),
        })

    cost_records.sort(key=lambda x: x['total_cost_value'], reverse=True)
    print(f"Cost models processed: {len(cost_records)}")
    print(f"Models with multiple batches: {sum(1 for r in cost_records if r['batch_count'] > 1)}")
    print(f"Models with cost variance: {sum(1 for r in cost_records if r['cost_spread'] > 0)}")

# ========== PRICE CHANGE ANALYSIS ==========
price_analysis = []  # list of price change records
price_summary = {}   # summary stats

# Extract price list dates from filenames
import re as _re
def _extract_price_date(fn):
    if fn:
        m = _re.search(r'(\d{2})\.(\d{2})\.(\d{4})', fn.split('/')[-1])
        if m:
            day, month, year = m.groups()
            return f'{year}年{int(month)}月{int(day)}日'
    return None

if args.price_list and args.price_list_compare:
    print("Processing price change analysis...")
    try:
        pl_cmp_raw = pd.read_excel(args.price_list_compare)
    except Exception as e:
        pl_cmp_raw = pd.read_excel(args.price_list_compare, engine='openpyxl')
    pl_cmp = normalize_spaces(pl_cmp_raw)

    # Build compare price map (same logic as current price map)
    cmp_price_map = {}
    cmp_brand_map = {}
    for _, r in pl_cmp.iterrows():
        mdl = str(r['SYSTEM MODEL NAME']).strip().upper()
        mdl_ns = mdl.replace(' ', '')
        price, src = resolve_price(r)
        cmp_price_map[mdl_ns] = (price, src)
        cmp_brand_map[mdl_ns] = str(r.get('BRANDS', '')).strip()

    # Get individual price levels for both periods
    def get_price_levels(row):
        """Return dict of all price levels."""
        levels = {}
        for col in ['PROMO PRICE', 'RRP WITH VAT', '3C HUB', 'RRP']:
            val = safe_float(row.get(col))
            if not pd.isna(val) and val > 0:
                levels[col] = round(val, 0)
        return levels

    # Build full price info for current and compare
    cur_full = {}  # model_ns -> {brand, price, source, promo_price, rrp_vat, 3c_hub, rrp}
    for _, r in pl.iterrows():
        mdl = str(r['SYSTEM MODEL NAME']).strip().upper()
        mdl_ns = mdl.replace(' ', '')
        levels = get_price_levels(r)
        price, src = resolve_price(r)
        cur_full[mdl_ns] = {
            'model': mdl,
            'brand': str(r.get('BRANDS', '')).strip(),
            'price': price,
            'price_source': src,
            'promo_price': levels.get('PROMO PRICE'),
            'rrp_vat': levels.get('RRP WITH VAT'),
            '3c_hub': levels.get('3C HUB'),
            'rrp': levels.get('RRP'),
            'is_promo': 'PROMO PRICE' in levels,
        }

    cmp_full = {}
    for _, r in pl_cmp.iterrows():
        mdl = str(r['SYSTEM MODEL NAME']).strip().upper()
        mdl_ns = mdl.replace(' ', '')
        levels = get_price_levels(r)
        price, src = resolve_price(r)
        cmp_full[mdl_ns] = {
            'model': mdl,
            'brand': str(r.get('BRANDS', '')).strip(),
            'price': price,
            'price_source': src,
            'promo_price': levels.get('PROMO PRICE'),
            'rrp_vat': levels.get('RRP WITH VAT'),
            '3c_hub': levels.get('3C HUB'),
            'rrp': levels.get('RRP'),
            'is_promo': 'PROMO PRICE' in levels,
        }

    # Cross-match and compute changes
    # 1. Models in both lists with price changes
    total_models_current = len(cur_full)
    total_models_compare = len(cmp_full)

    changes = []  # all models with meaningful data
    new_models = []  # only in current
    removed_models = []  # only in compare

    price_increases = 0
    price_decreases = 0
    new_promos = 0
    ended_promos = 0
    promo_price_changed = 0

    # Match model names between current and compare
    # Strategy: exact match on model_ns, then fuzzy substring match
    matched_pairs = {}  # cur_ns -> cmp_ns

    # First pass: exact match
    for cur_ns in cur_full:
        if cur_ns in cmp_full:
            matched_pairs[cur_ns] = cur_ns

    # Second pass: substring match for unmatched
    unmatched_cur = set(cur_full.keys()) - set(matched_pairs.keys())
    unmatched_cmp = set(cmp_full.keys()) - set(matched_pairs.values())

    for cur_ns in unmatched_cur:
        for cmp_ns in unmatched_cmp:
            if cur_ns in cmp_ns or cmp_ns in cur_ns:
                matched_pairs[cur_ns] = cmp_ns
                unmatched_cmp.discard(cmp_ns)
                break

    for cur_ns, cur_info in cur_full.items():
        if cur_ns in matched_pairs:
            cmp_ns = matched_pairs[cur_ns]
            cmp_info = cmp_full[cmp_ns]

            cur_price = cur_info['price']
            cmp_price = cmp_info['price']

            # Check if effective price changed
            price_changed = False
            diff = 0
            pct = 0
            if pd.notna(cur_price) and pd.notna(cmp_price) and cur_price != cmp_price:
                price_changed = True
                diff = round(cur_price - cmp_price, 0)
                pct = round((cur_price - cmp_price) / cmp_price * 100, 1) if cmp_price > 0 else 0
                if diff > 0:
                    price_increases += 1
                else:
                    price_decreases += 1

            # Check promo status change
            promo_change = 'no_change'
            cur_is_promo = cur_info['is_promo']
            cmp_is_promo = cmp_info['is_promo']

            if cur_is_promo and not cmp_is_promo:
                promo_change = 'new_promo'
                new_promos += 1
            elif not cur_is_promo and cmp_is_promo:
                promo_change = 'ended_promo'
                ended_promos += 1
            elif cur_is_promo and cmp_is_promo:
                cur_promo_price = cur_info.get('promo_price')
                cmp_promo_price = cmp_info.get('promo_price')
                if pd.notna(cur_promo_price) and pd.notna(cmp_promo_price) and cur_promo_price != cmp_promo_price:
                    promo_change = 'promo_price_changed'
                    promo_price_changed += 1

            # Get sales impact: find model in M10 and M11
            model_short = cur_info['model']  # original model name from price list
            # Try to find matching sales data
            m10_match = None
            m11_match = None
            for m in m10_model_analysis:
                m_ns = norm_key(m['model'])
                if cur_ns == m_ns or cur_ns in m_ns or m_ns in cur_ns:
                    m10_match = m
                    break
            for m in model_daily_trends:
                m_ns = norm_key(m['model'])
                if cur_ns == m_ns or cur_ns in m_ns or m_ns in cur_ns:
                    m11_match = m
                    break

            june_sales_qty = m10_match['qty'] if m10_match else None
            june_daily_avg = m10_match['daily_avg'] if m10_match else None
            mom_change = m11_match['mom_change'] if m11_match else None

            changes.append({
                'model': model_short,
                'brand': cur_info['brand'] or cmp_info['brand'],
                'price_tier': get_price_tier(cur_price) if pd.notna(cur_price) else '未知',
                'cur_price': int(cur_price) if pd.notna(cur_price) else None,
                'cmp_price': int(cmp_price) if pd.notna(cmp_price) else None,
                'cur_source': cur_info['price_source'],
                'cmp_source': cmp_info['price_source'],
                'cur_promo_price': cur_info.get('promo_price'),
                'cmp_promo_price': cmp_info.get('promo_price'),
                'cur_rrp_vat': cur_info.get('rrp_vat'),
                'cmp_rrp_vat': cmp_info.get('rrp_vat'),
                'price_changed': price_changed,
                'diff': int(diff) if price_changed else 0,
                'pct': pct if price_changed else 0,
                'promo_change': promo_change,
                'june_sales_qty': june_sales_qty,
                'june_daily_avg': june_daily_avg,
                'mom_sales_change': mom_change,
            })
        else:
            # New model (only in current)
            new_models.append({
                'model': cur_info['model'],
                'brand': cur_info['brand'],
                'price': int(cur_info['price']) if pd.notna(cur_info['price']) else None,
                'price_source': cur_info['price_source'],
                'is_promo': cur_info['is_promo'],
                'price_tier': get_price_tier(cur_info['price']) if pd.notna(cur_info['price']) else '未知',
            })

    for cmp_ns in set(cmp_full.keys()) - set(matched_pairs.values()):
        cmp_info = cmp_full[cmp_ns]
        removed_models.append({
            'model': cmp_info['model'],
            'brand': cmp_info['brand'],
            'price': int(cmp_info['price']) if pd.notna(cmp_info['price']) else None,
        })

    # Sort changes by absolute pct desc (most impactful first)
    changes_with_price_change = [c for c in changes if c['price_changed']]
    changes_with_price_change.sort(key=lambda x: abs(x['pct']), reverse=True)
    changes_no_price_change = [c for c in changes if not c['price_changed']]
    # Only include models with actual changes in the main list
    price_analysis = changes_with_price_change + [c for c in changes_no_price_change if c['promo_change'] != 'no_change']
    # Sort all: price changes first, then promo changes
    price_analysis.sort(key=lambda x: (0 if x['price_changed'] else 1, -abs(x.get('pct', 0))))

    price_summary = {
        'total_current_models': total_models_current,
        'total_compare_models': total_models_compare,
        'total_matched': len(matched_pairs),
        'price_increases': price_increases,
        'price_decreases': price_decreases,
        'total_price_changes': price_increases + price_decreases,
        'new_promos': new_promos,
        'ended_promos': ended_promos,
        'promo_price_changed': promo_price_changed,
        'new_models_count': len(new_models),
        'removed_models_count': len(removed_models),
        'change_records_count': len(price_analysis),
        'current_price_date': _extract_price_date(args.price_list),
        'compare_price_date': _extract_price_date(args.price_list_compare),
    }

    print(f"Price changes: {price_increases} increases, {price_decreases} decreases")
    print(f"Promo changes: {new_promos} new, {ended_promos} ended, {promo_price_changed} price changed")
    print(f"New models: {len(new_models)}, Removed: {len(removed_models)}")

output = {
    'meta': {
        'report_date': today_str,
        'period': f'{curr_start.strftime("%Y-%m-%d")} ~ {today_str}',
        'elapsed_days': ELAPSED_DAYS,
        'remaining_days': REMAINING_DAYS,
        'total_biz_days': TOTAL_BIZ_DAYS,
        'time_progress_pct': round(time_progress * 100, 1),
        'current_month': curr_month,
        'compare_month': compare_month,
        'total_target': round(TOTAL_TARGET, 1),
        'total_smart_qty': round(june_smart_qty, 1),
        'total_feature_qty': round(june_feature_qty, 1),
        'total_all_qty': round(june_all_qty, 1),
        'total_revenue': round(june_total_revenue, 0),
        'total_profit': round(june_total_profit, 0),
        'completion_rate': round(june_smart_qty / TOTAL_TARGET * 100, 1) if TOTAL_TARGET > 0 else 0,
        'may_smart_qty_15d': round(may_smart_qty_biz, 1),  # Business days matched
        'mom_change': round((june_smart_qty - may_smart_qty_biz) / may_smart_qty_biz * 100, 1) if may_smart_qty_biz > 0 else 0,
        'daily_avg_smart': round(june_smart_qty / ELAPSED_DAYS, 1),
        'daily_needed': round(daily_needed_total, 1),
        'total_gap': round(total_gap, 1),
    },
    'm1_store_target': store_perf,
    'm1_tier_summary': m1_tier_summary,
    'm2_store_category': store_cat[:40],
    'cat_structure': cat_structure,
    'm3_brands': june_brands.to_dict('records'),
    'm4_daily_detail': store_daily[:30],
    'm5_company_daily': company_daily,
    'm6_overstock_top': store_overstock_top,
    'm6_general_dead': general_dead,
    'm6_lowstock_top': lowstock_top,
    'm6_inv_store': inv_store_agg,
    'm6_turnover_summary': turnover_summary,
    'm6_brand_turnover': brand_turnover,
    'm6_model_turnover': model_turnover,
    'm6_store_model_turnover': store_model_turnover,
    'm6_all_brands': sorted(inv_turnover['品牌'].unique().tolist()),
    'm6_store_short_names': store_short_names,
    'm6_store_long_to_short': store_long_to_short,
    'm7_staff': {
        'total_staff': total_staff,
        'co_avg_smart': co_avg_smart,
        'co_avg_total': co_avg_total,
        'co_avg_profit': co_avg_profit,
        'store_efficiency': sp_eff_records,
        'top_salespersons': sp_rank.head(20).to_dict('records'),
        'bottom_salespersons': sp_rank[sp_rank['smart_qty'] >= 10].tail(10).to_dict('records'),
    },
    'm8_lagging': lagging_stores,
    'm9_issues': m9_issues,
    'm10_model_analysis': m10_model_analysis,
    'm10_price_tiers': ['全部', '10w以下', '10w', '20w', '30w', '40w', '50w', '50-100w', '100w以上'],
    'm10_all_brands': sorted(list(set(m['brand'] for m in m10_model_analysis if m['brand']))) if m10_model_analysis else [],
    'm11_model_trends': model_daily_trends,
    'm12_store_volatility': store_volatility,
    'm12_summary': m12_summary,
    'daily_chart': [{'d': r['date'], 'sq': int(r['smart_qty']), 'fq': int(r['feature_qty']),
                      'rev': int(r['revenue']), 'prof': int(r['profit']), 'may_sq': int(r['may_smart']),
                      'pr': r.get('profit_rate', 0)} for r in company_daily],
    'cost_data': cost_records,
    'price_analysis': price_analysis,
    'price_summary': price_summary,
}

outpath = args.out
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, default=str)
print(f"JSON saved: {outpath}")
print(f"Store target records: {len(store_perf)}")
print(f"Brand records: {len(june_brands)}")
print(f"Store overstock: {len(store_overstock_top)}")
print(f"General dead: {len(general_dead)}")
print(f"Low stock alerts: {len(lowstock_top)}")
print(f"Store inventory: {len(inv_store_agg)}")
print(f"Staff efficiency stores: {len(sp_eff_records)}, total staff: {total_staff}")
print("DONE")
