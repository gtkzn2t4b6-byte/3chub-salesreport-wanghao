"""
Generate store-stockout.html and price_trends.html
"""
import json
import pandas as pd
import math

WORKSPACE = '/Users/wanghao/WorkBuddy/2026-07-02-11-18-30'
with open(f'{WORKSPACE}/dashboard_full.json') as f:
    D = json.load(f)

records = D.get('m6_store_model_turnover', [])
short_names = D.get('m6_store_long_to_short', {})
report_date = D.get('meta', {}).get('report_date', '2026-06-30')
business_days = 26  # June has ~26 business days

# ========== STORE STOCKOUT ==========
def get_rating(row):
    sellable = row.get('可卖数', 0) or 0
    turn = row.get('turnover_days', 9999) or 9999
    sales = row.get('sales_qty', 0) or 0
    if sellable == 0 and sales > 0:
        return ("OUT OF STOCK", 1, "#ef4444")
    if sellable == 0 and sales == 0:
        return ("Dead Stock", 7, "#6b7280")
    if turn <= 3:
        return ("Stockout Warning", 2, "#f97316")
    if turn < 14:
        return ("Excellent", 4, "#22c55e")
    if turn <= 21:
        return ("Normal", 5, "#3b82f6")
    if turn <= 60:
        return ("Overstock Risk", 6, "#eab308")
    return ("Severe Overstock", 7, "#9333ea")

def get_suggestion(row, rating):
    sellable = row.get('可卖数', 0) or 0
    turn = row.get('turnover_days', 9999) or 9999
    sales = row.get('sales_qty', 0) or 0
    general = row.get('总仓库存', 0) or 0
    model = row.get('商品型号', '')
    if rating == "OUT OF STOCK":
        if general > 0:
            return f"URGENT: {int(general)} units in central stock. Prioritize transfer."
        return f"No stock. Check central warehouse."
    if rating == "Stockout Warning":
        if general > 0:
            return f"{int(general)} units available in central. Recommend transfer."
        return "Low stock. Monitor closely."
    if rating == "Excellent":
        return "Healthy stock level."
    if rating == "Normal":
        return "Monitor sales trend."
    if rating == "Overstock Risk":
        return "Consider promotion to accelerate sales."
    if rating == "Severe Overstock":
        return "Heavy overstock. Urgent promotion or return needed."
    return "Dead stock. Liquidation or return to supplier."

all_records = []
for r in records:
    rating, severity, color = get_rating(r)
    suggestion = get_suggestion(r, rating)
    sellable = r.get('可卖数', 0) or 0
    transit = r.get('在途', 0) or 0
    total = sellable + transit
    sales = r.get('sales_qty', 0) or 0
    turn = r.get('turnover_days', 9999) or 9999
    daily_avg = round(sales / business_days, 1) if business_days > 0 else 0
    store_raw = r.get('inv_store', '')
    store = short_names.get(store_raw, store_raw)
    cat_raw = r.get('二级分类名称', '')
    cat_disp = 'Smartphone' if 'SMART' in str(cat_raw) else ('Tablet' if 'TABLET' in str(cat_raw) else str(cat_raw))
    all_records.append({
        'store': store, 'brand': r.get('品牌', ''), 'model': r.get('商品型号', ''),
        'category': cat_disp, 'sellable': int(sellable), 'transit': int(transit),
        'total': int(total), 'general': int(r.get('总仓库存', 0) or 0),
        'daily_avg': daily_avg, 'sales': int(sales), 'turnover': round(turn, 1),
        'rating': rating, 'rating_color': color, 'severity': severity, 'suggestion': suggestion,
    })

stockout_records = [r for r in all_records if r['turnover'] <= 3 or r['sellable'] == 0]
stockout_records.sort(key=lambda x: -x['sales'])

stores_list = sorted(set(r['store'] for r in all_records))
brands_list = sorted(set(r['brand'] for r in all_records))
categories_list = sorted(set(r['category'] for r in all_records))

stockout_json = json.dumps(stockout_records, ensure_ascii=False)
all_json = json.dumps(all_records, ensure_ascii=False)

# ========== PRICE TRENDS ==========
def clean_cols(df):
    df.columns = [c.strip().strip("'") if isinstance(c, str) else c for c in df.columns]
    return df

price_current = clean_cols(pd.read_excel('/Users/wanghao/Downloads/Retail price list 29.06.2026.xlsx'))
price_compare = clean_cols(pd.read_excel('/Users/wanghao/Downloads/Retail price list 21.05.2026.xlsx'))

def to_num(v):
    try:
        return float(str(v).replace(',', ''))
    except:
        return None

def get_price(row):
    """Priority: PROMO PRICE > RRP WITH VAT > 3C HUB"""
    promo = row.get('PROMO PRICE')
    rrp_vat = row.get('RRP WITH VAT')
    c3chub = row.get('3C HUB')
    for v in [promo, rrp_vat, c3chub]:
        p = to_num(v)
        if p and p > 0:
            return p
    return None

# Build price dicts
price_cur = {}
for _, row in price_current.iterrows():
    model = str(row.get('SYSTEM MODEL NAME', '')).strip()
    p = get_price(row)
    if model and p:
        price_cur[model] = p

price_old = {}
for _, row in price_compare.iterrows():
    model = str(row.get('SYSTEM MODEL NAME', '')).strip()
    p = get_price(row)
    if model and p:
        price_old[model] = p

# Get M11 model trends for before/after sales
m11 = D.get('m11_model_trends', [])
# Group by model
from collections import defaultdict
m11_by_model = defaultdict(list)
for item in m11:
    m11_by_model[item['model']].append(item)

# Compute price changes and sales impact
price_trends = []
for model, from_p in price_old.items():
    to_p = price_cur.get(model)
    if to_p is None:
        continue
    if from_p == to_p:
        continue
    direction = 'up' if to_p > from_p else 'down'
    pct = round((to_p - from_p) / from_p * 100, 2)

    # Find brand from M11
    brand = ''
    price_tier = ''
    daily_sales_list = []
    total_qty = 0
    for item in m11_by_model.get(model, []):
        brand = item.get('brand', '') or brand
        price_tier = item.get('price_tier', '') or price_tier
        for d in item.get('daily', []):
            daily_sales_list.append(d.get('qty', 0))
        total_qty += sum(d.get('qty', 0) for d in item.get('daily', []))

    daily_avg = round(total_qty / business_days, 1) if business_days > 0 else 0

    # Count before/after sales (use 5/21 as switch point ~34 days before report date)
    # price_compare is 21 May, price_current is 29 June
    # ~19 days at old price (May 21 - Jun 8), ~21 days at new price (Jun 9 - Jun 29)
    # Actually the compare list is from May 21, so:
    # - Days at old price: May 21 to Jun 8 = 19 days
    # - Days at new price: Jun 9 to Jun 29 = 21 days
    # But we only have June data. Let's approximate:
    # Use the middle of June as the price change date (Jun 9 is ~19 days into June)
    # Actually let's just use the full June data and divide:
    # If price changed around Jun 9, that's 19 days at old, 21 days at new (out of 26 business days)
    before_days = 19
    after_days = 21

    # Get daily sales for each day
    daily_data = daily_sales_list if daily_sales_list else [0] * business_days
    before_sales = sum(daily_data[:before_days])
    after_sales = sum(daily_data[before_days:before_days+after_days])
    before_avg = round(before_sales / before_days, 1) if before_days > 0 else 0
    after_avg = round(after_sales / after_days, 1) if after_days > 0 else 0
    sales_pct = round((after_avg - before_avg) / before_avg * 100, 1) if before_avg > 0 else 0

    elasticity = round(abs(sales_pct / pct), 2) if pct != 0 else 0
    severity = round(abs(pct) * abs(sales_pct), 1) if direction == 'up' and sales_pct < 0 else round(abs(pct), 1)

    price_trends.append({
        'brand': brand, 'model': model, 'total_qty': total_qty, 'daily_avg': daily_avg,
        'price_tier': price_tier, 'current_price': int(to_p),
        'from_price': int(from_p), 'to_price': int(to_p),
        'price_pct': pct, 'before_avg': before_avg, 'after_avg': after_avg,
        'sales_pct': sales_pct, 'elasticity': elasticity, 'severity': severity,
        'direction': direction,
    })

price_trends.sort(key=lambda x: -abs(x['severity']))
price_data_json = json.dumps(price_trends, ensure_ascii=False)
print(f"Price trends: {len(price_trends)} models with price changes")

# ========== GENERATE PRICE TRENDS HTML ==========
def naira(v):
    if v is None or v == 0:
        return '-'
    return '₦{:,.0f}'.format(v).replace(',', ',')

price_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>3CHUB Price Trends - Impact Analysis</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f172a;color:#f1f5f9;font-size:13px}}
.header{{background:#1e293b;padding:16px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #334155}}
.header h1{{font-size:18px}}
.header .meta{{color:#94a3b8;font-size:12px}}
.content{{padding:20px 24px}}
.summary{{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap}}
.card{{background:#1e293b;border-radius:8px;padding:16px 20px;flex:1;min-width:150px}}
.card .val{{font-size:24px;font-weight:700}}
.card .lbl{{font-size:11px;color:#94a3b8;margin-top:4px;text-transform:uppercase}}
.filters{{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center}}
.filters select,.filters input{{background:#1e293b;color:#f1f5f9;border:1px solid #334155;border-radius:6px;padding:7px 12px;font-size:12px}}
.filters button{{background:#334155;color:#f1f5f9;border:none;border-radius:6px;padding:7px 16px;cursor:pointer;font-size:12px}}
.filters button:hover{{background:#475569}}
.chart-wrap{{background:#1e293b;border-radius:8px;padding:16px;margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden}}
th{{background:#334155;padding:10px 8px;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;white-space:nowrap;cursor:pointer}}
th:hover{{background:#475569}}
td{{padding:9px 8px;border-bottom:1px solid #1e293b;font-size:12px}}
tr:hover td{{background:#1e3a5f}}
.up{{color:#ef4444}}
.down{{color:##22c55e}}
.neutral{{color:#94a3b8}}
.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
.up .dot{{background:#ef4444}}
.down .dot{{background:#22c55e}}
.highlight{{background:#7f1d1d}}
</style>
</head>
<body>
<div class="header">
  <h1>3CHUB Price Change Impact Analysis</h1>
  <div class="meta">Report: {report_date} | Compare: 2026-05-21 vs 2026-06-29 | Price change period: ~Jun 9-29, 2026</div>
</div>
<div class="content">
  <div class="summary">
    <div class="card" style="border-left:3px solid #ef4444">
      <div class="val" style="color:#ef4444" id="cnt-up">0</div>
      <div class="lbl">Price Increases</div>
    </div>
    <div class="card" style="border-left:3px solid #22c55e">
      <div class="val" style="color:#22c55e" id="cnt-down">0</div>
      <div class="lbl">Price Decreases</div>
    </div>
    <div class="card" style="border-left:3px solid #fbbf24">
      <div class="val" style="color:#fbbf24" id="cnt-total">0</div>
      <div class="lbl">Total Changed</div>
    </div>
    <div class="card" style="border-left:3px solid #38bdf8">
      <div class="val" id="avg-severity">0</div>
      <div class="lbl">Avg Price Change%</div>
    </div>
  </div>

  <div class="filters">
    <select id="f-brand"><option value="">All Brands</option></select>
    <select id="f-tier"><option value="">All Price Tiers</option></select>
    <select id="f-dir"><option value="">All Directions</option><option value="up">Price Up</option><option value="down">Price Down</option></select>
    <input type="text" id="f-search" placeholder="Search model..." oninput="render()">
    <button onclick="document.getElementById('f-search').value='';['f-brand','f-tier','f-dir'].forEach(id=>document.getElementById(id).value='');render()">Clear</button>
  </div>

  <div id="stats" style="margin-bottom:12px;font-size:12px;color:#94a3b8"></div>

  <div style="overflow-x:auto">
  <table id="pt">
    <thead><tr>
      <th onclick="sort('brand')">Brand</th>
      <th onclick="sort('model')">Model</th>
      <th onclick="sort('price_tier')">Price Tier</th>
      <th onclick="sort('from_price')">Old Price</th>
      <th onclick="sort('to_price')">New Price</th>
      <th onclick="sort('price_pct')">Change%</th>
      <th onclick="sort('before_avg')">Daily Avg (Before)</th>
      <th onclick="sort('after_avg')">Daily Avg (After)</th>
      <th onclick="sort('sales_pct')">Sales Change%</th>
      <th onclick="sort('elasticity')">Elasticity</th>
      <th onclick="sort('severity')">Severity</th>
    </tr></thead>
    <tbody id="pt-body"></tbody>
  </table>
  </div>
</div>
<script>
const DATA = {price_data_json};

let sortKey = 'severity', sortAsc = false;

function naira(v) {{
  if (!v && v !== 0) return '-';
  return '₦' + Number(v).toLocaleString();
}}

function pct(v) {{
  if (!v && v !== 0) return '-';
  const sign = v > 0 ? '+' : '';
  return sign + v + '%';
}}

function getFiltered() {{
  const brand = document.getElementById('f-brand').value;
  const tier = document.getElementById('f-tier').value;
  const dir = document.getElementById('f-dir').value;
  const kw = document.getElementById('f-search').value.toLowerCase();
  return DATA.filter(r =>
    (!brand || r.brand === brand) && (!tier || r.price_tier === tier) &&
    (!dir || r.direction === dir) && (!kw || r.model.toLowerCase().includes(kw) || r.brand.toLowerCase().includes(kw))
  );
}}

function render() {{
  const rows = getFiltered().sort((a,b) => {{
    const av = a[sortKey], bv = b[sortKey];
    if (typeof av === 'number') return sortAsc ? av - bv : bv - av;
    return sortAsc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
  }});
  document.getElementById('stats').textContent = `Showing ${{rows.length}} of ${{DATA.length}} price-changed models`;
  document.getElementById('pt-body').innerHTML = rows.map(r => {{
    const dirClass = r.direction === 'up' ? 'up' : 'down';
    const salesColor = r.sales_pct > 0 ? '#22c55e' : r.sales_pct < 0 ? '#ef4444' : '#94a3b8';
    const isImpactful = r.direction === 'up' && r.sales_pct < -20;
    return `<tr style="${{isImpactful ? 'background:#450a0a' : ''}}">
      <td>${{r.brand}}</td>
      <td>${{r.model}}</td>
      <td>${{r.price_tier || '-'}}</td>
      <td>${{naira(r.from_price)}}</td>
      <td>${{naira(r.to_price)}}</td>
      <td class="${{dirClass}}"><span class="dot"></span>${{pct(r.price_pct)}}</td>
      <td>${{r.before_avg || '-'}}</td>
      <td>${{r.after_avg || '-'}}</td>
      <td style="color:${{salesColor}}">${{pct(r.sales_pct)}}</td>
      <td>${{r.elasticity || '-'}}</td>
      <td>${{r.severity || '-'}}</td>
    </tr>`;
  }}).join('');
}}

function sort(key) {{
  if (sortKey === key) sortAsc = !sortAsc;
  else {{ sortKey = key; sortAsc = false; }}
  render();
}}

// KPI
const up = DATA.filter(r => r.direction === 'up').length;
const down = DATA.filter(r => r.direction === 'down').length;
document.getElementById('cnt-up').textContent = up;
document.getElementById('cnt-down').textContent = down;
document.getElementById('cnt-total').textContent = DATA.length;
const avgPct = DATA.length ? (DATA.reduce((s,r) => s + Math.abs(r.price_pct), 0) / DATA.length).toFixed(1) : 0;
document.getElementById('avg-severity').textContent = avgPct + '%';

// Populate filters
const brands = [...new Set(DATA.map(r => r.brand))].sort();
const tiers = [...new Set(DATA.map(r => r.price_tier).filter(Boolean))].sort();
brands.forEach(b => {{ const o = document.createElement('option'); o.value=b; o.textContent=b; document.getElementById('f-brand').appendChild(o); }});
tiers.forEach(t => {{ const o = document.createElement('option'); o.value=t; o.textContent=t; document.getElementById('f-tier').appendChild(o); }});

render();
</script>
</body>
</html>"""

with open(f'{WORKSPACE}/deploy/price_trends.html', 'w', encoding='utf-8') as f:
    f.write(price_html)
print(f"price_trends.html written: {len(price_html):,} bytes")

# ========== STORE STOCKOUT HTML ==========
stockout_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>3CHUB Store Stockout &amp; Inventory Alert</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f172a;color:#f1f5f9;font-size:13px}}
.header{{background:#1e293b;padding:16px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #334155}}
.header h1{{font-size:18px}}
.header .meta{{color:#94a3b8;font-size:12px}}
.tabs{{display:flex;background:#1e293b;border-bottom:1px solid #334155}}
.tab{{padding:12px 24px;cursor:pointer;color:#94a3b8;font-weight:500;border-bottom:2px solid transparent;transition:all .2s}}
.tab:hover{{color:#f1f5f9}}
.tab.active{{color:#38bdf8;border-bottom-color:#38bdf8}}
.content{{padding:20px 24px}}
.kpi-row{{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap}}
.kpi{{background:#1e293b;border-radius:8px;padding:16px 24px;flex:1;min-width:150px}}
.kpi .val{{font-size:28px;font-weight:700}}
.kpi .lbl{{font-size:11px;color:#94a3b8;margin-top:4px;text-transform:uppercase}}
.filters{{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center}}
.filters input,.filters select{{background:#1e293b;color:#f1f5f9;border:1px solid #334155;border-radius:6px;padding:7px 12px;font-size:12px}}
.filters button{{background:#334155;color:#f1f5f9;border:none;border-radius:6px;padding:7px 16px;cursor:pointer;font-size:12px}}
.filters button:hover{{background:#475569}}
.page-section{{display:none}}
.page-section.active{{display:block}}
table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden}}
th{{background:#334155;padding:10px 8px;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;white-space:nowrap;cursor:pointer;position:sticky;top:0;z-index:10}}
th:hover{{background:#475569}}
td{{padding:9px 8px;border-bottom:1px solid #1e293b;font-size:12px}}
tr:hover td{{background:#1e3a5f}}
.stats-bar{{display:flex;gap:16px;margin-bottom:16px;font-size:12px;color:#94a3b8;flex-wrap:wrap}}
.export-btn{{background:#16a34a;color:#fff;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;font-size:12px}}
.pulse{{animation:pulse 1.5s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
</style>
</head>
<body>
<div class="header">
  <h1>3CHUB Inventory Alert</h1>
  <div class="meta">Report Date: {report_date} | Business Days: {business_days}</div>
</div>
<div class="tabs">
  <div class="tab active" onclick="showPage('stockout')" id="tab-stockout">Stockout Alert</div>
  <div class="tab" onclick="showPage('turnover')" id="tab-turnover">Store Turnover</div>
</div>
<div class="content">
  <div id="page-stockout" class="page-section active">
    <div class="kpi-row">
      <div class="kpi" style="border-left:3px solid #ef4444">
        <div class="val" style="color:#ef4444" id="kpi-oos">0</div>
        <div class="lbl">Out of Stock</div>
      </div>
      <div class="kpi" style="border-left:3px solid #f97316">
        <div class="val" style="color:#f97316" id="kpi-warn">0</div>
        <div class="lbl">Stockout Warning (&le;3d)</div>
      </div>
      <div class="kpi" style="border-left:3px solid #22c55e">
        <div class="val" style="color:#22c55e" id="kpi-exc">0</div>
        <div class="lbl">Excellent</div>
      </div>
      <div class="kpi" style="border-left:3px solid #eab308">
        <div class="val" style="color:#eab308" id="kpi-over">0</div>
        <div class="lbl">Overstock Risk</div>
      </div>
    </div>
    <div class="filters">
      <input type="text" id="so-search" placeholder="Search store / model..." oninput="renderSo()">
      <select id="so-brand" onchange="renderSo()"><option value="">All Brands</option></select>
      <select id="so-cat" onchange="renderSo()"><option value="">All Categories</option></select>
      <button onclick="clearSo()">Clear</button>
      <button class="export-btn" onclick="exportCsv(getFSo())">Export CSV</button>
    </div>
    <div class="stats-bar"><span id="so-stats"></span></div>
    <div style="overflow-x:auto">
    <table>
      <thead><tr>
        <th onclick="sortSo('store')">Store</th><th onclick="sortSo('brand')">Brand</th><th onclick="sortSo('model')">Model</th>
        <th onclick="sortSo('category')">Category</th><th onclick="sortSo('sellable')">Sellable Qty</th>
        <th onclick="sortSo('transit')">Transit Qty</th><th onclick="sortSo('total')">Total Qty</th>
        <th onclick="sortSo('general')">General Stock</th><th onclick="sortSo('daily_avg')">Daily Avg Sales</th>
        <th onclick="sortSo('sales')">Mo. Sales</th><th onclick="sortSo('turnover')">Days of Stock</th>
        <th onclick="sortSo('rating')">Rating</th><th onclick="sortSo('suggestion')">Suggestion</th>
      </tr></thead>
      <tbody id="so-tbody"></tbody>
    </table>
    </div>
  </div>

  <div id="page-turnover" class="page-section">
    <div class="filters">
      <input type="text" id="st-search" placeholder="Search store / model..." oninput="renderSt()">
      <select id="st-store" onchange="renderSt()"><option value="">All Stores</option></select>
      <select id="st-brand" onchange="renderSt()"><option value="">All Brands</option></select>
      <select id="st-cat" onchange="renderSt()"><option value="">All Categories</option></select>
      <select id="st-rating" onchange="renderSt()"><option value="">All Ratings</option></select>
      <button onclick="clearSt()">Clear</button>
      <button class="export-btn" onclick="exportCsv(getFSt())">Export CSV</button>
    </div>
    <div class="stats-bar"><span id="st-stats"></span></div>
    <div style="overflow-x:auto">
    <table>
      <thead><tr>
        <th onclick="sortSt('store')">Store</th><th onclick="sortSt('brand')">Brand</th><th onclick="sortSt('model')">Model</th>
        <th onclick="sortSt('category')">Category</th><th onclick="sortSt('sellable')">Sellable Qty</th>
        <th onclick="sortSt('transit')">Transit Qty</th><th onclick="sortSt('total')">Total Qty</th>
        <th onclick="sortSt('general')">General Stock</th><th onclick="sortSt('daily_avg')">Daily Avg Sales</th>
        <th onclick="sortSt('sales')">Mo. Sales</th><th onclick="sortSt('turnover')">Days of Stock</th>
        <th onclick="sortSt('rating')">Rating</th><th onclick="sortSt('suggestion')">Suggestion</th>
      </tr></thead>
      <tbody id="st-tbody"></tbody>
    </table>
    </div>
  </div>
</div>
<script>
const soData = {stockout_json};
const allData = {all_json};
let soK='sales',soA=false,stK='sales',stA=false;

const brands = {json.dumps(brands_list, ensure_ascii=False)};
const cats = {json.dumps(categories_list, ensure_ascii=False)};
const stores = {json.dumps(stores_list, ensure_ascii=False)};

function showPage(p){{
  ['stockout','turnover'].forEach(x=>{{
    document.getElementById('tab-'+x).classList.toggle('active',x===p);
    document.getElementById('page-'+x).classList.toggle('active',x===p);
  }});
}}

function e(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}}

function getFSo(){{
  const kw=document.getElementById('so-search').value.toLowerCase();
  const b=document.getElementById('so-brand').value;
  const c=document.getElementById('so-cat').value;
  return soData.filter(r=>(!kw||r.store.toLowerCase().includes(kw)||r.model.toLowerCase().includes(kw)||r.brand.toLowerCase().includes(kw))&&(!b||r.brand===b)&&(!c||r.category===c));
}}
function getFSt(){{
  const kw=document.getElementById('st-search').value.toLowerCase();
  const s=document.getElementById('st-store').value;
  const b=document.getElementById('st-brand').value;
  const c=document.getElementById('st-cat').value;
  const rt=document.getElementById('st-rating').value;
  return allData.filter(r=>(!kw||r.store.toLowerCase().includes(kw)||r.model.toLowerCase().includes(kw)||r.brand.toLowerCase().includes(kw))&&(!s||r.store===s)&&(!b||r.brand===b)&&(!c||r.category===c)&&(!rt||r.rating===rt));
}}

function makeRow(r,isSo){{
  const bg=r.rating==='OUT OF STOCK'?'#fee2e2':r.rating==='Stockout Warning'?'#fff7ed':'';
  const tc=r.sellable===0?'#ef4444':'#22c55e';
  const oosTag=(r.sellable===0&&r.sales>0&&isSo)?'<span style="background:#dc2626;color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:700;margin-left:4px" class="pulse">OUT</span>':'';
  const ratingBg=r.rating_color;
  const ratingFg=['OUT OF STOCK','Stockout Warning','Dead Stock'].includes(r.rating)?'#fff':'#000';
  return `<tr style="background:${{bg}}">
    <td>${{e(r.store)}}</td><td>${{e(r.brand)}}</td><td>${{e(r.model)}}${{oosTag}}
    <td>${{e(r.category)}}</td>
    <td style="color:${{tc}}">${{r.sellable}}</td>
    <td>${{r.transit>0?r.transit:'-'}}</td><td>${{r.total}}</td>
    <td>${{r.general}}</td><td>${{r.daily_avg}}</td><td>${{r.sales}}</td><td>${{r.turnover}}</td>
    <td style="background:${{ratingBg}};color:${{ratingFg}};font-weight:700;font-size:11px">${{e(r.rating)}}</td>
    <td style="font-size:11px;color:#94a3b8">${{e(r.suggestion)}}</td>
  </tr>`;
}}

function sortSo(k){{soK=k;soA=soK===k?!soA:false;renderSo();}}
function sortSt(k){{stK=k;stA=stK===k?!stA:false;renderSt();}}

function renderSo(){{
  const rows=getFSo().sort((a,b)=>{{const av=a[soK],bv=b[soK];return typeof av==='number'?soA?av-bv:bv-av:soA?String(av).localeCompare(String(bv)):String(bv).localeCompare(String(av));}});
  document.getElementById('so-stats').textContent=`Showing ${{rows.length}} of ${{soData.length}} (turnover ≤3d or out of stock)`;
  document.getElementById('so-tbody').innerHTML=rows.map(r => makeRow(r,true)).join('');
}}
function renderSt(){{
  const rows=getFSt().sort((a,b)=>{{const av=a[stK],bv=b[stK];return typeof av==='number'?stA?av-bv:bv-av:stA?String(av).localeCompare(String(bv)):String(bv).localeCompare(String(av));}});
  document.getElementById('st-stats').textContent=`Showing ${{rows.length}} of ${{allData.length}} records`;
  document.getElementById('st-tbody').innerHTML=rows.map(r => makeRow(r,false)).join('');
}}

function clearSo(){{document.getElementById('so-search').value='';document.getElementById('so-brand').value='';document.getElementById('so-cat').value='';renderSo();}}
function clearSt(){{['st-search','st-store','st-brand','st-cat','st-rating'].forEach(id=>document.getElementById(id).value='');renderSt();}}

function exportCsv(rows){{
  const cols=['store','brand','model','category','sellable','transit','total','general','daily_avg','sales','turnover','rating','suggestion'];
  const csv=[cols.join(',')].concat(rows.map(r=>cols.map(c=>'"'+(String(r[c]||'').replace(/"/g,'""'))+'"').join(','))).join('\\n');
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}}));
  a.download='inventory_'+(new Date().toISOString().slice(0,10))+'.csv';a.click();
}}

// KPI
document.getElementById('kpi-oos').textContent=soData.filter(r=>r.sellable===0).length;
document.getElementById('kpi-warn').textContent=soData.filter(r=>r.sellable>0&&r.turnover<=3).length;
document.getElementById('kpi-exc').textContent=allData.filter(r=>r.rating==='Excellent').length;
document.getElementById('kpi-over').textContent=allData.filter(r=>['Overstock Risk','Severe Overstock'].includes(r.rating)).length;

// Dropdowns
brands.forEach(b=>{{['so-brand','st-brand'].forEach(id=>{{const o=document.createElement('option');o.value=b;o.textContent=b;document.getElementById(id).appendChild(o);}});}});
cats.forEach(c=>{{['so-cat','st-cat'].forEach(id=>{{const o=document.createElement('option');o.value=c;o.textContent=c;document.getElementById(id).appendChild(o);}});}});
stores.forEach(s=>{{const o=document.createElement('option');o.value=s;o.textContent=s;document.getElementById('st-store').appendChild(o);}});
const allRatings=['OUT OF STOCK','Stockout Warning','Excellent','Normal','Overstock Risk','Severe Overstock','Dead Stock'];
allRatings.forEach(r=>{{const o=document.createElement('option');o.value=r;o.textContent=r;document.getElementById('st-rating').appendChild(o);}});

renderSo();
</script>
</body>
</html>"""

with open(f'{WORKSPACE}/deploy/store-stockout.html', 'w', encoding='utf-8') as f:
    f.write(stockout_html)
print(f"store-stockout.html written: {len(stockout_html):,} bytes")
