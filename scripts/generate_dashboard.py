#!/usr/bin/env python3
"""Generate the full 9-module sales dashboard HTML"""
import argparse
import json

parser = argparse.ArgumentParser(description='Generate sales dashboard HTML')
parser.add_argument('--data', required=True, help='Path to dashboard_full.json')
parser.add_argument('--history', default=None, help='Path to historical_data.json (optional)')
parser.add_argument('--out', default='dashboard_director.html', help='Output HTML file path')
args = parser.parse_args()

with open(args.data) as f:
    D = json.load(f)

# Load historical data if available
H = None
if args.history:
    try:
        with open(args.history) as f:
            H = json.load(f)
    except:
        pass

# Ensure required keys exist with defaults
D.setdefault('m9_issues', [])
D.setdefault('m1_tier_summary', [])
D.setdefault('price_analysis', [])
D.setdefault('price_summary', {})
D.setdefault('m12_store_volatility', [])
D.setdefault('m12_summary', {})

M = D['meta']
# Ensure numeric types for all meta fields (some may be strings from JSON)
for k in ('total_target', 'total_smart_qty', 'total_feature_qty', 'total_all_qty', 'total_revenue', 'total_profit', 'completion_rate', 'mom_change', 'daily_avg_smart', 'daily_needed', 'total_gap', 'elapsed_days', 'remaining_days', 'time_progress_pct', 'total_biz_days'):
    if k in M:
        try: M[k] = float(M[k])
        except (ValueError, TypeError): pass
# Time-progress-aware threshold for completion rate displays
_time_prog = M.get('time_progress_pct', 50)  # fallback 50% for backward compat
# Month labels
_curr_month = int(M.get('current_month', 6))
_compare_month = int(M.get('compare_month', 5))
_curr_m_label = f"{_curr_month}月" if _curr_month != 6 else "本月"
_cmp_m_label = f"{_compare_month}月" if _compare_month != 5 else "上月"
# Price list date labels (use specific dates if available)
PS = D.get('price_summary', {})
_price_curr_label = PS.get('current_price_date', _curr_m_label)
_price_cmp_label = PS.get('compare_price_date', _cmp_m_label)
fmt_n = lambda x: f"{x:,.0f}" if abs(x)>=1000 else f"{x:,.1f}"
fmt_pct = lambda x: f"{x:.1f}%"
fmt_naira = lambda x: f"₦{x/1e6:.1f}M" if abs(x)>=1e6 else f"₦{x/1e3:.0f}K"
# Date formatting: "2026-06-15" → "6月15日"
def fmt_date(date_str):
    parts = date_str.split('-')
    if len(parts) == 3:
        return f"{int(parts[1])}月{int(parts[2])}日"
    return date_str
# short date for periods: "2026-06-01 ~ 2026-06-15" → "6.1~6.15"
def fmt_period_short(date_str):
    parts = date_str.split(' ~ ')
    if len(parts) == 2:
        p1 = parts[0].split('-')
        p2 = parts[1].split('-')
        return f"{int(p1[1])}.{int(p1[2])}~{int(p2[1])}.{int(p2[2])}"
    return date_str

# Pre-compute some values
store_data = D['m1_store_target']
sorted_stores = sorted(store_data, key=lambda x: x['rate'], reverse=True)





# Generate store rows for M1
def m1_rows():
    rows = []
    for i, s in enumerate(sorted_stores):
        tc = s['tier_color']
        daily = f"{s['daily_need']:.0f}" if s['remaining']>0 else "-"
        mom_c = "#22c55e" if s['mom']>=0 else "#ef4444"
        mom_html = f"<span style='color:{mom_c}'>{s['mom']:+.1f}%</span>"
        bar_w = min(s['rate'], 100)
        rows.append(f"""<tr style="background:{tc}10">
            <td>{i+1}</td><td class="store-name">{s['short']}</td>
            <td>{s['target']:.0f}</td><td>{s['qty']:.0f}</td>
            <td><div class="progress-wrap"><div class="progress-bar" style="width:{bar_w}%;background:{tc}"></div><span>{s['rate']:.1f}%</span></div></td>
            <td>{s['remaining']:.0f}</td><td>{daily}</td>
            <td>{mom_html}</td>
            <td><span class="tier-badge" style="background:{tc}22;color:{tc};border:1px solid {tc}55">{s['tier']}</span></td>
        </tr>""")
    return '\n'.join(rows)

# Generate M2 rows
def m2_rows():
    sorted_m2 = sorted(D['m2_store_category'], key=lambda x: x['total_qty'], reverse=True)
    rows = []
    for i, s in enumerate(sorted_m2):
        rows.append(f"""<tr>
            <td>{i+1}</td><td class="store-name">{s['short']}</td>
            <td>{s['smart_qty']:.0f}</td>
            <td>{s['feature_qty']:.0f}</td><td><b>{s['total_qty']:.0f}</b></td>
            <td><div class="progress-wrap"><div class="progress-bar" style="width:{s['smart_pct']}%;background:#3b82f6"></div><span>{s['smart_pct']:.0f}%</span></div></td>
        </tr>""")
    return '\n'.join(rows)

# Generate M3 rows
def m3_rows():
    total_qty = sum(b['qty'] for b in D['m3_brands'])
    rows = []
    for i, b in enumerate(D['m3_brands']):
        pct = b['qty']/total_qty*100
        mom = b['mom_pct']
        mom_disp = "新增" if mom >= 9999 else f"{mom:+.1f}%"
        mom_c = "#22c55e" if mom >= 0 and mom < 9999 else "#ef4444" if mom < 0 else "#f59e0b"
        pr = b.get('profit_rate', 0)
        pr_c = "#22c55e" if pr >= 10 else "#f59e0b" if pr >= 5 else "#ef4444"
        avg_p = b.get('avg_price', 0)
        up = b.get('unit_profit', 0)
        rows.append(f"""<tr>
            <td>{i+1}</td><td><b>{b['品牌']}</b></td>
            <td>{b['qty']:.0f}</td><td>{pct:.1f}%</td>
            <td>{fmt_naira(b['revenue'])}</td><td>{fmt_naira(b['profit'])}</td>
            <td>{fmt_naira(avg_p)}</td><td>{fmt_naira(up)}</td>
            <td style="color:{pr_c};font-weight:600">{pr:.1f}%</td>
            <td style="color:{mom_c};font-weight:600">{mom_disp}</td>
        </tr>""")
    return '\n'.join(rows)

# Generate M5 daily summary rows
def m5_rows():
    rows = []
    for r in reversed(D['m5_company_daily']):
        pr = r.get('profit_rate', 0)
        pr_c = "#22c55e" if pr >= 10 else "#f59e0b" if pr >= 5 else "#ef4444"
        mom_c = "#22c55e" if r['smart_qty'] >= r['may_smart'] else "#ef4444"
        rows.append(f"""<tr>
            <td><b>{r['date']}</b></td>
            <td>{r['smart_qty']:.0f}</td><td>{r['feature_qty']:.0f}</td><td><b>{r['total_qty']:.0f}</b></td>
            <td>{fmt_naira(r['revenue'])}</td><td>{fmt_naira(r['profit'])}</td>
            <td style="color:{pr_c};font-weight:600">{pr:.1f}%</td>
            <td style="color:{mom_c}">{r['may_smart']:.0f}</td>
        </tr>""")
    return '\n'.join(rows)

# Generate M4 rows (last day)
def m4_rows():
    rows = []
    for r in D['m4_daily_detail']:
        met = r.get('target_met','N')
        met_c = "#22c55e" if met=="Y" else "#ef4444"
        met_icon = "✓" if met=="Y" else "✗"
        met_html = f"<span style='color:{met_c}'>{met_icon}</span>"
        change_html = ""
        dc = r.get('day_change',0)
        if dc > 0:
            change_html = f"<span style='color:#22c55e'>+{dc:.0f}</span>"
        elif dc < 0:
            change_html = f"<span style='color:#ef4444'>{dc:.0f}</span>"
        else:
            change_html = "<span style='color:#999'>0</span>"
        rows.append(f"""<tr>
            <td class="store-name">{r['short']}</td>
            <td>{r['smart_qty']:.0f}</td><td>{r['tablet_qty']:.0f}</td>
            <td>{r['feature_qty']:.0f}</td><td><b>{r['total']:.0f}</b></td>
            <td>{r.get('yesterday_smart',0):.0f}</td>
            <td>{r['daily_target']:.0f}</td><td>{met_html}</td>
            <td>{change_html}</td>
        </tr>""")
    return '\n'.join(rows)

# Generate M6 overstock rows
def m6_overstock_rows():
    rows = []
    for o in D['m6_overstock_top']:
        rows.append(f"""<tr style="background:rgba(239,68,68,0.12)">
            <td>{o['仓库'].replace('-PHONES','')}</td>
            <td>{o['品牌']}</td>
            <td class="model-name">{o['商品型号']}</td>
            <td style="color:#f87171;font-weight:700">{o['可卖数']:.0f}</td>
            <td style="color:#f87171">{fmt_naira(o['资金占用'])}</td>
            <td style="color:#475569">促销清库/跨店调拨</td>
        </tr>""")
    return '\n'.join(rows)

def m6_lowstock_rows():
    rows = []
    for l in D['m6_lowstock_top']:
        stock = l['可卖数']
        general_stock = l.get('总仓库存', 0)
        general_disp = f"{general_stock:.0f}" if general_stock > 0 else "0"
        general_color = "#22c55e" if general_stock > 0 else "#ef4444"
        td = l.get('turnover_days', None)
        if stock == 0:
            # Already out of stock
            stock_disp = "已缺货"
            stock_color = "#ef4444"
            td_disp = "已缺货"
            td_color = "#ef4444"
            suggestion = "🚨 已断货！立即从总仓调拨"
            suggestion_color = "#ef4444"
        else:
            stock_disp = f"{stock:.0f}"
            stock_color = "#fbbf24"
            if td is not None and td != 9999 and td == td:  # not None, not 9999, not NaN
                td_disp = f"{td:.0f}天"
                if td < 4:
                    td_color = "#ef4444"
                elif td < 15:
                    td_color = "#22c55e"
                elif td <= 21:
                    td_color = "#3b82f6"
                else:
                    td_color = "#f59e0b"
            else:
                td_disp = "-"
                td_color = "#475569"
            suggestion = "紧急从总仓调拨"
            suggestion_color = "#475569"
        rows.append(f"""<tr style="background:rgba(245,158,11,0.12)">
            <td>{l['仓库'].replace('-PHONES','')}</td>
            <td>{l['品牌']}</td>
            <td class="model-name">{l['商品型号']}</td>
            <td style="color:{stock_color};font-weight:700">{stock_disp}</td>
            <td style="color:{td_color};font-weight:700">{td_disp}</td>
            <td style="color:{general_color};font-weight:700">{general_disp}</td>
            <td style="color:#475569">{l['近1月销量']:.0f}</td>
            <td style="color:{suggestion_color};font-weight:600">{suggestion}</td>
        </tr>""")
    return '\n'.join(rows)

def m6_general_rows():
    rows = []
    for g in D['m6_general_dead']:
        rows.append(f"""<tr style="background:rgba(239,68,68,0.12)">
            <td>{g['品牌']}</td>
            <td class="model-name">{g['商品型号']}</td>
            <td style="color:#f87171;font-weight:700">{g['可卖数']:.0f}</td>
            <td style="color:#f87171">{fmt_naira(g['资金占用'])}</td>
            <td style="color:#475569">停止采购/清库活动</td>
        </tr>""")
    return '\n'.join(rows)

def m6_turnover_rows():
    """Generate store turnover ranking table rows. Uses short store names.
    Formula: 周转天数 = 门店总可卖数 / 门店日均销量"""
    stores = D.get('m6_inv_store', [])
    short_names = D.get('m6_store_short_names', {})
    # Sort by turnover_days (ascending, best first; put 9999 at end)
    sorted_stores = sorted(stores, key=lambda x: x.get('turnover_days', 9999))
    rows = []
    for i, s in enumerate(sorted_stores, 1):
        td = s.get('turnover_days', 9999)
        store_name = s['inv_store']
        short_name = short_names.get(store_name, store_name)
        if td >= 9999:
            rating = "全死库"
            rating_color = "#ef4444"
            suggestion = "紧急：无一动销，排查门店运营状态"
        elif td < 4:
            rating = "🟥 缺货预警"
            rating_color = "#ef4444"
            suggestion = "库存仅够售卖<4天，紧急补货！"
        elif td < 15:
            rating = "优秀"
            rating_color = "#22c55e"
            suggestion = "周转健康，保持当前备货节奏"
        elif td <= 21:
            rating = "正常"
            rating_color = "#3b82f6"
            suggestion = "周转正常，关注慢动销型号"
        elif td <= 60:
            rating = "🟠 积压风险"
            rating_color = "#f59e0b"
            suggestion = "周转偏慢，启动促销/跨店调拨"
        else:
            rating = "严重滞销"
            rating_color = "#dc2626"
            suggestion = "严重积压，立即启动清库活动"
        td_disp = "∞" if td >= 9999 else f"{td:.0f}"
        daily_avg = s.get('daily_avg_sales', 0)
        daily_disp = f"{daily_avg:.1f}" if daily_avg > 0 else "0"
        rows.append(f"""<tr style="background:{rating_color}10">
            <td>{i}</td>
            <td class="store-name" title="{store_name}">{short_name}</td>
            <td>{s.get('total_stock', 0):.0f}</td>
            <td>{daily_disp}</td>
            <td style="color:{rating_color};font-weight:700">{td_disp} 天</td>
            <td style="color:{rating_color};font-weight:600">{rating}</td>
            <td style="color:#475569;font-size:11px">{suggestion}</td>
        </tr>""")
    return '\n'.join(rows)

def m6_turnover_kpi():
    """Generate KPI cards for turnover summary."""
    ts = D.get('m6_turnover_summary', {})
    short_names = D.get('m6_store_short_names', {})
    avg_days = ts.get('avg_days', '-')
    warning = ts.get('warning', 0)
    excellent = ts.get('excellent_old', ts.get('excellent', 0))
    good = ts.get('good', 0)
    risk = ts.get('risk', 0)
    critical = ts.get('critical', 0)
    all_dead = ts.get('all_dead_count', 0)
    best_store = ts.get('best_store', '-')
    best_days = ts.get('best_days', 0)
    worst_store = ts.get('worst_store', '-')
    worst_days = ts.get('worst_days', 0)
    return f"""<div class="kpi-row" style="margin-bottom:12px">
            <div class="kpi-card">
                <div class="kpi-label">平均周转天数</div>
                <div class="kpi-value">{avg_days}<small>天</small></div>
                <div class="kpi-sub">全公司加权均值</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">🔴 缺货预警（&lt;4天）</div>
                <div class="kpi-value" style="color:#ef4444">{warning}<small>家</small></div>
                <div class="kpi-sub">即将断货，紧急补货</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">健康门店（4-21天）</div>
                <div class="kpi-value" style="color:#22c55e">{excellent + good}<small>家</small></div>
                <div class="kpi-sub">周转优秀{excellent}家 + 正常{good}家</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">🟠 积压风险（22-60天）</div>
                <div class="kpi-value" style="color:#f59e0b">{risk}<small>家</small></div>
                <div class="kpi-sub">需促销/跨店调拨</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">严重滞销（&gt;60天）</div>
                <div class="kpi-value" style="color:#dc2626">{critical}<small>家</small></div>
                <div class="kpi-sub">含{all_dead}家全死库门店</div>
            </div>
        </div>
        <div style="display:flex;gap:16px;margin-bottom:12px;font-size:11px;color:var(--text2)">
            <span>🏆 最快周转：{short_names.get(best_store, best_store)}（{best_days}天）</span>
            <span>⚠️ 最慢周转：{short_names.get(worst_store, worst_store)}（{worst_days}天）</span>
            <span>📊 计算范围：手机+平板，不含总仓</span>
        </div>"""


def m6_brand_turnover_rows():
    """Generate brand-level turnover ranking table rows.
    Formula: 品牌周转 = 品牌门店总可卖数(不含总仓) / 品牌日均销量"""
    brands = D.get('m6_brand_turnover', [])
    rows = []
    for i, b in enumerate(brands, 1):
        td = b.get('turnover_days', 9999)
        if td >= 9999:
            rating = "全死库"
            rating_color = "#ef4444"
        elif td < 15:
            rating = "优秀"
            rating_color = "#22c55e"
        elif td < 30:
            rating = "正常"
            rating_color = "#3b82f6"
        elif td < 60:
            rating = "偏慢"
            rating_color = "#f59e0b"
        else:
            rating = "严重滞销"
            rating_color = "#ef4444"
        td_disp = "∞" if td >= 9999 else f"{td:.0f}"
        store_s = b.get('store_sellable', 0)
        gen_s = b.get('general_sellable', 0)
        da = b.get('brand_daily_avg', 0)
        rows.append(f"""<tr style="background:{rating_color}10">
            <td>{i}</td>
            <td class="brand-name">{b['品牌']}</td>
            <td>{store_s:.0f}</td>
            <td style="color:#f59e0b">{gen_s:.0f}</td>
            <td>{da:.1f}</td>
            <td style="color:{rating_color};font-weight:700">{td_disp} 天</td>
            <td style="color:{rating_color};font-weight:600">{rating}</td>
        </tr>""")
    return '\n'.join(rows)

def m6_model_turnover_rows():
    """Generate model-level turnover ranking table rows.
    Formula: 型号周转 = 所有门店仓总可卖数 / 型号日均销量，按日销降序"""
    models = D.get('m6_model_turnover', [])[:50]
    rows = []
    for i, m in enumerate(models, 1):
        td = m.get('turnover_days', 9999)
        if td >= 9999:
            rating = "全死库"
            rating_color = "#ef4444"
        elif td < 15:
            rating = "优秀"
            rating_color = "#22c55e"
        elif td < 30:
            rating = "正常"
            rating_color = "#3b82f6"
        elif td < 60:
            rating = "偏慢"
            rating_color = "#f59e0b"
        else:
            rating = "严重滞销"
            rating_color = "#ef4444"
        td_disp = "∞" if td >= 9999 else f"{td:.0f}"
        stock = m.get('total_sellable', 0)
        transit = m.get('total_transit', 0)
        brand = m['品牌']
        daily_sales = m.get('daily_avg_sales', 0)
        rows.append(f"""<tr style="background:{rating_color}10" data-brand="{brand}">
            <td>{i}</td>
            <td>{brand}</td>
            <td class="model-name">{m['商品型号']}</td>
            <td style="font-weight:700">{stock:.0f}</td>
            <td style="color:#f59e0b">{transit:.0f}</td>
            <td style="font-weight:600">{daily_sales:.1f}</td>
            <td style="color:{rating_color};font-weight:700">{td_disp} 天</td>
            <td style="color:{rating_color};font-weight:600">{rating}</td>
            <td style="color:#475569;font-size:11px">{fmt_naira(m.get('资金占用', 0))}</td>
        </tr>""")
    return '\n'.join(rows)

def m6_store_model_js():
    """Generate JavaScript data and UI for single-store model turnover drill-down.
    Enhanced: category/brand columns, sales-volume sorting, 可卖数+在途, short store names."""
    data = D.get('m6_store_model_turnover', [])
    short_names = D.get('m6_store_short_names', {})
    all_brands = D.get('m6_all_brands', [])
    
    # Build JS store data: {short_name: [models sorted by sales desc]}
    js_data = {}
    store_options = []
    for r in data:
        store = r.get('inv_store', '')
        short = short_names.get(store, store)
        if short not in js_data:
            js_data[short] = {'dept': store, 'models': []}
        cat_raw = r.get('二级分类名称', '')
        cat_disp = '手机' if 'SMART' in str(cat_raw) else ('平板' if 'TABLET' in str(cat_raw) else str(cat_raw))
        js_data[short]['models'].append({
            'cat': cat_disp,
            'brand': r.get('品牌', ''),
            'model': r.get('商品型号', ''),
            'sellable': int(r.get('可卖数', 0)),
            'transit': int(r.get('在途', 0)),
            'turnover': int(r.get('turnover_days', 9999)),
            'sales': int(r.get('sales_qty', 0)),
            'fund': int(r.get('资金占用', 0)),
            'general_stock': int(r.get('总仓库存', 0)),
        })
    # Sort store options by short name
    store_options = sorted(js_data.keys())
    
    return f"""<script>
    const storeModelData = {json.dumps(js_data, ensure_ascii=False)};
    const storeModelBrands = {json.dumps(all_brands, ensure_ascii=False)};
    const storeOptions = {json.dumps(store_options, ensure_ascii=False)};
    const m11ModelTrends = {json.dumps(D.get('m11_model_trends', []), ensure_ascii=False)};
    const m11Brands = {json.dumps(sorted(set(t['brand'] for t in D.get('m11_model_trends', []) if t.get('brand'))), ensure_ascii=False)};
    const m11Tiers = {json.dumps(sorted(set(t['price_tier'] for t in D.get('m11_model_trends', []) if t.get('price_tier'))), ensure_ascii=False)};
    
    function initStoreCombo() {{
        const list = document.getElementById('store-combo-list');
        storeOptions.forEach(s => {{
            const div = document.createElement('div');
            div.style.cssText = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;font-size:12px;border-bottom:1px solid #1e293b';
            div.textContent = s;
            div.onmouseenter = function() {{ this.style.background = '#334155'; }};
            div.onmouseleave = function() {{ this.style.background = ''; }};
            div.onclick = function(e) {{ e.stopPropagation(); selectStoreCombo(s); }};
            div.setAttribute('data-store', s);
            list.appendChild(div);
        }});
    }}
    function toggleStoreCombo() {{
        const dd = document.getElementById('store-combo-dropdown');
        const input = document.getElementById('store-combo-search');
        if (dd.style.display === 'block') {{
            dd.style.display = 'none';
        }} else {{
            dd.style.display = 'block';
            input.value = '';
            filterStoreCombo();
            setTimeout(function(){{ input.focus(); }}, 50);
        }}
    }}
    function filterStoreCombo() {{
        const keyword = document.getElementById('store-combo-search').value.toLowerCase().trim();
        const items = document.querySelectorAll('#store-combo-list div[data-store]');
        let visible = 0;
        items.forEach(d => {{
            const store = d.getAttribute('data-store') || '';
            if (store.toLowerCase().includes(keyword)) {{
                d.style.display = '';
                visible++;
            }} else {{
                d.style.display = 'none';
            }}
        }});
        let noMatch = document.getElementById('combo-no-match');
        if (visible === 0) {{
            if (!noMatch) {{
                noMatch = document.createElement('div');
                noMatch.id = 'combo-no-match';
                noMatch.style.cssText = 'padding:8px 12px;color:#94a3b8;font-size:12px';
                noMatch.textContent = '未找到匹配门店';
                document.getElementById('store-combo-list').appendChild(noMatch);
            }}
            noMatch.style.display = '';
        }} else {{
            if (noMatch) noMatch.style.display = 'none';
        }}
    }}
    function selectStoreCombo(store) {{
        document.getElementById('store-combo-btn').innerHTML = '<span style="color:#22c55e">'+store+'</span> ▾';
        document.getElementById('store-select').value = store;
        document.getElementById('store-combo-dropdown').style.display = 'none';
        filterStoreModels();
    }}
    function handleComboKey(e) {{
        const dd = document.getElementById('store-combo-dropdown');
        if (dd.style.display !== 'block') return;
        const items = Array.from(document.querySelectorAll('#store-combo-list div[data-store]')).filter(d => d.style.display !== 'none');
        if (e.key === 'Escape') {{
            dd.style.display = 'none';
        }} else if (e.key === 'Enter') {{
            e.preventDefault();
            const active = dd.querySelector('.combo-active');
            if (active) {{
                selectStoreCombo(active.getAttribute('data-store'));
            }} else if (items.length > 0) {{
                selectStoreCombo(items[0].getAttribute('data-store'));
            }}
        }} else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {{
            e.preventDefault();
            const active = dd.querySelector('.combo-active');
            let idx = active ? items.indexOf(active) : -1;
            if (e.key === 'ArrowDown') idx = (idx + 1) % items.length;
            else idx = (idx - 1 + items.length) % items.length;
            items.forEach(d => {{ d.style.background = ''; d.classList.remove('combo-active'); }});
            if (items[idx]) {{
                items[idx].style.background = '#334155';
                items[idx].classList.add('combo-active');
                items[idx].scrollIntoView({{block:'nearest'}});
            }}
        }}
    }}
    // Hide combo dropdown when clicking outside
    document.addEventListener('click', function(e) {{
        const combo = document.getElementById('store-combo-dropdown');
        const btn = document.getElementById('store-combo-btn');
        if (combo && btn && !btn.contains(e.target) && !combo.contains(e.target)) {{
            combo.style.display = 'none';
        }}
    }});
    function populateStoreModelBrandFilter() {{
        const sel = document.getElementById('sm-brand-filter');
        sel.innerHTML = '<option value="">全部品牌</option>';
        storeModelBrands.forEach(b => {{
            sel.innerHTML += '<option value="'+b+'">'+b+'</option>';
        }});
    }}
    function filterStoreModels() {{
        const store = document.getElementById('store-select').value;
        const brand = document.getElementById('sm-brand-filter').value;
        const cat = document.getElementById('sm-cat-filter').value;
        const tbody = document.getElementById('store-model-tbody');
        tbody.innerHTML = '';
        if (!store || !storeModelData[store]) return;
        let models = storeModelData[store].models;
        // Apply filters
        if (brand) models = models.filter(m => m.brand === brand);
        if (cat) models = models.filter(m => m.cat === cat);
        models.forEach((r, i) => {{
            const td = r.turnover;
            const stock = r.sellable;
            let rating = '优秀', color = '#22c55e', suggestion = '周转健康，保持备货', warnIcon = '';
            if (stock === 0 && r.sales > 0) {{
                rating = '🚨 已断货'; color = '#ef4444'; suggestion = '🚨 已断货！立即从总仓调拨'; warnIcon = '🚨 ';
            }} else if (td >= 9999) {{
                rating = '全死库'; color = '#ef4444'; suggestion = '无一动销，排查型号适配性';
            }} else if (td < 4) {{
                rating = '🔴 缺货预警'; color = '#ef4444'; suggestion = '库存仅够<4天，紧急补货！'; warnIcon = '🚨 ';
            }} else if (td <= 14) {{
                rating = '优秀'; color = '#22c55e'; suggestion = '周转健康，保持备货节奏';
            }} else if (td <= 21) {{
                rating = '正常'; color = '#3b82f6'; suggestion = '周转正常，关注动销节奏';
            }} else if (td <= 60) {{
                rating = '🟠 积压风险'; color = '#f59e0b'; suggestion = '周转偏慢，启动促销/调拨';
            }} else {{
                rating = '严重滞销'; color = '#dc2626'; suggestion = '严重积压，立即清库';
            }}
            const td_disp = td >= 9999 ? '∞' : String(td);
            const sold = r.sales > 0 ? String(r.sales) : '0';
            tbody.innerHTML += '<tr style="background:'+color+'10">'+
                '<td>'+warnIcon+(i+1)+'</td>'+
                '<td>'+r.cat+'</td>'+
                '<td>'+r.brand+'</td>'+
                '<td class=\"model-name\">'+r.model+'</td>'+
                '<td style=\"font-weight:700;'+(stock===0?'color:#ef4444':'')+'">'+String(stock)+'</td>'+
                '<td style=\"color:#f59e0b\">'+String(r.transit)+'</td>'+
                '<td>'+sold+'</td>'+
                '<td style=\"color:'+color+';font-weight:700\">'+td_disp+' 天</td>'+
                '<td style=\"font-weight:600;'+(r.general_stock===0?'color:#475569':'color:#22c55e')+'\">'+(r.general_stock||0)+'</td>'+
                '<td style=\"color:'+color+';font-weight:600\">'+rating+'</td>'+
                '<td style=\"color:#475569;font-size:11px\">'+suggestion+'</td>'+
                '<td style=\"color:#475569;font-size:11px\">₦'+(r.fund||0).toLocaleString()+'</td>'+
            '</tr>';
        }});
    }}
    function filterModelTurnover() {{
        const brand = document.getElementById('model-brand-filter').value;
        const rows = document.querySelectorAll('#inv-model tbody tr');
        rows.forEach(row => {{
            const brandCell = row.cells[1];
            if (!brand || (brandCell && brandCell.textContent === brand)) {{
                row.style.display = '';
            }} else {{
                row.style.display = 'none';
            }}
        }});
    }}
    function initModelBrandFilter() {{
        const sel = document.getElementById('model-brand-filter');
        if (!sel) return;
        sel.innerHTML = '<option value="">全部品牌</option>';
        storeModelBrands.forEach(b => {{
            sel.innerHTML += '<option value="'+b+'">'+b+'</option>';
        }});
    }}
    document.addEventListener('DOMContentLoaded', function() {{
        initStoreCombo();
        populateStoreModelBrandFilter();
        initModelBrandFilter();
    }});
    </script>"""


def m8_rows():
    rows = []
    for s in sorted(D['m8_lagging'], key=lambda x: x['rate']):
        tc = s['tier_color']
        catchup = f"需日均{s['daily_need']:.0f}台" if s['remaining']>0 else "-"
        mom_c = "#22c55e" if s['mom']>=0 else "#ef4444"
        rows.append(f"""<tr style="background:{tc}10">
            <td class="store-name">{s['short']}</td>
            <td>{s['target']:.0f}</td><td>{s['qty']:.0f}</td>
            <td style="color:{tc};font-weight:700">{s['rate']:.1f}%</td>
            <td style="color:#ef4444">{s['remaining']:.0f}</td>
            <td>{catchup}</td>
            <td style="color:{mom_c}">{s['mom']:+.1f}%</td>
        </tr>""")
    return '\n'.join(rows)

# M12 Store Volatility
def m12_sparkline(series, color='#3b82f6', w=80, h=24):
    """Generate an SVG sparkline from a numeric series."""
    if not series or len(series) < 2:
        return '<svg width="{w}" height="{h}"></svg>'.format(w=w, h=h)
    vals = [float(v) for v in series]
    mx, mn = max(vals), min(vals)
    rng = mx - mn if mx != mn else 1
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (n - 1)
        y = h - (v - mn) / rng * (h - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = ' '.join(pts)
    # Last point dot
    lx = (n-1) * w / (n - 1)
    ly = h - (vals[-1] - mn) / rng * (h - 4) - 2
    return f'''<svg width="{w}" height="{h}" style="vertical-align:middle">
        <polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/>
        <circle cx="{lx:.1f}" cy="{ly:.1f}" r="1.8" fill="{color}"/>
    </svg>'''

def m12_rows():
    rows = []
    rating_order = {'稳定': 1, '正常': 2, '波动较大': 3, '剧烈波动': 4, '停业': 5}
    trend_order = {'上升': 1, '平稳': 2, '下降': 3}
    for i, s in enumerate(D.get('m12_store_volatility', [])):
        rc = s.get('rating_color', '#666')
        tc = s.get('trend_color', '#666')
        spark = m12_sparkline(s.get('daily_series', []), rc)
        cv_c = '#22c55e' if s['cv'] <= 25 else ('#3b82f6' if s['cv'] <= 40 else ('#f59e0b' if s['cv'] <= 60 else '#ef4444'))
        cv_chg = s.get('cv_change', 0)
        cv_chg_str = f"<span style='color:{'#ef4444' if cv_chg > 0 else '#22c55e'}'>{cv_chg:+.1f}pp</span>" if cv_chg != 0 else "<span style='color:#6b7280'>—</span>"
        zero_badge = f"<span style='color:#ef4444;font-weight:600'>{s['zero_days']}天</span>" if s['zero_days'] > 0 else "<span style='color:#6b7280'>0</span>"
        ro = rating_order.get(s['rating'], 0)
        to = trend_order.get(s['trend_dir'], 0)
        rows.append(f"""<tr data-idx="{i}" style="cursor:pointer" onclick="document.getElementById('m12_store_select').value='{i}';m12ShowDetail('{i}')" onmouseenter="this.style.background='var(--surface2)'" onmouseleave="this.style.background=''">
            <td data-v="{i+1}">{i+1}</td>
            <td class="store-name" data-v="{s['short']}" style="color:#3b82f6;text-decoration:underline">{s['short']}</td>
            <td data-v="{s['mean']:.1f}">{s['mean']:.1f}</td>
            <td data-v="{s['cv']:.1f}" style="color:{cv_c};font-weight:600">{s['cv']:.1f}%</td>
            <td data-v="{s['std']:.1f}">{s['std']:.1f}</td>
            <td data-v="{s['max']:.0f}">{s['max']:.0f}</td>
            <td data-v="{s['min']:.0f}">{s['min']:.0f}</td>
            <td data-v="{s['zero_days']}">{zero_badge}</td>
            <td data-v="{to}" style="color:{tc};font-weight:600">{s['trend_dir']}</td>
            <td data-v="{cv_chg:.1f}">{cv_chg_str}</td>
            <td data-v="{ro}"><span style="background:{rc}18;color:{rc};border:1px solid {rc}44;padding:1px 6px;border-radius:3px;font-size:11px">{s['rating']}</span></td>
            <td>{spark}</td>
        </tr>""")
    return '\n'.join(rows)

def m12_kpi_cards():
    s = D.get('m12_summary', {})
    rd = s.get('rating_dist', {})
    cards = [
        ('活跃门店', f"{s.get('active_stores', 0)}", f"/ {s.get('total_stores', 0)} 家", '#3b82f6'),
        ('平均CV', f"{s.get('avg_cv', 0):.1f}%", '变异系数均值', '#8b5cf6'),
        ('最稳定', s.get('most_stable', '-'), f"CV {s.get('most_stable_cv', 0):.1f}%", '#22c55e'),
        ('最波动', s.get('most_volatile', '-'), f"CV {s.get('most_volatile_cv', 0):.1f}%", '#ef4444'),
        ('零销量天数门店', f"{s.get('zero_day_count', 0)}", '家存在零销日', '#f97316'),
        ('趋势下降门店', f"{s.get('declining_count', 0)}", '家日销下滑', '#dc2626'),
    ]
    parts = []
    for label, val, sub, color in cards:
        parts.append(f"""<div class="kpi-card" style="flex:1;min-width:140px">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{val}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""")
    # Rating distribution bar
    total_active = s.get('active_stores', 1) or 1
    bar_parts = []
    bar_colors = {'稳定': '#22c55e', '正常': '#3b82f6', '波动较大': '#f59e0b', '剧烈波动': '#ef4444', '停业': '#6b7280'}
    for r in ['稳定', '正常', '波动较大', '剧烈波动', '停业']:
        cnt = rd.get(r, 0)
        if cnt > 0:
            pct = cnt / total_active * 100
            bar_parts.append(f'<div style="flex:{cnt};background:{bar_colors[r]};min-width:20px" title="{r}: {cnt}家 ({pct:.0f}%)">{cnt}</div>')
    bar_html = ''.join(bar_parts) if bar_parts else '<div style="color:#6b7280">无数据</div>'
    parts.append(f"""<div style="flex-basis:100%;margin-top:4px">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">波动评级分布</div>
        <div style="display:flex;height:22px;border-radius:4px;overflow:hidden;font-size:10px;color:#fff;font-weight:600;line-height:22px;text-align:center">{bar_html}</div>
    </div>""")
    return '\n'.join(parts)

def m9_rows():
    type_colors = {
        '未达日目标': '#f59e0b', '月度严重滞后': '#ef4444', '缺货预警': '#ef4444',
        '库存积压': '#f97316', '品牌销量下滑': '#f97316', '当日零销量': '#dc2626'
    }
    rows = []
    for iss in D['m9_issues']:
        c = type_colors.get(iss['type'], '#666')
        rows.append(f"""<tr>
            <td><span class="issue-type" style="background:{c}18;color:{c};border:1px solid {c}44">{iss['type']}</span></td>
            <td class="store-name">{iss['store']}</td>
            <td>{iss['detail']}</td>
            <td style="color:#3b82f6">{iss['action']}</td>
        </tr>""")
    return '\n'.join(rows)

# M7 Staff Efficiency
def m7_store_rows():
    m7 = D.get('m7_staff', {})
    eff = m7.get('store_efficiency', [])
    co_avg = m7.get('co_avg_smart', 0)
    rows = []
    for i, s in enumerate(eff):
        eff_c = s.get('eff_color', '#3b82f6')
        # Gap vs company average
        gap = s['avg_smart_per_person'] - co_avg
        gap_str = f"+{gap:.1f}" if gap >= 0 else f"{gap:.1f}"
        gap_c = "#22c55e" if gap >= 0 else "#ef4444"
        rows.append(f"""<tr>
            <td>{i+1}</td><td class="store-name">{s['short']}</td>
            <td>{s['staff_count']}</td>
            <td style="font-weight:700;color:{gap_c}">{s['avg_smart_per_person']:.1f}</td>
            <td>{s['avg_total_per_person']:.1f}</td>
            <td style="color:#22c55e">₦{s['avg_profit_per_person']/1e3:.0f}K</td>
            <td><span class="tier-badge" style="background:{eff_c}22;color:{eff_c};border:1px solid {eff_c}55">{s['eff_tier']}</span></td>
            <td class="store-name" style="font-size:10px">{s.get('top_sp_name','-')} ({s.get('top_sp_qty',0):.0f}台)</td>
        </tr>""")
    return '\n'.join(rows)

def m7_top_sp_rows():
    m7 = D.get('m7_staff', {})
    top = m7.get('top_salespersons', [])
    rows = []
    for i, s in enumerate(top[:15]):
        pr_c = "#22c55e" if s['profit_rate'] >= 10 else "#f59e0b" if s['profit_rate'] >= 5 else "#ef4444"
        rows.append(f"""<tr>
            <td>{i+1}</td><td class="store-name">{s['营业员']}</td>
            <td style="font-weight:700">{s['smart_qty']:.0f}</td>
            <td>{fmt_naira(s['revenue'])}</td>
            <td style="color:{pr_c};font-weight:600">{s['profit_rate']:.1f}%</td>
        </tr>""")
    return '\n'.join(rows)

def m7_bottom_sp_rows():
    m7 = D.get('m7_staff', {})
    bottom = m7.get('bottom_salespersons', [])
    rows = []
    for i, s in enumerate(bottom):
        pr_c = "#22c55e" if s['profit_rate'] >= 10 else "#f59e0b" if s['profit_rate'] >= 5 else "#ef4444"
        rows.append(f"""<tr>
            <td>{i+1}</td><td class="store-name">{s['营业员']}</td>
            <td style="color:#ef4444;font-weight:700">{s['smart_qty']:.0f}</td>
            <td>{fmt_naira(s['revenue'])}</td>
            <td style="color:{pr_c};font-weight:600">{s['profit_rate']:.1f}%</td>
        </tr>""")
    return '\n'.join(rows)

# Tier summary cards HTML
def tier_cards():
    html = ''
    for t in D['m1_tier_summary']:
        html += f"""<div class="tier-card" style="border-left:4px solid {t['color']}">
            <div class="tier-name" style="color:{t['color']}">{t['tier']} ({t['count']}家)</div>
            <div class="tier-rate">{t['avg_rate']:.1f}%</div>
            <div class="tier-detail">销量{t['total_qty']:,} / 任务{t['total_target']:,}</div>
            <div class="tier-stores">{', '.join(t['stores'][:5])}{'...' if len(t['stores'])>5 else ''}</div>
        </div>"""
    return html

# Daily chart data
daily_labels = json.dumps([r['d'] for r in D['daily_chart']])
daily_sq = json.dumps([r['sq'] for r in D['daily_chart']])
daily_fq = json.dumps([r['fq'] for r in D['daily_chart']])
daily_rev = json.dumps([r['rev']/1e6 for r in D['daily_chart']])
daily_prof = json.dumps([r['prof']/1e6 for r in D['daily_chart']])
daily_may = json.dumps([r['may_sq'] for r in D['daily_chart']])

# Brand chart data - ALL brands
brand_labels = json.dumps([b['品牌'] for b in D['m3_brands']])
brand_qty = json.dumps([b['qty'] for b in D['m3_brands']])
brand_rev = json.dumps([round(b['revenue']/1e6,1) for b in D['m3_brands']])
brand_pr = json.dumps([b.get('profit_rate', 0) for b in D['m3_brands']])
brand_may_qty = json.dumps([b['may_qty'] for b in D['m3_brands']])
brand_profit = json.dumps([round(b['profit']/1e6,1) for b in D['m3_brands']])
brand_colors = json.dumps(['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#06b6d4','#a3e635'])

# M5 chart data
m5_labels = json.dumps([r['date'] for r in D['m5_company_daily']])
m5_sq = json.dumps([r['smart_qty'] for r in D['m5_company_daily']])
m5_fq = json.dumps([r['feature_qty'] for r in D['m5_company_daily']])
m5_rev = json.dumps([round(r['revenue']/1e6,1) for r in D['m5_company_daily']])

# M2 category pie data - 3 separate categories from JSON
cat_pie_labels = json.dumps([c['name'] for c in D['cat_structure']])
cat_pie_data = json.dumps([c['qty'] for c in D['cat_structure']])
cat_pie_colors = json.dumps([c['color'] for c in D['cat_structure']])

# For alert text and charts
cat_total = sum(c['qty'] for c in D['cat_structure'])
cat_rev_labels = json.dumps([c['name'] for c in D['cat_structure']])
cat_rev_data = json.dumps([round(c['revenue']/1e6, 1) for c in D['cat_structure']])
cat_rev_colors = json.dumps([c['color'] for c in D['cat_structure']])
# Pre-build category revenue bar chart data
cat_rev_bar_js = '{labels:' + cat_rev_labels + ',datasets:[{label:\'营收(百万₦)\',data:' + cat_rev_data + ',backgroundColor:' + cat_rev_colors + '}]},'
# Build category analysis text dynamically
cat_items_text = '，'.join([f"{c['name']}{c['qty']:.0f}台({c['qty']/cat_total*100:.1f}%)" for c in D['cat_structure'] if c['qty'] > 0])

# Pre-build chart JS configs that have tricky brace patterns (avoid f-string {var}} issue)
report_brand_data = '{labels:' + brand_labels + ',datasets:[{label:\'销量\',data:' + brand_qty + ',backgroundColor:' + brand_colors + ',yAxisID:\'y\'},{label:\'毛利率%\',data:' + brand_pr + ',type:\'line\',borderColor:\'#a78bfa\',backgroundColor:\'#a78bfa33\',yAxisID:\'y1\',pointRadius:3,borderWidth:2,tension:0.3}]},'
cat_pie_data_js = '{labels:' + cat_pie_labels + ',datasets:[{data:' + cat_pie_data + ',backgroundColor:' + cat_pie_colors + '}]},'
brand_qty_data_js = '{labels:' + brand_labels + ',datasets:[{label:\'本月销量\',data:' + brand_qty + ',backgroundColor:' + brand_colors + '},{label:\'上月销量\',data:' + brand_may_qty + ',backgroundColor:\'#64748b\'}]}'
brand_rev_data_js = '{labels:' + brand_labels + ',datasets:[{label:\'营收(百万₦)\',data:' + brand_rev + ',backgroundColor:\'#22c55e88\',borderColor:\'#22c55e\',borderWidth:1},{label:\'毛利(百万₦)\',data:' + brand_profit + ',backgroundColor:\'#3b82f688\',borderColor:\'#3b82f6\',borderWidth:1}]},'

# Company M5 summary
m5_total = D['m5_company_daily'][-1] if D['m5_company_daily'] else {}
last7 = D['m5_company_daily'][-7:] if len(D['m5_company_daily'])>=7 else D['m5_company_daily']
avg7_smart = sum(r['smart_qty'] for r in last7)/len(last7) if last7 else 0

# Generate trend analysis text
trend_days = D['daily_chart']
if len(trend_days) >= 3:
    last3 = trend_days[-3:]
    trend_dir = "上升" if last3[-1]['sq'] > last3[0]['sq'] else "下降" if last3[-1]['sq'] < last3[0]['sq'] else "持平"
    peak_day = max(trend_days, key=lambda x: x['sq'])
    low_day = min(trend_days, key=lambda x: x['sq'])
    trend_text = f"近3日智能机销量呈{trend_dir}趋势。月内峰值{peak_day['d']}（{peak_day['sq']:.0f}台），最低{low_day['d']}（{low_day['sq']:.0f}台）。7日日均智能机{avg7_smart:.0f}台，距完成月度任务还需日均{M['daily_needed']:.0f}台，缺口{M['total_gap']:.0f}台。"
else:
    trend_text = "数据不足，暂无趋势分析。"

# Store contribution
total_company_smart = M['total_smart_qty']
top5_stores = sorted(D['m2_store_category'], key=lambda x: x['smart_qty'], reverse=True)[:5]
top5_pct = sum(s['smart_qty'] for s in top5_stores)/total_company_smart*100
tail10 = sorted(D['m2_store_category'], key=lambda x: x['smart_qty'])[:10]
tail10_pct = sum(s['smart_qty'] for s in tail10)/total_company_smart*100

# M8 recovery plan text
lagging_count = len([s for s in D['m8_lagging'] if s['tier']=='严重滞后'])
warning_count = len([s for s in D['m8_lagging'] if s['tier']=='预警'])
recovery_text = f"""全公司智能机总缺口 <b style="color:#ef4444">{M['total_gap']:.0f}台</b>，剩余{M['remaining_days']}天需日均完成 <b>{M['daily_needed']:.0f}台</b>（当前日均{M['daily_avg_smart']:.0f}台）。
其中严重滞后门店{lagging_count}家、预警门店{warning_count}家。建议：(1) 加大TECNO/INFINIX爆款主推力度，头部门店挑大梁；(2) 滞销机型捆绑促销拉动客单；(3) 严重滞后门店安排区域经理驻店帮扶。"""

# Report summary
mom_color = "#ef4444" if M['mom_change']<0 else "#22c55e"
overstock_fund = sum(o['资金占用'] for o in D['m6_overstock_top'])
report_summary = f"""截至{fmt_date(M['report_date'])}，全公司智能机完成率 <b>{M['completion_rate']:.1f}%</b>（{M['total_smart_qty']:.0f}台/{M['total_target']:.0f}台），剩余{M['remaining_days']}天缺口{M['total_gap']:.0f}台，日均需达{M['daily_needed']:.0f}台（当前日均{M['daily_avg_smart']:.0f}台）。
整体环比上月同期 <b style="color:{mom_color}">{M['mom_change']:+.1f}%</b>。
<b>严重滞后{lagging_count}家</b>门店需重点关注，库存积压资金约{fmt_naira(overstock_fund)}需清库。"""

# ===== DATA REPORT for WeChat sharing =====
# Today's data (last day in m5)
today = D['m5_company_daily'][-1]
yesterday = D['m5_company_daily'][-2] if len(D['m5_company_daily']) >= 2 else today

# Recent 7-day trend
recent7 = D['m5_company_daily'][-7:] if len(D['m5_company_daily']) >= 7 else D['m5_company_daily']
trend_desc = "数据不足，暂无法判断"
first3 = 0
last3 = 0
if len(recent7) >= 3:
    first3 = sum(r['smart_qty'] for r in recent7[:3])
    last3 = sum(r['smart_qty'] for r in recent7[-3:])
    if last3 > first3 * 1.05:
        trend_desc = "📈 上行趋势"
    elif last3 < first3 * 0.95:
        trend_desc = "📉 下行趋势"
    else:
        trend_desc = "➡️ 平稳运行"

# Top/Bottom brands
brands_sorted = sorted(D['m3_brands'], key=lambda b: b['qty'], reverse=True)
top3_brands = brands_sorted[:3]
bottom3_brands = brands_sorted[-3:]

# Top/Bottom stores
stores_ranked = sorted(D['m1_store_target'], key=lambda s: s['rate'], reverse=True)
top3_stores = stores_ranked[:3]
bottom3_stores = stores_ranked[-3:]

# Brand profit leaders
brands_by_pr = sorted(D['m3_brands'], key=lambda b: b.get('profit_rate',0), reverse=True)
best_pr_brand = brands_by_pr[0]
worst_pr_brand = brands_by_pr[-1]

# Daily goal: today's smart vs daily target
daily_target = M['total_target'] / (M['elapsed_days'] + M['remaining_days'])  # Use total biz days
today_vs_target = today['smart_qty'] / daily_target * 100 if daily_target > 0 else 0

data_report = f"""<div class="report-block">
    <div class="report-title">📊 总览</div>
    <div class="report-text">截至{fmt_date(M['report_date'])}，智能机累计销量 <b>{M['total_smart_qty']:,.0f}台</b>，完成率 <b style="color:{'#22c55e' if M['completion_rate']>=_time_prog else '#ef4444'}">{M['completion_rate']:.1f}%</b>，剩余缺口 <b style="color:#ef4444">{M['total_gap']:,.0f}台</b>。环比上月同期 <b style="color:{mom_color}">{M['mom_change']:+.1f}%</b>，日均需达成 <b>{M['daily_needed']:.0f}台</b>。</div>
</div>
<div class="report-block">
    <div class="report-title">📅 今日表现 ({today['date']})</div>
    <div class="report-text">智能机 <b>{today['smart_qty']:.0f}台</b> + 功能机 <b>{today['feature_qty']:.0f}台</b> = 总销量 <b>{today['total_qty']:.0f}台</b>。营收 <b>₦{today['revenue']/1e6:.1f}M</b>，毛利 <b>₦{today['profit']/1e6:.1f}M</b>，毛利率 <b>{today['profit_rate']:.1f}%</b>。日目标完成度 <b style="color:{'#22c55e' if today_vs_target>=100 else '#ef4444'}">{today_vs_target:.0f}%</b>。</div>
</div>
<div class="report-block">
    <div class="report-title">📈 趋势判断</div>
    <div class="report-text">近7日趋势：<b>{trend_desc}</b>。前3日均 <b>{first3/3:.0f}台</b> → 后3日均 <b>{last3/3:.0f}台</b>。</div>
</div>
<div class="report-block">
    <div class="report-title">🏆 品牌 TOP3</div>
    <div class="report-text">{'  '.join(f"<b>{i+1}.{b['品牌']}</b> {b['qty']:.0f}台 ({b.get('profit_rate',0):.1f}%)" for i, b in enumerate(top3_brands))}</div>
</div>
<div class="report-block">
    <div class="report-title">⚠️ 品牌关注</div>
    <div class="report-text">毛利率最高 <b>{best_pr_brand['品牌']}</b> ({best_pr_brand.get('profit_rate',0):.1f}%)，最低 <b>{worst_pr_brand['品牌']}</b> ({worst_pr_brand.get('profit_rate',0):.1f}%)。尾部品牌：{'  '.join(f"{b['品牌']} {b['qty']:.0f}台" for b in bottom3_brands)}。</div>
</div>
<div class="report-block">
    <div class="report-title">🏪 门店表现</div>
    <div class="report-text">最佳：{'  '.join(f"<b>{s['short']}</b> {s['rate']:.0f}%" for s in top3_stores)}。落后：{'  '.join(f"<b style='color:#ef4444'>{s['short']}</b> {s['rate']:.0f}%" for s in bottom3_stores)}。</div>
</div>"""

# ===== Historical Data Helpers =====
if H:
    hdata = H['data']
    hsum = H['summaries']
    hbrand = H['brand_data']
    
    # Store count
    total_stores_h = len(hdata['phone_sales'])
    
    # Monthly totals
    mt = hsum['monthly_total_phone_sales']
    sorted_months = sorted(mt.keys())
    latest_month_label = sorted_months[-1]
    latest_month_total = mt[latest_month_label]
    
    # YoY
    latest_yoy = hsum['yoy_growth_rates'].get(latest_month_label, 0)
    prev_year_parts = latest_month_label.split('-')
    prev_year_label = f"{int(prev_year_parts[0])-1}-{prev_year_parts[1]}"
    
    # All-time total
    total_sales_alltime = sum(v for v in mt.values() if v is not None)
    
    # Peak month
    peak_month = max(mt, key=mt.get)
    peak_sales = mt[peak_month]
    
    # 2026 YTD (all available months in 2026)
    months_2026_all = [m for m in sorted_months if m.startswith('2026-')]
    ytd_2026 = sum(mt.get(m, 0) or 0 for m in months_2026_all)
    month_count_2026 = len(months_2026_all)
    
    # Historical monthly data for charts (as JS arrays)
    history_months_js = json.dumps(sorted_months)
    history_sales_js = json.dumps([mt[m] for m in sorted_months])
    history_yoy_js = json.dumps([hsum['yoy_growth_rates'].get(m, None) for m in sorted_months])
    
    # Recent 18 months subset for cleaner default view
    recent_months = sorted_months[-18:] if len(sorted_months) > 18 else sorted_months
    recent_months_js = json.dumps(recent_months)
    recent_sales_js = json.dumps([mt[m] for m in recent_months])
    
    # Brand data: only 2026 (no 2025 data available)
    brands_2026 = hbrand.get('2026', {})
    all_brands = sorted(brands_2026.keys(),
                        key=lambda b: sum(v for v in brands_2026.get(b, {}).values() if v is not None), reverse=True)
    
    # Brand monthly: 2026 all available months
    brand_2026_data = {}
    months_2026_only = sorted([m for m in sorted_months if m.startswith('2026-')])
    brand_month_labels = [f'{int(m.split("-")[1])}月' for m in months_2026_only]
    for b in all_brands[:8]:  # top 8 brands
        b26 = brands_2026.get(b, {})
        d26 = [b26.get(m, 0) or 0 for m in months_2026_only]
        brand_2026_data[b] = {'data': d26, 'total': sum(d26)}
    
    # Brand market share for 2026 (stacked bar)
    brand_share_labels = []
    brand_share_datasets = []
    colors_brand = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16','#f97316','#64748b']
    for i, b in enumerate(all_brands[:8]):
        b26 = brands_2026.get(b, {})
        d = [b26.get(m, 0) or 0 for m in months_2026_only]
        brand_share_datasets.append({
            'label': b, 'data': d,
            'backgroundColor': colors_brand[i % len(colors_brand)] + '88',
            'borderColor': colors_brand[i % len(colors_brand)],
            'borderWidth': 1
        })
    brand_share_labels_js = json.dumps(brand_month_labels)
    brand_share_datasets_js = json.dumps(brand_share_datasets)
    
    # Revenue & Profit monthly (as Naira millions)
    rev_monthly = {}
    profit_monthly = {}
    for store, months in hdata.get('revenue', {}).items():
        for m, v in months.items():
            if v is not None:
                rev_monthly[m] = rev_monthly.get(m, 0) + v
    for store, months in hdata.get('gross_profit', {}).items():
        for m, v in months.items():
            if v is not None:
                profit_monthly[m] = profit_monthly.get(m, 0) + v
    
    rev_data = [rev_monthly.get(m, 0) / 1e6 for m in sorted_months]
    profit_data = [profit_monthly.get(m, 0) / 1e6 for m in sorted_months]
    
    # Store ranking table rows (2026 only) — include all available months
    def history_store_rows():
        store_list = []
        for store, months_data in hdata['phone_sales'].items():
            monthly_2026 = {}
            for m in months_2026_only:
                mm = int(m.split('-')[1])
                monthly_2026[mm] = months_data.get(m, 0) or 0
            ytd = sum(monthly_2026.values())
            store_list.append((store, monthly_2026, ytd))
        store_list.sort(key=lambda x: x[2], reverse=True)
        
        rows = []
        n_months = len(months_2026_only)
        for rank, (store, mdata, ytd) in enumerate(store_list[:15], 1):
            short = store.replace('D_', '').replace('D_MSL ', '').replace('-', ' ')[:25]
            avg = ytd / max(n_months, 1)
            # Trend: compare last 2 months
            month_nums = sorted(mdata.keys())
            trend = ''
            if len(month_nums) >= 2:
                last = mdata[month_nums[-1]]
                prev = mdata[month_nums[-2]]
                if prev > 0 and last > prev * 1.1:
                    trend = '<span style="color:#22c55e">📈 上升</span>'
                elif prev > 0 and last < prev * 0.9:
                    trend = '<span style="color:#ef4444">📉 下降</span>'
                else:
                    trend = '<span style="color:#94a3b8">➡ 平稳</span>'
            
            row_vals = [str(rank), short] + [f'{mdata[m]:.0f}' for m in month_nums] + [f'{ytd:.0f}', f'{avg:.0f}', trend]
            rows.append('<tr>' + ''.join(f'<td>{v}</td>' for v in row_vals) + '</tr>')
        return '\n'.join(rows)
    
    # Brand monthly comparison data for JS — 2026 only
    brand_monthly_labels_js = json.dumps(brand_month_labels)
    brand_monthly_datasets_js = json.dumps([
        {
            'label': f'{b} 2026',
            'data': brand_2026_data[b]['data'],
            'borderColor': colors_brand[i % len(colors_brand)],
            'backgroundColor': colors_brand[i % len(colors_brand)] + '44',
            'tension': 0.3,
            'borderWidth': 2.5
        } for i, b in enumerate(all_brands[:8]) if b in brand_2026_data
    ])
    
    # Revenue & Profit JS
    rev_profit_labels_js = json.dumps([m.replace('2023-','23-').replace('2024-','24-').replace('2025-','25-').replace('2026-','26-') for m in sorted_months])
    rev_data_js = json.dumps(rev_data)
    profit_data_js = json.dumps(profit_data)

    print(f"[History] {total_stores_h} stores, {len(sorted_months)} months loaded")

    # 2026-only data for default view
    months_2026 = [m for m in sorted_months if m.startswith('2026-')]
    sales_2026 = [mt[m] for m in months_2026]
    months_2026_js = json.dumps(months_2026)
    sales_2026_js = json.dumps(sales_2026)
    
    # ========== 历史趋势分析洞察 ==========
    # 1. YTD
    ytd_sum = sum(mt.get(m, 0) or 0 for m in months_2026_all)
    monthly_avg_2026 = ytd_sum / max(month_count_2026, 1)
    
    # 2. 近期趋势：最近3个月 vs 前3个月
    recent_3_months = months_2026_all[-3:] if len(months_2026_all) >= 3 else months_2026_all
    prev_3_months = months_2026_all[-6:-3] if len(months_2026_all) >= 6 else months_2026_all[:len(months_2026_all)//2]
    recent_3_sum = sum(mt.get(m, 0) or 0 for m in recent_3_months)
    prev_3_sum = sum(mt.get(m, 0) or 0 for m in prev_3_months)
    trend_pct = ((recent_3_sum - prev_3_sum) / prev_3_sum * 100) if prev_3_sum > 0 else 0
    
    # 3. 最佳/最差月份
    peak_sales_val = 0
    worst_sales_val = float('inf')
    peak_month_label = ''
    worst_month_label = ''
    for m in months_2026_all:
        v = mt.get(m, 0) or 0
        if v > peak_sales_val:
            peak_sales_val = v
            peak_month_label = m
        if v < worst_sales_val and v > 0:
            worst_sales_val = v
            worst_month_label = m
    peak_mm = int(peak_month_label.split('-')[1]) if peak_month_label else 0
    
    # 4. 生成洞察文字
    history_insight_items = []
    
    # YTD 累计 + 月均
    history_insight_items.append(f"📊 <b>2026累计 {ytd_sum:,.0f}台</b> · 月均 {monthly_avg_2026:,.0f}台 · {month_count_2026}个月数据")
    
    # 趋势方向
    if trend_pct > 5:
        history_insight_items.append(f"📈 <b>近期趋势向上</b>：近3月({', '.join(recent_3_months)})环比+{trend_pct:.1f}%")
    elif trend_pct < -5:
        history_insight_items.append(f"📉 <b>近期趋势向下</b>：近3月环比{trend_pct:.1f}%，需关注下滑原因")
    else:
        history_insight_items.append(f"📊 <b>近期走势平稳</b>：近3月环比{trend_pct:+.1f}%")
    
    # 2026年月度趋势
    sales_2026_list = [mt.get(m, 0) or 0 for m in months_2026_all]
    if len(sales_2026_list) >= 2:
        best_m_idx = sales_2026_list.index(max(sales_2026_list))
        worst_m_idx = sales_2026_list.index(min(v for v in sales_2026_list if v > 0))
        best_m_label = months_2026_all[best_m_idx].split('-')[1] + '月'
        worst_m_label = months_2026_all[worst_m_idx].split('-')[1] + '月'
        history_insight_items.append(f"🏆 <b>2026年内最佳/最差月</b>：{best_m_label}（{max(sales_2026_list):,.0f}台）/ {worst_m_label}（{min(sales_2026_list):,.0f}台）")
    
    history_insight_html = '<div class="history-insight-box"><h4>📊 趋势分析摘要</h4>' + \
        ''.join(f'<div class="insight-item">{item}</div>' for item in history_insight_items) + \
        '</div>'
    
    # ========== 季度表现汇总 ==========
    # Compute quarterly totals for 2026
    q_data = {}
    q_data['2026'] = {}
    for q in [1, 2, 3, 4]:
        m_start = (q-1)*3 + 1
        m_end = q*3
        total = sum(mt.get(f'2026-{m:02d}', 0) or 0 for m in range(m_start, m_end+1))
        q_data['2026'][q] = total
    q_labels_js = json.dumps(['Q1','Q2','Q3','Q4'])
    q_2026_js = json.dumps([q_data['2026'][q] for q in [1,2,3,4] if q_data['2026'][q] > 0])
    
    # ========== 品牌贡献排行 ==========
    # Top brands: 2026 YTD contribution
    brand_ranking = []
    for b in all_brands[:8]:
        s26 = brand_2026_data.get(b, {}).get('total', 0)
        pct = (s26 / ytd_sum * 100) if ytd_sum > 0 else 0
        brand_ranking.append((b, s26, pct))
    brand_ranking.sort(key=lambda x: x[1], reverse=True)
    brand_rank_labels_js = json.dumps([b[0] for b in brand_ranking])
    brand_rank_data_js = json.dumps([b[1] for b in brand_ranking])
    brand_rank_pct_js = json.dumps([round(b[2], 1) for b in brand_ranking])
    
    # Build history page HTML (as f-string to use computed vars)
    history_page_html = f"""
<!-- ===== PAGE: 历史趋势 ===== -->
<div id="page-history" style="display:none">

<!-- KPI Row (no data span / all-time total) -->
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">最新月销量 ({latest_month_label})</div>
        <div class="kpi-value">{fmt_n(latest_month_total)}</div>
        <div class="kpi-sub">日均 {latest_month_total/26:.0f} 台 · 环比{'+' if latest_month_total > (mt.get(sorted_months[-2], 0) or 0) else ''}{(latest_month_total - (mt.get(sorted_months[-2], 0) or 0)) / max((mt.get(sorted_months[-2], 0) or 0), 1) * 100:+.1f}%</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">2026 累计销量</div>
        <div class="kpi-value">{fmt_n(ytd_2026)}</div>
        <div class="kpi-sub">{month_count_2026}个月 · 月均 {ytd_2026/month_count_2026:,.0f} 台</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">历史最高月销量</div>
        <div class="kpi-value" style="color:#22c55e">{fmt_n(peak_sales)}</div>
        <div class="kpi-sub">{peak_month}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">全系统门店数</div>
        <div class="kpi-value">{total_stores_h}</div>
        <div class="kpi-sub">覆盖全部销售部门</div>
    </div>
</div>

<!-- Monthly Phone Sales KPI Summary -->

{history_insight_html}

<!-- Chart 1: Monthly Phone Sales Trend -->
<div class="section">
    <div class="section-header">
        <div class="section-title">📈 公司智能机零售销量</div>
        <div class="sub-tabs" style="margin-left:auto">
            <button class="sub-tab active" onclick="switchMonthlyView('thisyear', this)">2026年</button>
            <button class="sub-tab" onclick="switchMonthlyView('all', this)">全部历史</button>
        </div>
    </div>
    <div class="section-body">
        <div id="chart_history_monthly_wrap" style="height:420px"><canvas id="chart_history_monthly"></canvas></div>
        <div id="chart_history_monthly_all_wrap" style="display:none;height:420px"><canvas id="chart_history_monthly_all"></canvas></div>
    </div>
</div>

<!-- Chart 2: Brand Market Share Evolution -->
<div class="section">
    <div class="section-header"><div class="section-title">🎯 品牌月度销量趋势 (2026年)</div></div>
    <div class="section-body">
        <div class="sub-tabs" style="margin-bottom:8px">
            <button class="sub-tab active" onclick="switchBrandView('brand_monthly',this)">📊 月度对比</button>
            <button class="sub-tab" onclick="switchBrandView('brand_share',this)">🥧 市场份额</button>
        </div>
        <div id="brand_monthly" style="height:420px"><canvas id="chart_history_brand_monthly"></canvas></div>
        <div id="brand_share" style="display:none;height:420px"><canvas id="chart_history_brand_share"></canvas></div>
    </div>
</div>

<!-- Chart 3: YoY Growth + Revenue/Profit -->
<div class="section">
    <div class="section-header"><div class="section-title">📊 营收毛利 & 品牌贡献</div></div>
    <div class="section-body">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
            <div><h4 style="margin:0 0 8px;font-size:13px;color:var(--text2)">月度销售额 & 毛利 (百万₦)</h4><div style="height:320px"><canvas id="chart_history_rev_profit"></canvas></div></div>
            <div><h4 style="margin:0 0 8px;font-size:13px;color:var(--text2)">品牌2026累计贡献 TOP8</h4><div style="height:320px"><canvas id="chart_history_brand_contrib"></canvas></div></div>
        </div>
    </div>
</div>

<!-- Store Rankings -->
<div class="section">
    <div class="section-header"><div class="section-title">🏪 2026年门店月度销量排名 TOP15</div></div>
    <div class="section-body">
        <div class="tbl-wrap" style="max-height:500px">
            <table id="tbl_history_store"><thead><tr>
                <th onclick="sortTable('tbl_history_store',0)">排名</th>
                <th onclick="sortTable('tbl_history_store',1)">门店</th>
""" + ''.join(f'<th onclick="sortTable(\'tbl_history_store\',{i+2})">{int(m.split("-")[1])}月</th>' for i, m in enumerate(months_2026_only)) + """
                <th onclick="sortTable('tbl_history_store',""" + str(len(months_2026_only)+2) + """)">YTD合计</th>
                <th onclick="sortTable('tbl_history_store',""" + str(len(months_2026_only)+3) + """)">月均</th>
                <th onclick="sortTable('tbl_history_store',""" + str(len(months_2026_only)+4) + """)">趋势</th>
            </tr></thead><tbody>""" + history_store_rows() + """</tbody></table>
        </div>
    </div>
</div>

</div><!-- end page-history -->
"""

    # Build history JS code
    history_js = f"""
// ===== HISTORY CHARTS =====
function initHistoryCharts() {{
    // Chart 1a: 2026 Only (default view)
    var chartMonthly2026 = new Chart(document.getElementById('chart_history_monthly'), {{
        type: 'line',
        data: {{
            labels: {months_2026_js},
            datasets: [
                {{
                    label: '公司智能机零售销量',
                    data: {sales_2026_js},
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 7
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true }} }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y.toLocaleString() + ' 台' }} }}
            }},
            scales: {{
                y: {{ beginAtZero: false, grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8' }} }},
                x: {{ grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8', maxRotation: 45 }} }}
            }}
        }}
    }});

    // Chart 1b: Full History (lazy init)
    var chartMonthlyAll = null;
    function initMonthlyAll() {{
        if (chartMonthlyAll) return;
        var canvas = document.getElementById('chart_history_monthly_all');
        chartMonthlyAll = new Chart(canvas, {{
            type: 'line',
            data: {{
                labels: {history_months_js},
                datasets: [
                    {{
                        label: '公司智能机零售销量',
                        data: {history_sales_js},
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59,130,246,0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 1,
                        pointHoverRadius: 5,
                        borderWidth: 1.5
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true }} }},
                    tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y.toLocaleString() + ' 台' }} }}
                }},
                scales: {{
                    y: {{ beginAtZero: false, grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8' }} }},
                    x: {{ grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8', maxRotation: 60, font: {{ size: 9 }} }} }}
                }}
            }}
        }});
    }}

    // Switch monthly view
    window.switchMonthlyView = function(view, btn) {{
        var thisYearWrap = document.getElementById('chart_history_monthly_wrap');
        var allWrap = document.getElementById('chart_history_monthly_all_wrap');
        btn.parentElement.querySelectorAll('.sub-tab').forEach(function(t) {{ t.classList.remove('active'); }});
        btn.classList.add('active');
        if (view === 'thisyear') {{
            thisYearWrap.style.display = 'block';
            allWrap.style.display = 'none';
        }} else {{
            thisYearWrap.style.display = 'none';
            allWrap.style.display = 'block';
            initMonthlyAll();
        }}
    }};

    // Chart 2a: Brand Monthly Comparison
    new Chart(document.getElementById('chart_history_brand_monthly'), {{
        type: 'line',
        data: {{
            labels: {brand_monthly_labels_js},
            datasets: {brand_monthly_datasets_js}
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true, boxWidth: 10, padding: 8, font: {{ size: 10 }} }} }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString() + ' 台' }} }}
            }},
            scales: {{
                y: {{ beginAtZero: false, grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8' }} }},
                x: {{ grid: {{ color: 'rgba(51,65,85,0.2)' }}, ticks: {{ color: '#94a3b8' }} }}
            }}
        }}
    }});

    // Chart 2b: Brand Share (Stacked Bar)
    new Chart(document.getElementById('chart_history_brand_share'), {{
        type: 'bar',
        data: {{
            labels: {brand_share_labels_js},
            datasets: {brand_share_datasets_js}
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true, boxWidth: 10, padding: 8, font: {{ size: 10 }} }} }}
            }},
            scales: {{
                x: {{ stacked: true, grid: {{ color: 'rgba(51,65,85,0.2)' }}, ticks: {{ color: '#94a3b8' }} }},
                y: {{ stacked: true, grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8' }} }}
            }}
        }}
    }});

    // Chart 3: Brand Contribution (Doughnut)
    new Chart(document.getElementById('chart_history_brand_contrib'), {{
        type: 'doughnut',
        data: {{
            labels: {brand_rank_labels_js},
            datasets: [{{
                data: {brand_rank_pct_js},
                backgroundColor: ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16'],
                borderColor: '#1e293b',
                borderWidth: 2
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true, boxWidth: 10, padding: 8, font: {{ size: 10 }}, generateLabels: function(chart) {{
                    const ds = chart.data.datasets[0];
                    return chart.data.labels.map((label, i) => ({{
                        text: label + ' (' + ds.data[i] + '%)',
                        fillStyle: ds.backgroundColor[i],
                        strokeStyle: ds.backgroundColor[i],
                        lineWidth: 0,
                        hidden: false,
                        index: i
                    }}));
                }} }} }},
                tooltip: {{ callbacks: {{ label: ctx => ctx.label + ': ' + ctx.parsed + '%' }} }}
            }}
        }}
    }});

    // Chart 4: Revenue & Profit
    new Chart(document.getElementById('chart_history_rev_profit'), {{
        type: 'line',
        data: {{
            labels: {rev_profit_labels_js},
            datasets: [
                {{
                    label: '营收 (百万₦)',
                    data: {rev_data_js},
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y'
                }},
                {{
                    label: '毛利 (百万₦)',
                    data: {profit_data_js},
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y1'
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true }} }},
                datalabels: {{ display: false }}
            }},
            scales: {{
                y: {{ type: 'linear', position: 'left', grid: {{ color: 'rgba(51,65,85,0.35)' }}, ticks: {{ color: '#94a3b8', callback: v => v.toFixed(0) + 'M' }} }},
                y1: {{ type: 'linear', position: 'right', grid: {{ display: false }}, ticks: {{ color: '#22c55e', callback: v => v.toFixed(0) + 'M' }} }},
                x: {{ grid: {{ color: 'rgba(51,65,85,0.2)' }}, ticks: {{ color: '#94a3b8', maxRotation: 45 }} }}
            }}
        }}
    }});
}}

function switchBrandView(name, btn) {{
    document.querySelectorAll('#page-history .sub-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('brand_monthly').style.display = name === 'brand_monthly' ? 'block' : 'none';
    document.getElementById('brand_share').style.display = name === 'brand_share' ? 'block' : 'none';
    if (name === 'brand_share') {{
        setTimeout(() => {{ if(window.Chart) Chart.helpers.each(Chart.instances, c => c.resize()); }}, 50);
    }}
}}
"""
else:
    history_page_html = ''
    history_js = ''

# Model analysis page HTML
if D.get('m10_model_analysis'):
    m10 = D['m10_model_analysis']
    m10_brands = D.get('m10_all_brands', [])
    m10_tiers = D.get('m10_price_tiers', [])
    # Build m11 lookup for daily sales analysis
    m11_lookup = {}
    for t in D.get('m11_model_trends', []):
        m11_lookup[t['model']] = t

    # Generate table rows
    m10_rows = ''
    for i, r in enumerate(m10):
        t = m11_lookup.get(r['model'], {})
        mom = t.get('mom_change', None)
        cv = t.get('cv_pct', None)
        slope = t.get('trend_slope', None)
        # Format trend direction
        if slope is not None:
            if slope < -2:
                trend_dir = '↓降'
                trend_color = '#ef4444'
            elif slope < 0:
                trend_dir = '↘缓'
                trend_color = '#f59e0b'
            elif slope > 2:
                trend_dir = '↑升'
                trend_color = '#22c55e'
            else:
                trend_dir = '→稳'
                trend_color = '#94a3b8'
        else:
            trend_dir = '—'
            trend_color = '#94a3b8'
        # Format MoM
        if mom is not None:
            mom_str = f'{mom:.1f}%'
            mom_color = '#22c55e' if mom > 0 else '#ef4444' if mom < 0 else '#94a3b8'
        else:
            mom_str = '—'
            mom_color = '#94a3b8'
        # Format CV
        if cv is not None:
            cv_str = f'{cv:.1f}%'
            cv_color = '#22c55e' if cv < 20 else '#f59e0b' if cv < 35 else '#ef4444'
        else:
            cv_str = '—'
            cv_color = '#94a3b8'
        m10_rows += f'''<tr data-brand="{r['brand']}" data-tier="{r['price_tier']}" data-i="{i}" onclick="toggleModelDetail({i})" style="cursor:pointer">
            <td>{i+1}</td>
            <td>{r['brand']}</td>
            <td style="text-align:left">{r['model']}</td>
            <td>{r['qty']}</td>
            <td>{r['daily_avg']}</td>
            <td style="color:{mom_color}">{mom_str}</td>
            <td style="color:{cv_color}">{cv_str}</td>
            <td style="color:{trend_color}">{trend_dir}</td>
            <td>₦{r['price']:,}</td>
            <td><span class="tier-badge tier-{r['price_tier'].replace(' ', '').replace('+','').replace('-','')}">{r['price_tier']}</span></td>
            <td style="color:{'#22c55e' if r['profit_margin']>0 else '#ef4444'}">{r['profit_margin']}%</td>
            <td>{r['total_inventory']}</td>
            <td style="color:{'#22c55e' if isinstance(r['turnover_days'], (int,float)) and r['turnover_days']<30 else '#ef4444' if isinstance(r['turnover_days'], (int,float)) and r['turnover_days']>60 else '#f59e0b'}">{r['turnover_days']}</td>
        </tr>'''

    model_section_html = f'''
<!-- S10: 型号销量分析 (embedded in deep analysis) -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">10</span> 型号销量分析（智能机+平板）</div>
        <div style="font-size:11px;color:var(--text2)">共{len(m10)}个型号 | 点击型号行展开日销量分析 | 点击表头可排序</div>
    </div>
    <div class="section-body">
        <!-- Filters -->
        <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center;">
            <input type="text" id="m10-search" placeholder="🔍 搜索型号..." style="padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--card2);color:var(--text1);font-size:13px;width:200px;">
            <select id="m10-brand-filter" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--card2);color:var(--text1);font-size:13px;">
                <option value="全部">全部品牌</option>
                {''.join(f'<option value="{b}">{b}</option>' for b in m10_brands)}
            </select>
            <select id="m10-tier-filter" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--card2);color:var(--text1);font-size:13px;">
                {''.join(f'<option value="{t}">{t}</option>' for t in m10_tiers)}
            </select>
            <button onclick="m10ResetFilters()" style="padding:8px 16px;border-radius:8px;border:1px solid var(--border);background:var(--card2);color:var(--text1);font-size:13px;cursor:pointer;">🔄 重置筛选</button>
        </div>
        <!-- Table -->
        <div class="tbl-wrap" style="max-height:70vh">
            <table id="tbl-model">
                <thead>
                    <tr>
                        <th onclick="m10Sort(0)" style="cursor:pointer">#</th>
                        <th onclick="m10Sort(1)" style="cursor:pointer">品牌</th>
                        <th style="text-align:left;cursor:pointer" onclick="m10Sort(2)">型号</th>
                        <th onclick="m10Sort(3)" style="cursor:pointer">销量 ↕</th>
                        <th onclick="m10Sort(4)" style="cursor:pointer">日销</th>
                        <th onclick="m10Sort(5)" style="cursor:pointer">环比 ↕</th>
                        <th onclick="m10Sort(6)" style="cursor:pointer">CV ↕</th>
                        <th onclick="m10Sort(7)" style="cursor:pointer">趋势</th>
                        <th onclick="m10Sort(8)" style="cursor:pointer">价格</th>
                        <th>价位段</th>
                        <th onclick="m10Sort(10)" style="cursor:pointer">毛利率</th>
                        <th onclick="m10Sort(11)" style="cursor:pointer">总库存</th>
                        <th onclick="m10Sort(12)" style="cursor:pointer">周转 ↕</th>
                    </tr>
                </thead>
                <tbody id="m10-tbody">
                    {m10_rows}
                </tbody>
            </table>
            <div id="m10-detail-panel" style="display:none;margin-top:12px;padding:16px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                    <h4 id="m10-detail-title" style="margin:0;font-size:14px;color:var(--blue)">型号日销量分析</h4>
                    <span onclick="closeModelDetail()" style="cursor:pointer;font-size:16px;color:var(--text2)">✕</span>
                </div>
                <div id="m10-detail-stats" style="display:flex;gap:16px;margin-bottom:12px;font-size:12px;color:var(--text2)"></div>
                <div style="position:relative;height:280px">
                    <canvas id="m10-detail-chart"></canvas>
                </div>
            </div>
            <div id="m10-pagination" style="margin-top:16px;display:flex;flex-wrap:wrap;align-items:center;gap:8px;"></div>
        </div>

        <!-- Model Sales Trend Chart -->
        <div style="margin-top:24px;padding-top:20px;border-top:1px solid var(--border)">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
                <h3 style="margin:0;font-size:14px;color:var(--blue)">📈 型号销量波动趋势（可多选对比，最多5个）</h3>
                <span style="font-size:11px;color:var(--text2)">蓝线={_curr_m_label}，橙/紫虚线={_cmp_m_label}同期参考</span>
            </div>
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
                <label style="color:var(--text2);font-size:11px;white-space:nowrap">品牌：</label>
                <select id="trend-brand-filter" onchange="filterTrendCombo()" style="padding:5px 8px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:11px;max-width:100px">
                    <option value="">全部品牌</option>
                </select>
                <label style="color:var(--text2);font-size:11px;white-space:nowrap;margin-left:4px">价位段：</label>
                <select id="trend-tier-filter" onchange="filterTrendCombo()" style="padding:5px 8px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:11px;max-width:100px">
                    <option value="">全部价位</option>
                </select>
                <div style="position:relative;margin-left:4px">
                    <button id="trend-combo-btn" onclick="toggleTrendCombo()"
                     style="padding:6px 24px 6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--card2);color:var(--text1);font-size:12px;cursor:pointer;text-align:left;min-width:180px;white-space:nowrap">
                        + 添加型号 ▾
                    </button>
                    <div id="trend-combo-dropdown" style="display:none;position:absolute;top:100%;left:0;width:280px;background:#1e293b;border:1px solid #334155;border-radius:6px;z-index:1000;margin-top:2px;box-shadow:0 8px 24px rgba(0,0,0,0.5)">
                        <div style="padding:6px 8px;border-bottom:1px solid #334155">
                            <input type="text" id="trend-combo-search" placeholder="输入型号搜索..."
                             style="width:100%;padding:6px 10px;border-radius:4px;border:1px solid #475569;background:#0f172a;color:#e2e8f0;font-size:12px;box-sizing:border-box"
                             oninput="filterTrendCombo()" onkeydown="handleTrendComboKey(event)" onclick="event.stopPropagation()">
                        </div>
                        <div id="trend-combo-list" style="max-height:350px;overflow-y:auto"></div>
                    </div>
                </div>
                <div id="trend-selected-tags" style="display:flex;gap:4px;flex-wrap:wrap"></div>
                <button onclick="clearTrendSelection()" style="padding:6px 12px;border-radius:6px;border:1px solid var(--border);background:var(--card2);color:var(--text2);font-size:12px;cursor:pointer">✕ 清除全部</button>
            </div>
            <div style="position:relative;height:340px">
                <canvas id="trendChart"></canvas>
            </div>
            <div id="trend-stats" style="margin-top:12px;font-size:11px;color:var(--text2)"></div>
        </div>
    </div>
</div>
'''
else:
    model_section_html = ''

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover,shrink-to-fit=no">
<title>销售部数据看板 | {M['report_date']}</title>

<!-- Open Graph / WeChat sharing preview -->
<meta property="og:title" content="销售部数据看板 | 完成率{M['completion_rate']:.1f}%">
<meta property="og:description" content="智能机{M['total_smart_qty']:.0f}台/{M['total_target']:.0f}台 · 剩余缺口{M['total_gap']:.0f}台 · {len(D['m1_store_target'])}家门店 · 点击查看完整报告">
<meta property="og:image" content="/share-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:type" content="website">
<meta property="og:site_name" content="销售部数据看板">
<!-- WeChat specific -->
<meta itemprop="name" content="销售部数据看板 | 完成率{M['completion_rate']:.1f}%">
<meta itemprop="description" content="智能机{M['total_smart_qty']:.0f}台/{M['total_target']:.0f}台 · 剩余缺口{M['total_gap']:.0f}台 · 点击查看完整报告">
<meta itemprop="image" content="/share-card.png">
<!-- WeChat disable text selection & callout menu -->
<meta name="format-detection" content="telephone=no,email=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>
<style>
:root {{
    --bg: #0f172a; --surface: #1e293b; --surface2: #334155;
    --border: #334155; --text: #f1f5f9; --text2: #94a3b8;
    --card: #1e293b; --card2: #334155; --text1: #f1f5f9; --muted: #94a3b8;
    --red: #ef4444; --green: #16a34a; --blue: #2563eb; --yellow: #d97706; --orange: #ea580c;
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:var(--font); background:var(--bg); color:var(--text); font-size:13px; line-height:1.5; }}
.header {{ background:linear-gradient(135deg,#1e293b,#0f172a); padding:16px 24px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:100; color:#fff; }}
.header h1 {{ font-size:18px; font-weight:700; color:#fff; }}
.header .date {{ color:#94a3b8; font-size:12px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
.header .time-progress {{ background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 8px; border-radius:4px; font-weight:600; font-size:11px; border:1px solid rgba(59,130,246,0.25); }}
.mode-tabs {{ display:flex; gap:4px; }}
.mode-tab {{ padding:6px 16px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600; border:1px solid rgba(255,255,255,0.15); color:#94a3b8; background:transparent; transition:all .2s; }}
.mode-tab.active {{ background:rgba(255,255,255,0.25); color:#fff; border-color:rgba(255,255,255,0.5); }}
.page-tabs {{ display:flex; gap:4px; }}
.page-tab {{ padding:6px 16px; border-radius:6px; cursor:pointer; font-size:13px; font-weight:700; border:1px solid var(--border); color:var(--text2); background:transparent; transition:all .2s; }}
.page-tab.active {{ background:var(--blue); color:#fff; border-color:var(--blue); }}
.page-tab-badge {{ font-size:10px; background:var(--red); color:#fff; padding:1px 6px; border-radius:8px; margin-left:2px; }}
.pf-btn.active {{ background:var(--surface2); color:var(--text); border-color:var(--text2); }}
.container {{ max-width:1400px; margin:0 auto; padding:16px; }}

/* KPI Cards */
.kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:16px; }}
.kpi-card {{ background:var(--surface); border-radius:10px; padding:14px 16px; border:1px solid var(--border); }}
.kpi-label {{ color:var(--text2); font-size:11px; text-transform:uppercase; letter-spacing:.5px; }}
.kpi-value {{ font-size:22px; font-weight:800; margin:4px 0; }}
.kpi-sub {{ font-size:11px; color:var(--text2); }}

/* Sections */
.section {{ background:var(--surface); border-radius:10px; margin-bottom:16px; border:1px solid var(--border); overflow:hidden; }}
.section-header {{ padding:12px 16px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }}
.section-title {{ font-size:14px; font-weight:700; display:flex; align-items:center; gap:8px; }}
.section-title .num {{ background:var(--blue); color:#fff; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:11px; }}
.section-body {{ padding:12px 16px; }}

/* Tier cards */
.tier-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; margin-bottom:16px; }}
.tier-card {{ background:var(--surface2); border-radius:8px; padding:12px 14px; }}
.tier-name {{ font-size:13px; font-weight:700; }}
.tier-rate {{ font-size:28px; font-weight:800; margin:4px 0; }}
.tier-detail {{ font-size:11px; color:var(--text2); }}
.tier-stores {{ font-size:10px; color:var(--text2); margin-top:4px; word-break:break-all; }}

/* Tables */
.tbl-wrap {{ overflow-x:auto; max-height:500px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th {{ background:var(--surface2); color:var(--text); font-weight:600; text-align:left; padding:8px 10px; position:sticky; top:0; z-index:5; cursor:pointer; white-space:nowrap; }}
td {{ padding:7px 10px; border-bottom:1px solid var(--border); white-space:nowrap; }}
tr:hover {{ background:rgba(255,255,255,0.05) !important; }}
.m6-table th {{ background:rgba(51,65,85,0.9); color:var(--text); border-bottom:1px solid var(--border); }}
.m6-table td {{ border-bottom-color:rgba(51,65,85,0.6); color:var(--text); }}
.store-name {{ font-weight:600; max-width:120px; overflow:hidden; text-overflow:ellipsis; }}

/* M12 Sortable Table */
.m12-sortable {{ user-select:none; transition:background 0.15s; }}
.m12-sortable:hover {{ background:#3b82f6 !important; color:#fff !important; }}
.m12-sortable.m12-active {{ background:#1e3a5f !important; }}
.m12-arrow {{ font-size:10px; color:var(--text2); margin-left:2px; }}
.m12-active .m12-arrow {{ color:#3b82f6; font-weight:700; }}
.m12-sortable:hover .m12-arrow {{ color:#fff; }}
.model-name {{ max-width:200px; overflow:hidden; text-overflow:ellipsis; }}
.tier-badge {{ padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }}
.tier-badge.tier-10w以下 {{ background:#22c55e22;color:#22c55e;border:1px solid #22c55e55; }}
.tier-badge.tier-10w {{ background:#86efac22;color:#16a34a;border:1px solid #16a34a55; }}
.tier-badge.tier-20w {{ background:#fef08a22;color:#ca8a04;border:1px solid #ca8a0455; }}
.tier-badge.tier-30w {{ background:#f59e0b22;color:#d97706;border:1px solid #d9770655; }}
.tier-badge.tier-40w {{ background:#fb923c22;color:#ea580c;border:1px solid #ea580c55; }}
.tier-badge.tier-50w {{ background:#ef444422;color:#ef4444;border:1px solid #ef444455; }}
.tier-badge.tier-50-100w {{ background:#a855f722;color:#a855f7;border:1px solid #a855f755; }}
.tier-badge.tier-100w以上 {{ background:#6366f122;color:#6366f1;border:1px solid #6366f155; }}
.issue-type {{ padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}

/* Progress */
.progress-wrap {{ display:flex; align-items:center; gap:6px; min-width:100px; }}
.progress-bar {{ height:6px; border-radius:3px; min-width:2px; }}
.progress-wrap span {{ font-size:11px; white-space:nowrap; min-width:36px; }}

/* Charts */
.chart-row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }}
.chart-box {{ background:var(--surface); border-radius:10px; border:1px solid var(--border); padding:14px; }}
.chart-box canvas {{ max-height:280px; }}
.chart-title {{ font-size:13px; font-weight:700; margin-bottom:10px; color:var(--text); }}

/* Alert boxes */
.alert-box {{ padding:12px 16px; border-radius:8px; margin-bottom:12px; font-size:12px; line-height:1.8; color:var(--text); }}
.alert-red {{ background:rgba(239,68,68,0.08); border-left:4px solid var(--red); color:var(--text); }}
.alert-yellow {{ background:rgba(245,158,11,0.08); border-left:4px solid var(--yellow); color:var(--text); }}
.alert-blue {{ background:rgba(59,130,246,0.08); border-left:4px solid var(--blue); color:var(--text); }}

/* WeChat Data Report blocks */
.report-summary {{ display:flex; flex-direction:column; gap:10px; }}
.report-block {{ background:var(--surface); border-radius:10px; padding:14px 16px; border:1px solid var(--border); }}
.report-block:first-child {{ background:linear-gradient(135deg,rgba(59,130,246,0.15),rgba(59,130,246,0.08)); border-color:var(--blue); }}
.report-title {{ font-size:13px; font-weight:700; color:var(--text2); margin-bottom:6px; }}
.report-block:first-child .report-title {{ color:#60a5fa; }}
.report-text {{ font-size:13px; color:var(--text); line-height:1.8; }}
.report-text b {{ color:var(--text); }}

/* Sub-tabs */
.sub-tabs {{ display:flex; gap:2px; margin-bottom:12px; }}
.sub-tab {{ padding:4px 12px; border-radius:6px; cursor:pointer; font-size:11px; color:var(--text2); background:var(--surface2); border:none; }}
.sub-tab.active {{ background:var(--blue); color:#fff; }}

/* Mode visibility */
.report-only {{ }}
.analysis-only {{ }}
#mode-analysis {{ min-height: 0; }}
#mode-analysis .chart-box canvas {{ width: 100% !important; }}

/* M6 sub-sections */
.inv-sub {{ margin-bottom:16px; }}
.inv-sub h4 {{ font-size:13px; font-weight:700; margin-bottom:8px; padding-left:8px; border-left:3px solid var(--orange); }}

/* Footer summary */
.summary-box {{ background:var(--surface); border-radius:10px; padding:16px; border:1px solid var(--border); margin-bottom:16px; }}
.summary-box h3 {{ font-size:14px; font-weight:700; margin-bottom:8px; color:#60a5fa; }}
.summary-box p {{ font-size:12px; line-height:1.9; color:#cbd5e1; }}
.summary-box b {{ color:#f1f5f9; }}

@media(max-width:768px) {{
    /* ===== BASE ===== */
    body {{ font-size:14px; -webkit-text-size-adjust:100%; }}
    .container {{ padding:8px; max-width:100vw; }}

    /* ===== HEADER ===== */
    .header {{ padding:10px 12px; flex-wrap:wrap; gap:8px; position:static; }}
    .header h1 {{ font-size:15px; }}
    .header .date {{ font-size:10px; }}
    .page-tabs, .mode-tabs {{ flex-wrap:wrap; gap:3px; }}
    .page-tab, .mode-tab {{ padding:8px 10px; font-size:11px; min-height:44px; display:inline-flex; align-items:center; white-space:nowrap; }}
    .page-tab .page-tab-badge {{ font-size:9px; padding:1px 4px; }}

    /* ===== KPI ===== */
    .kpi-row {{ grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px; }}
    .kpi-card {{ padding:10px 12px; border-radius:8px; }}
    .kpi-label {{ font-size:10px; }}
    .kpi-value {{ font-size:18px; }}
    .kpi-sub {{ font-size:10px; }}

    /* ===== SECTIONS ===== */
    .section {{ margin-bottom:10px; border-radius:8px; }}
    .section-header {{ padding:10px 12px; }}
    .section-title {{ font-size:13px; }}
    .section-title .num {{ width:20px; height:20px; font-size:10px; }}
    .section-body {{ padding:8px 10px; }}

    /* ===== TIER CARDS ===== */
    .tier-grid {{ grid-template-columns:1fr 1fr; gap:8px; }}
    .tier-card {{ padding:10px 12px; }}
    .tier-name {{ font-size:12px; }}
    .tier-rate {{ font-size:22px; }}
    .tier-detail {{ font-size:10px; }}
    .tier-stores {{ font-size:9px; }}

    /* ===== CHARTS ===== */
    .chart-row {{ grid-template-columns:1fr; gap:10px; margin-bottom:10px; }}
    .chart-box {{ padding:10px; }}
    .chart-box canvas {{ max-height:220px !important; height:220px !important; }}
    .chart-title {{ font-size:12px; margin-bottom:6px; }}

    /* ===== TABLES - horizontal scroll ===== */
    .tbl-wrap {{ max-height:350px; overflow-x:auto; -webkit-overflow-scrolling:touch; }}
    table {{ font-size:11px; min-width:600px; }}
    th {{ padding:6px 8px; font-size:10px; }}
    td {{ padding:5px 8px; font-size:10px; }}
    .store-name {{ max-width:80px; }}
    .model-name {{ max-width:130px; }}

    /* M6 tables */
    .m6-table th {{ font-size:10px; padding:6px 8px; }}
    .m6-table td {{ font-size:10px; padding:5px 8px; }}

    /* ===== ALERTS ===== */
    .alert-box {{ padding:10px 12px; font-size:11px; line-height:1.7; }}

    /* ===== SUMMARY ===== */
    .summary-box {{ padding:12px; }}
    .summary-box h3 {{ font-size:13px; }}
    .summary-box p {{ font-size:11px; }}

    /* ===== MODE SWITCHING ===== */
    #mode-analysis .chart-box canvas {{ height:200px !important; }}

    /* ===== REPORT BLOCKS ===== */
    .report-block {{ padding:10px 12px; }}
    .report-title {{ font-size:12px; }}
    .report-text {{ font-size:12px; line-height:1.7; }}

    /* ===== PROGRESS BARS ===== */
    .progress-wrap {{ min-width:70px; }}
    .progress-bar {{ height:4px; }}
    .progress-wrap span {{ font-size:10px; min-width:30px; }}

    /* ===== SUB TABS ===== */
    .sub-tabs {{ overflow-x:auto; -webkit-overflow-scrolling:touch; white-space:nowrap; }}
    .sub-tab {{ padding:6px 10px; font-size:10px; min-height:36px; }}
}}

/* Phone-small */
@media(max-width:420px) {{
    .kpi-row {{ grid-template-columns:1fr 1fr; }}
    .kpi-value {{ font-size:16px; }}
    .tier-grid {{ grid-template-columns:1fr; }}
    .header {{ flex-direction:column; align-items:flex-start; }}
    .header > div:last-child {{ width:100%; display:flex; flex-wrap:wrap; gap:4px; }}
    .page-tab, .mode-tab {{ flex:1; text-align:center; justify-content:center; }}
    .chart-box canvas {{ max-height:180px !important; height:180px !important; }}
}}

/* WeChat specific */
@media screen and (min-width:0\\0) {{
    /* WeChat smooth scroll */
    body {{ -webkit-overflow-scrolling:touch; }}
    /* Disable long-press callout */
    * {{ -webkit-touch-callout:none; -webkit-user-select:none; user-select:none; }}
    input, textarea {{ -webkit-user-select:text; user-select:text; }}
    /* Hide WeChat bottom navigation bar space */
    body::after {{ content:''; display:block; height:env(safe-area-inset-bottom); }}
    /* Prevent pull-to-refresh */
    body {{ overscroll-behavior:none; }}
}}

</style>
</head>
<body>
<div class="header">
    <div>
        <h1>📊 销售部数据看板</h1>
        <div class="date">数据周期: {M['period']} <span class="time-progress">时间进度 {M['time_progress_pct']:.1f}%</span> | 已过{M['elapsed_days']:.0f}天 / 剩余{M['remaining_days']:.0f}天 | 生成时间: {M['report_date']}</div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
        <div class="page-tabs" id="page-tabs" style="display:none;gap:4px;margin-right:12px;">
            <button class="page-tab active" onclick="switchPage('dashboard')" id="tab-dashboard">📊 数据看板</button>
            <button class="page-tab" onclick="switchPage('issues')" id="tab-issues">📋 问题汇总 <span class="page-tab-badge">{len(D['m9_issues'])}</span></button>
            {f'''<button class="page-tab" onclick="switchPage('prices')" id="tab-prices">💰 价格分析 <span class="page-tab-badge">{len(D.get("price_analysis", []))}</span></button>''' if D.get('price_analysis') else ''}
            {'''<button class="page-tab" onclick="switchPage('history')" id="tab-history">📈 历史趋势</button>''' if H else ''}
        </div>
        <div class="mode-tabs" id="mode-tabs">
            <button class="mode-tab active" onclick="switchMode('report')">📋 汇报精简版</button>
            <button class="mode-tab" onclick="switchMode('analysis')">🔍 深度分析版</button>
        </div>
    </div>
</div>

<div class="container">

<!-- ===== PAGE: 数据看板 ===== -->
<div id="page-dashboard">

<!-- KPI Row -->
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">智能机累计销量</div>
        <div class="kpi-value">{fmt_n(M['total_smart_qty'])}</div>
        <div class="kpi-sub">月度目标 {fmt_n(M['total_target'])} | 完成率 <b style="color:{'#22c55e' if M['completion_rate']>=_time_prog else '#ef4444'}">{M['completion_rate']:.1f}%</b></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">手机总销量</div>
        <div class="kpi-value">{fmt_n(M['total_all_qty'])}</div>
        <div class="kpi-sub">智能机{fmt_n(M['total_smart_qty'])} + 功能机{fmt_n(M['total_feature_qty'])}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">累计营收</div>
        <div class="kpi-value" style="color:#22c55e">{fmt_naira(M['total_revenue'])}</div>
        <div class="kpi-sub">毛利 {fmt_naira(M['total_profit'])} | 毛利率 {M['total_profit']/M['total_revenue']*100:.1f}%</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">总缺口 / 日均需完成</div>
        <div class="kpi-value" style="color:#ef4444">{fmt_n(M['total_gap'])}</div>
        <div class="kpi-sub">剩余{M['remaining_days']:.0f}天需日均 <b style="color:#f59e0b">{M['daily_needed']:.0f}台</b></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">环比上月同期</div>
        <div class="kpi-value" style="color:{'#22c55e' if M['mom_change']>=0 else '#ef4444'}">{M['mom_change']:+.1f}%</div>
        <div class="kpi-sub">上月同期{fmt_n(M['may_smart_qty_15d'])}台 → 本月{fmt_n(M['total_smart_qty'])}台</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">日均智能机 / 门店数</div>
        <div class="kpi-value">{M['daily_avg_smart']:.0f}</div>
        <div class="kpi-sub">活跃门店{len(D['m1_store_target'])}家 | 日均目标{M['daily_needed']:.0f}台</div>
    </div>
</div>

<!-- ===== REPORT MODE ===== -->
<div id="mode-report">

<!-- M5 Trend (Report) -->
<div class="chart-row report-only">
    <div class="chart-box">
        <div class="chart-title">每日智能机销量趋势</div>
        <canvas id="chart_report_trend"></canvas>
    </div>
    <div class="chart-box">
        <div class="chart-title">全品牌销量 & 毛利率</div>
        <canvas id="chart_report_brand"></canvas>
    </div>
</div>

<!-- M5 Daily Summary (Report) -->
<div class="section report-only">
    <div class="section-header">
        <div class="section-title"><span class="num">5</span> 每日销量汇总</div>
    </div>
    <div class="section-body">
        <div class="tbl-wrap" style="max-height:350px">
            <table><thead><tr>
                <th>日期</th><th>智能机</th><th>功能机</th><th>合计</th>
                <th>营收</th><th>毛利</th><th>毛利率</th><th>上月同期</th>
            </tr></thead><tbody>{m5_rows()}</tbody></table>
        </div>
    </div>
</div>

<!-- 数据汇报 (Report) -->
<div class="section report-only">
    <div class="section-header">
        <div class="section-title"><span class="num">📋</span> 数据汇报</div>
    </div>
    <div class="section-body">
        <div class="report-summary">{data_report}</div>
    </div>
</div>

<!-- M8 Gap (Report) -->
<div class="summary-box report-only">
    <h3>🎯 月度追赶方案</h3>
    <p>{recovery_text}</p>
</div>

</div><!-- end report mode -->

<!-- ===== ANALYSIS MODE ===== -->
<div id="mode-analysis" style="display:none">

<!-- M1: Full Store Target Table -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">1</span> 各门店智能机月度任务完成度</div>
        <div style="font-size:11px;color:var(--text2)">点击表头排序</div>
    </div>
    <div class="section-body">
        <div class="tier-grid">{tier_cards()}</div>
        <div class="tbl-wrap" style="margin-top:12px">
            <table id="tbl_m1">
                <thead><tr>
                    <th onclick="sortTable('tbl_m1',0)">排名</th><th onclick="sortTable('tbl_m1',1)">门店</th>
                    <th onclick="sortTable('tbl_m1',2)">月度任务</th><th onclick="sortTable('tbl_m1',3)">累计智能机</th>
                    <th onclick="sortTable('tbl_m1',4)">完成率</th><th onclick="sortTable('tbl_m1',5)">剩余任务</th>
                    <th onclick="sortTable('tbl_m1',6)">日均需达成</th><th onclick="sortTable('tbl_m1',7)">环比</th>
                    <th>分层</th>
                </tr></thead>
                <tbody>{m1_rows()}</tbody>
            </table>
        </div>
    </div>
</div>

<!-- M2: Store Category -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">2</span> 各门店手机总销量 + 品类结构</div>
    </div>
    <div class="section-body">
        <div class="chart-row" style="margin-bottom:12px">
            <div class="chart-box">
                <div class="chart-title">全品类销量分布（饼图）</div>
                <canvas id="chart_cat_pie"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">全品类营收对比（条形图）</div>
                <canvas id="chart_cat_rev_bar"></canvas>
            </div>
        </div>
        <div class="alert-box alert-blue" style="margin-top:10px">
<b>品类结构分析：</b>{cat_items_text}。
TOP5门店贡献智能机{top5_pct:.0f}%，尾部10门店仅贡献{tail10_pct:.0f}%，头部门店虹吸效应明显。
        </div>
    </div>
</div>

<!-- M3: Brand Analysis -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">3</span> 全品牌销售结构分析</div>
    </div>
    <div class="section-body">
        <div class="chart-row" style="margin-bottom:12px">
            <div class="chart-box">
                <div class="chart-title">品牌销量分布</div>
                <canvas id="chart_brand_qty"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">品牌营收对比</div>
                <canvas id="chart_brand_rev"></canvas>
            </div>
        </div>
        <div class="tbl-wrap">
            <table id="tbl_m3">
                <thead><tr>
                    <th>排名</th><th>品牌</th><th>销量</th><th>占比</th><th>营收</th><th>毛利</th><th>平均单价</th><th>单机毛利</th><th>毛利率</th><th>环比</th>
                </tr></thead>
                <tbody>{m3_rows()}</tbody>
            </table>
        </div>
    </div>
</div>

<!-- M4: Daily Store Detail -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">4</span> 各门店最近一日销售明细（{M['period']}）</div>
    </div>
    <div class="section-body">
        <div class="tbl-wrap">
            <table id="tbl_m4">
                <thead><tr>
                    <th>门店</th><th>智能机</th><th>平板</th><th>功能机</th><th>合计</th>
                    <th>前日智能机</th><th>日目标</th><th>达标</th><th>环比变动</th>
                </tr></thead>
                <tbody>{m4_rows()}</tbody>
            </table>
        </div>
    </div>
</div>

<!-- M5: Company Daily Summary -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">5</span> 公司全局每日销售汇总</div>
    </div>
    <div class="section-body">
        <div class="chart-row" style="margin-bottom:12px">
            <div class="chart-box">
                <div class="chart-title">每日智能机 vs 上月同期</div>
                <canvas id="chart_m5_daily"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">每日营收趋势（百万₦）</div>
                <canvas id="chart_m5_rev"></canvas>
            </div>
        </div>
        <div class="tbl-wrap" style="margin-bottom:12px">
            <table id="tbl_m5">
                <thead><tr>
                    <th>日期</th><th>智能机</th><th>功能机</th><th>合计</th>
                    <th>营收</th><th>毛利</th><th>毛利率</th><th>上月同期</th>
                </tr></thead>
                <tbody>{m5_rows()}</tbody>
            </table>
        </div>
        <div class="alert-box alert-blue">
            <b>📈 趋势分析：</b>{trend_text}
            <br><b>渠道贡献：</b>TOP5门店贡献智能机{top5_pct:.0f}%，尾部10门店仅{tail10_pct:.0f}%。
            建议重点扶持中段门店，缩小头部与尾部差距。
        </div>
    </div>
</div>

{model_section_html}

<!-- M12: Store Daily Sales Volatility -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">12</span> 门店日销波动分析</div>
        <div style="font-size:11px;color:var(--muted)">CV变异系数越低 = 日销越稳定 · 趋势斜率反映增减方向 · 含上月同期CV对比</div>
    </div>
    <div class="section-body">
        <div class="kpi-row" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">
            {m12_kpi_cards()}
        </div>
        <div class="alert-box alert-blue" style="margin-bottom:12px">
            <b>📊 波动分析方法说明：</b><br>
            • <b>CV变异系数</b> = 标准差/均值，反映日销波动程度。≤25%稳定，25-40%正常，40-60%波动较大，>60%剧烈波动<br>
            • <b>趋势方向</b> = 线性回归斜率判断，↑上升/→平稳/↓下降<br>
            • <b>CV环比变化</b> = 本月CV - 上月同期CV，正值表示波动加剧，负值表示波动改善<br>
            • <b>零销量天数</b> = 营业日中智能机销量为0的天数，需排查运营异常
        </div>
        <div id="m12_filter_bar" style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
            <label style="font-size:13px;font-weight:600;color:var(--text)">选择门店查看日销波动明细：</label>
            <select id="m12_store_select" onchange="m12ShowDetail(this.value)" style="padding:6px 12px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:13px;min-width:200px;cursor:pointer">
                <option value="">— 选择门店 —</option>
            </select>
            <span id="m12_filter_hint" style="font-size:11px;color:var(--muted)"></span>
        </div>
        <div id="m12_detail_panel" style="display:none;margin-bottom:16px"></div>
        <div class="tbl-wrap" style="max-height:600px">
            <table id="tbl_m12"><thead><tr>
                <th>排名</th>
                <th onclick="m12Sort(1,'text')" class="m12-sortable">门店 <span class="m12-arrow" id="m12_arrow_1"></span></th>
                <th onclick="m12Sort(2,'num')" class="m12-sortable">日均<br>(台) <span class="m12-arrow" id="m12_arrow_2"></span></th>
                <th onclick="m12Sort(3,'num')" class="m12-sortable">CV<br>变异系数 <span class="m12-arrow" id="m12_arrow_3"></span></th>
                <th onclick="m12Sort(4,'num')" class="m12-sortable">标准差 <span class="m12-arrow" id="m12_arrow_4"></span></th>
                <th onclick="m12Sort(5,'num')" class="m12-sortable">最高<br>日销 <span class="m12-arrow" id="m12_arrow_5"></span></th>
                <th onclick="m12Sort(6,'num')" class="m12-sortable">最低<br>日销 <span class="m12-arrow" id="m12_arrow_6"></span></th>
                <th onclick="m12Sort(7,'num')" class="m12-sortable">零销<br>天数 <span class="m12-arrow" id="m12_arrow_7"></span></th>
                <th onclick="m12Sort(8,'num')" class="m12-sortable">趋势<br>方向 <span class="m12-arrow" id="m12_arrow_8"></span></th>
                <th onclick="m12Sort(9,'num')" class="m12-sortable">CV环比<br>变化 <span class="m12-arrow" id="m12_arrow_9"></span></th>
                <th onclick="m12Sort(10,'num')" class="m12-sortable">波动<br>评级 <span class="m12-arrow" id="m12_arrow_10"></span></th>
                <th>日销<br>趋势</th>
            </tr></thead><tbody>{m12_rows()}</tbody></table>
        </div>
    </div>
</div>

<!-- M6: Inventory -->
<div class="section analysis-only" style="background:transparent">
    <div class="section-header">
        <div class="section-title"><span class="num">6</span> 门店库存周转 & 风险预警</div>
    </div>
    <div class="section-body">
        {m6_turnover_kpi()}
        <div class="sub-tabs">
            <button class="sub-tab active" onclick="showInvTab('brand',this)">📈 品牌周转</button>
            <button class="sub-tab" onclick="showInvTab('model',this)">📱 型号周转</button>
            <button class="sub-tab" onclick="showInvTab('turnover',this)">📊 门店周转天数</button>
            <button class="sub-tab" onclick="showInvTab('store-model',this)">🔍 单店型号周转</button>
            <button class="sub-tab" onclick="showInvTab('overstock',this)">🔴 门店滞销积压</button>
            <button class="sub-tab" onclick="showInvTab('lowstock',this)">🟡 缺货预警</button>
            <button class="sub-tab" onclick="showInvTab('general',this)">🟠 总仓死库</button>
            <button class="sub-tab" onclick="showInvTab('cost',this)">💰 商品成本查询</button>
        </div>
        <div id="inv-brand" class="inv-sub">
            <h4>各品牌库存周转天数排名（门店总可卖数 ÷ 日均销量，手机+平板，不含总仓）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>排名</th><th>品牌</th><th>门店可卖数</th><th>总仓可卖数</th><th>日均销量</th><th>周转天数</th><th>评级</th>
            </tr></thead><tbody>{m6_brand_turnover_rows()}</tbody></table></div>
        </div>
        <div id="inv-model" class="inv-sub" style="display:none">
            <h4>型号库存周转天数排名（所有门店仓可卖数 ÷ 日均销量，按日销降序，手机+平板）</h4>
            <div style="margin-bottom:10px;display:flex;align-items:center;gap:8px">
                <label style="color:var(--text2);font-size:12px">品牌筛选：</label>
                <select id="model-brand-filter" onchange="filterModelTurnover()" style="padding:6px 10px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:12px">
                    <option value="">全部品牌</option>
                </select>
            </div>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>排名</th><th>品牌</th><th>型号</th><th>门店总可卖数</th><th>在途</th><th>当月日销</th><th>周转天数</th><th>评级</th><th>资金占用</th>
            </tr></thead><tbody>{m6_model_turnover_rows()}</tbody></table></div>
        </div>
        <div id="inv-turnover" class="inv-sub" style="display:none">
            <h4>各门店库存周转天数排名（门店总可卖数 ÷ 日均销量，手机+平板，不含总仓）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>排名</th><th>门店</th><th>库存总数</th><th>日均销量</th><th>周转天数</th><th>评级</th><th>建议</th>
            </tr></thead><tbody>{m6_turnover_rows()}</tbody></table></div>
        </div>
        <div id="inv-store-model" class="inv-sub" style="display:none">
            <h4>单店型号库存周转（手机+平板，按销量降序，不含总仓）</h4>
            <div style="margin-bottom:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <label style="color:var(--text2);font-size:12px">门店：</label>
                <div style="position:relative">
                    <button id="store-combo-btn" onclick="toggleStoreCombo()"
                     style="padding:6px 30px 6px 10px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:12px;cursor:pointer;text-align:left;min-width:180px;position:relative">
                        选择门店 ▾
                    </button>
                    <div id="store-combo-dropdown" style="display:none;position:absolute;top:100%;left:0;width:280px;background:#1e293b;border:1px solid #334155;border-radius:6px;z-index:1000;margin-top:2px;box-shadow:0 8px 24px rgba(0,0,0,0.5)">
                        <div style="padding:6px 8px;border-bottom:1px solid #334155">
                            <input type="text" id="store-combo-search" placeholder="输入门店名搜索..."
                             style="width:100%;padding:6px 10px;border-radius:4px;border:1px solid #475569;background:#0f172a;color:#e2e8f0;font-size:12px;box-sizing:border-box"
                             oninput="filterStoreCombo()" onkeydown="handleComboKey(event)" onclick="event.stopPropagation()">
                        </div>
                        <div id="store-combo-list" style="max-height:350px;overflow-y:auto"></div>
                    </div>
                </div>
                <input type="hidden" id="store-select" value="">
                <label style="color:var(--text2);font-size:12px">品类：</label>
                <select id="sm-cat-filter" onchange="filterStoreModels()" style="padding:6px 10px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:12px">
                    <option value="">全部品类</option>
                    <option value="手机">手机</option>
                    <option value="平板">平板</option>
                </select>
                <label style="color:var(--text2);font-size:12px">品牌：</label>
                <select id="sm-brand-filter" onchange="filterStoreModels()" style="padding:6px 10px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:12px">
                    <option value="">全部品牌</option>
                </select>
            </div>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>排名</th><th>品类</th><th>品牌</th><th>型号</th><th>可卖数</th><th>在途</th><th>当月销量</th><th>周转天数</th><th>总仓库存</th><th>评级</th><th>预警/建议</th><th>资金占用</th>
            </tr></thead><tbody id="store-model-tbody"></tbody></table></div>
        </div>
        <div id="inv-overstock" class="inv-sub" style="display:none">
            <h4>门店滞销积压机型（有库存但全公司月销量为零）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>门店</th><th>品牌</th><th>型号</th><th>库存</th><th>资金占用</th><th>建议</th>
            </tr></thead><tbody>{m6_overstock_rows()}</tbody></table></div>
        </div>
        <div id="inv-lowstock" class="inv-sub" style="display:none">
            <h4>热门品牌缺货预警（库存≤3台 或 周转天数<4天，且全公司月销量>0）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>门店</th><th>品牌</th><th>型号</th><th>门店库存</th><th>周转天数</th><th>总仓库存</th><th>全公司月销</th><th>建议</th>
            </tr></thead><tbody>{m6_lowstock_rows()}</tbody></table></div>
        </div>
        <div id="inv-general" class="inv-sub" style="display:none">
            <h4>总仓死库（GENERAL-PHONES，有库存但全公司月销量为零）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>品牌</th><th>型号</th><th>库存</th><th>资金占用</th><th>建议</th>
            </tr></thead><tbody>{m6_general_rows()}</tbody></table></div>
        </div>
        <div id="inv-cost" class="inv-sub" style="display:none">
            <h4>商品成本价查询（按批次进货成本，加权均价 = Σ(结存×单价) ÷ 总结存）</h4>
            <div style="margin-bottom:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                <input type="text" id="cost-search" placeholder="输入型号名称搜索..." oninput="filterCostTable()" style="flex:1;min-width:220px;padding:8px 12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:13px">
                <select id="cost-brand-filter" onchange="filterCostTable()" style="padding:8px 12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:13px">
                    <option value="">全部品牌</option>
                </select>
                <span id="cost-result-count" style="color:var(--text2);font-size:12px"></span>
            </div>
            <div class="tbl-wrap"><table class="m6-table" id="cost-table"><thead><tr>
                <th onclick="sortTable('cost-table',0)">品牌</th>
                <th onclick="sortTable('cost-table',1)">型号</th>
                <th onclick="sortTable('cost-table',2)">品类</th>
                <th onclick="sortTable('cost-table',3)">总结存</th>
                <th onclick="sortTable('cost-table',4)">批次数</th>
                <th onclick="sortTable('cost-table',5)">加权均价 ₦</th>
                <th onclick="sortTable('cost-table',6)">最低价 ₦</th>
                <th onclick="sortTable('cost-table',7)">最高价 ₦</th>
                <th onclick="sortTable('cost-table',8)">成本差 ₦</th>
                <th onclick="sortTable('cost-table',9)">库存成本总额 ₦</th>
                <th>批次明细</th>
            </tr></thead><tbody id="cost-tbody"></tbody></table></div>
        </div>
        {m6_store_model_js()}
    </div>
</div>

<!-- M7: People Efficiency -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">7</span> 门店人效 & 业绩诊断</div>
        <div style="font-size:11px;color:var(--text2)">全公司{D.get('m7_staff',{}).get('total_staff','-')}名营业员 · 人均智能机{D.get('m7_staff',{}).get('co_avg_smart','-')}台</div>
    </div>
    <div class="section-body">
        <div class="kpi-row" style="margin-bottom:12px">
            <div class="kpi-card">
                <div class="kpi-label">营业员总数</div>
                <div class="kpi-value">{D.get('m7_staff',{}).get('total_staff','-')}</div>
                <div class="kpi-sub">覆盖 {len(D.get('m7_staff',{}).get('store_efficiency',[]))} 家门店</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">人均智能机销量</div>
                <div class="kpi-value">{D.get('m7_staff',{}).get('co_avg_smart','-')}</div>
                <div class="kpi-sub">台/人（{M['elapsed_days']}天累计）</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">人均总销量</div>
                <div class="kpi-value">{D.get('m7_staff',{}).get('co_avg_total','-')}</div>
                <div class="kpi-sub">含功能机 · 台/人</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">人均毛利贡献</div>
                <div class="kpi-value" style="color:#22c55e">₦{D.get('m7_staff',{}).get('co_avg_profit',0)/1e3:.0f}K</div>
                <div class="kpi-sub">全品类 · {M['elapsed_days']}天累计</div>
            </div>
        </div>
        <div class="sub-tabs">
            <button class="sub-tab active" onclick="showEffTab('store',this)">🏪 门店人效排名</button>
            <button class="sub-tab" onclick="showEffTab('top',this)">🏆 TOP营业员</button>
            <button class="sub-tab" onclick="showEffTab('bottom',this)">⚠️ 尾部营业员</button>
        </div>
        <div id="eff-store">
            <div class="tbl-wrap" style="max-height:400px">
                <table id="tbl_m7"><thead><tr>
                    <th>排名</th><th>门店</th><th>人数</th><th>人均智能机</th><th>人均总销量</th><th>人均毛利</th><th>绩效分层</th><th>TOP营业员</th>
                </tr></thead><tbody>{m7_store_rows()}</tbody></table>
            </div>
        </div>
        <div id="eff-top" style="display:none">
            <div class="tbl-wrap" style="max-height:400px">
                <table><thead><tr>
                    <th>排名</th><th>营业员</th><th>智能机销量</th><th>营收</th><th>毛利率</th>
                </tr></thead><tbody>{m7_top_sp_rows()}</tbody></table>
            </div>
        </div>
        <div id="eff-bottom" style="display:none">
            <div class="tbl-wrap" style="max-height:400px">
                <table><thead><tr>
                    <th>排名</th><th>营业员</th><th>智能机销量</th><th>营收</th><th>毛利率</th>
                </tr></thead><tbody>{m7_bottom_sp_rows()}</tbody></table>
            </div>
        </div>
    </div>
</div>

<!-- M8: Gap Recovery -->
<div class="section analysis-only">
    <div class="section-header">
        <div class="section-title"><span class="num">8</span> 月度任务缺口追赶方案</div>
    </div>
    <div class="section-body">
        <div class="summary-box" style="margin-bottom:12px">
            <h3>🎯 追赶方案</h3>
            <p>{recovery_text}</p>
        </div>
        <div class="alert-box alert-blue">
            <b>具体动作建议：</b><br>
            1. <b>加大爆款主推：</b>TECNO/INFINIX占销量60%+，确保各门店主推机型库存充足、导购话术到位<br>
            2. <b>滞销清库：</b>INFINIX HOT 70等滞销机型（总仓524台）需立即启动促销清库，释放资金<br>
            3. <b>严重滞后门店帮扶：</b>16家严重滞后门店安排区域经理驻店，分析原因（客流/人员/备货）<br>
            4. <b>缺货补位：</b>INFINIX SMART20多门店库存不足，优先调拨至高产出门店
        </div>
        <div class="tbl-wrap" style="margin-top:12px">
            <table><thead><tr>
                <th>门店</th><th>任务</th><th>已完成</th><th>完成率</th><th>缺口</th><th>日均需达成</th><th>环比</th>
            </tr></thead><tbody>{m8_rows()}</tbody></table></div>
    </div>
</div>


</div><!-- end analysis mode -->

</div><!-- end page-dashboard -->

<!-- ===== PAGE: 问题汇总 ===== -->
<div id="page-issues" style="display:none">

<div class="section">
    <div class="section-header">
        <div class="section-title"><span class="num">9</span> 每日问题汇总 + 行动待办清单</div>
        <div style="font-size:11px;color:var(--red);font-weight:600">共{len(D['m9_issues'])}条异常</div>
    </div>
    <div class="section-body">
        <div class="tbl-wrap" style="max-height:none">
            <table><thead><tr>
                <th>类型</th><th>对象</th><th>详情</th><th>改善建议</th>
            </tr></thead><tbody>{m9_rows()}</tbody></table></div>
    </div>
</div>

</div><!-- end page-issues -->

<!-- ===== PAGE: 价格分析 ===== -->"""
if D.get('price_analysis') and D.get('price_summary'):
    ps = D['price_summary']
    pa = D['price_analysis']
    # Price analysis page tabs
    price_increases = [r for r in pa if r['diff'] > 0]
    price_decreases = [r for r in pa if r['diff'] < 0]
    promo_changes = [r for r in pa if not r['price_changed'] and r['promo_change'] != 'no_change']
    # Build price change rows
    price_rows = ''
    for i, r in enumerate(pa):
        # Determine promo status display
        promo_tag = ''
        if r['promo_change'] == 'new_promo':
            promo_tag = '<span style="background:#22c55e20;color:#22c55e;padding:1px 6px;border-radius:4px;font-size:10px;margin-left:4px">新促销</span>'
        elif r['promo_change'] == 'ended_promo':
            promo_tag = '<span style="background:#ef444420;color:#ef4444;padding:1px 6px;border-radius:4px;font-size:10px;margin-left:4px">促销结束</span>'
        elif r['promo_change'] == 'promo_price_changed':
            promo_tag = '<span style="background:#f59e0b20;color:#f59e0b;padding:1px 6px;border-radius:4px;font-size:10px;margin-left:4px">促销价变动</span>'
        # Price source display
        cur_src_tag = '<span style="font-size:10px;color:var(--text2)">' + r['cur_source'] + '</span>'
        cmp_src_tag = '<span style="font-size:10px;color:var(--text2)">' + r['cmp_source'] + '</span>'
        # Sales impact display
        sales_tag = ''
        if r.get('june_sales_qty'):
            sales_tag = f'<span style="font-size:10px;color:var(--text2)">{r["june_sales_qty"]}台</span>'
            if r.get('mom_sales_change'):
                mc = r['mom_sales_change']
                sales_tag += f' <span style="font-size:10px;color:{'#22c55e' if mc>0 else '#ef4444' if mc<0 else 'var(--text2)'}">环比{mc}%</span>'
        elif r.get('june_daily_avg'):
            sales_tag = f'<span style="font-size:10px;color:var(--text2)">日均{r["june_daily_avg"]}台</span>'
        # Price change direction arrow
        direction = '↑' if r['diff'] > 0 else '↓' if r['diff'] < 0 else '→'
        direction_color = '#ef4444' if r['diff'] > 0 else '#22c55e' if r['diff'] < 0 else 'var(--text2)'
        # Current price details (show promo vs regular)
        price_detail_cur = ''
        if r.get('cur_promo_price') and r.get('cur_rrp_vat'):
            price_detail_cur = f'<div style="font-size:10px;color:#f59e0b">促销 ₦{int(r["cur_promo_price"]):,}</div><div style="font-size:10px;color:var(--text2)">原价 ₦{int(r["cur_rrp_vat"]):,}</div>'
        elif r.get('cur_promo_price'):
            price_detail_cur = f'<div style="font-size:10px;color:#f59e0b">促销 ₦{int(r["cur_promo_price"]):,}</div>'
        elif r.get('cur_rrp_vat'):
            price_detail_cur = f'<div>₦{int(r["cur_price"]):,}</div>'
        else:
            price_detail_cur = f'<div>₦{int(r["cur_price"]):,}</div>' if r.get('cur_price') else '<div>-</div>'
        # Compare price details
        price_detail_cmp = ''
        if r.get('cmp_promo_price') and r.get('cmp_rrp_vat'):
            price_detail_cmp = f'<div style="font-size:10px;color:#f59e0b">促销 ₦{int(r["cmp_promo_price"]):,}</div><div style="font-size:10px;color:var(--text2)">原价 ₦{int(r["cmp_rrp_vat"]):,}</div>'
        elif r.get('cmp_promo_price'):
            price_detail_cmp = f'<div style="font-size:10px;color:#f59e0b">促销 ₦{int(r["cmp_promo_price"]):,}</div>'
        elif r.get('cmp_rrp_vat'):
            price_detail_cmp = f'<div>₦{int(r["cmp_price"]):,}</div>'
        else:
            price_detail_cmp = f'<div>₦{int(r["cmp_price"]):,}</div>' if r.get('cmp_price') else '<div>-</div>'
        price_rows += f'''<tr data-type="{('increase' if r['diff']>0 else 'decrease' if r['diff']<0 else 'promo')}" data-brand="{r['brand']}">
            <td>{i+1}</td>
            <td>{r['brand']}</td>
            <td style="text-align:left;max-width:200px;overflow:hidden;text-overflow:ellipsis">{r['model'][:40]}{promo_tag}</td>
            <td>{price_detail_cmp}</td>
            <td>{price_detail_cur}</td>
            <td style="color:{direction_color};font-weight:700">{direction} {abs(r['pct'])}%</td>
            <td style="color:{direction_color}">₦{abs(int(r['diff'])):,}</td>
            <td>{sales_tag}</td>
        </tr>'''

    price_page_html = f"""
<div id="page-prices" style="display:none">

<div style="padding:0 0 12px 0">
    <button onclick="switchPage('dashboard')" style="padding:6px 16px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);font-size:12px;cursor:pointer;">← 返回数据看板</button>
</div>

<div class="section">
    <div class="section-header">
        <div class="section-title"><span class="num">10</span> 价格变动分析（{_price_cmp_label} vs {_price_curr_label}）</div>
        <div style="font-size:11px;color:var(--text2)">{_price_cmp_label}价格表 vs {_price_curr_label}价格表</div>
    </div>
    <div class="section-body">
        <!-- KPI Cards -->
        <div class="kpi-row" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
            <div class="kpi-card">
                <div class="kpi-label">价格变动型号</div>
                <div class="kpi-value" style="color:var(--blue)">{ps.get('total_price_changes', 0)}</div>
                <div class="kpi-sub">/ {ps.get('total_matched', 0)} 在售型号</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">涨价型号</div>
                <div class="kpi-value" style="color:#ef4444">{ps.get('price_increases', 0)}</div>
                <div class="kpi-sub">↑ 平均涨幅</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">降价型号</div>
                <div class="kpi-value" style="color:#22c55e">{ps.get('price_decreases', 0)}</div>
                <div class="kpi-sub">↓ 平均降幅</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">新促销启动</div>
                <div class="kpi-value" style="color:#f59e0b">{ps.get('new_promos', 0)}</div>
                <div class="kpi-sub">5月无促销→6月有促销</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">促销结束</div>
                <div class="kpi-value" style="color:#94a3b8">{ps.get('ended_promos', 0)}</div>
                <div class="kpi-sub">5月有促销→6月无促销</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">新增型号</div>
                <div class="kpi-value" style="color:#22c55e">{ps.get('new_models_count', 0)}</div>
                <div class="kpi-sub">6月新增上架</div>
            </div>
        </div>

        <!-- Filter bar -->
        <div style="display:flex;gap:8px;margin:12px 0;flex-wrap:wrap;align-items:center">
            <span style="color:var(--text2);font-size:11px">筛选：</span>
            <button onclick="priceFilter('all')" id="pf-all" class="pf-btn active" style="padding:4px 12px;border-radius:4px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:var(--text)">全部 ({len(pa)})</button>
            <button onclick="priceFilter('increase')" id="pf-increase" class="pf-btn" style="padding:4px 12px;border-radius:4px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:#ef4444;background:transparent">涨价 ({len(price_increases)})</button>
            <button onclick="priceFilter('decrease')" id="pf-decrease" class="pf-btn" style="padding:4px 12px;border-radius:4px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:#22c55e;background:transparent">降价 ({len(price_decreases)})</button>
            <button onclick="priceFilter('promo')" id="pf-promo" class="pf-btn" style="padding:4px 12px;border-radius:4px;font-size:11px;cursor:pointer;border:1px solid var(--border);color:#f59e0b;background:transparent">促销变化 ({len(promo_changes)})</button>
        </div>

        <!-- Price change table -->
        <div class="tbl-wrap" style="max-height:none">
            <table id="price-table"><thead><tr>
                <th>#</th>
                <th>品牌</th>
                <th style="text-align:left">型号</th>
                <th>{_price_cmp_label}价格</th>
                <th>{_price_curr_label}价格</th>
                <th>变动幅度</th>
                <th>变动金额</th>
                <th>销量影响</th>
            </tr></thead><tbody id="price-tbody">{price_rows}</tbody></table>
        </div>

        <!-- Price change impact summary -->
        <div style="margin-top:16px;padding:12px;background:var(--surface2);border-radius:8px;font-size:12px;color:var(--text2)">
            <b style="color:var(--text)">💡 价格分析要点：</b><br>
            <span>• 促销价优先级：促销价 > 含税零售价 > 3CHUB价</span><br>
            <span>• 涨价型号需关注销量环比变化（是否因涨价导致销量下滑）</span><br>
            <span>• 降价/新促销型号需关注销量环比增长（是否因促销拉动销量）</span>
        </div>
    </div>
</div>

</div><!-- end page-prices -->
"""
else:
    price_page_html = ''

html += f"""

{price_page_html}

{history_page_html}

<script>
// Data
const D = {json.dumps(D, ensure_ascii=False)};
const isDark = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim().startsWith('#0') || getComputedStyle(document.documentElement).getPropertyValue('--bg').trim().startsWith('#1');

// Mode switch
function switchMode(mode) {{
    document.querySelectorAll('.mode-tab').forEach((t,i) => t.classList.toggle('active', (mode==='report'?i===0:i===1)));
    document.getElementById('mode-report').style.display = mode==='report'?'block':'none';
    document.getElementById('mode-analysis').style.display = mode==='analysis'?'block':'none';
    // Hide page-tabs (问题汇总) in report mode; show in analysis mode
    document.getElementById('page-tabs').style.display = mode==='report'?'none':'flex';
    // In report mode, always show dashboard page
    if(mode==='report') {{
        switchPage('dashboard');
    }}
    if(mode==='analysis') {{
        if(!window._analysisChartsInit) {{
            setTimeout(() => {{
                initAnalysisCharts();
                window._analysisChartsInit = true;
            }}, 50);
        }} else {{
            setTimeout(() => {{
                Chart.helpers.each(Chart.instances, c => c.resize());
            }}, 50);
        }}
    }}
}}

// Page switch (dashboard / issues)
function switchPage(page) {{
    document.querySelectorAll('.page-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-'+page).classList.add('active');
    document.getElementById('page-dashboard').style.display = page==='dashboard'?'block':'none';
    document.getElementById('page-issues').style.display = page==='issues'?'block':'none';
    {'''document.getElementById('page-prices').style.display = page==='prices'?'block':'none';''' if D.get('price_analysis') else ''}
    {'''document.getElementById('page-history').style.display = page==='history'?'block':'none';''' if H else ''}
    document.getElementById('mode-tabs').style.display = page==='dashboard'?'flex':'none';
    if(page==='dashboard') {{
        window._analysisChartsInit = false;
    }}
    {'''if(page==='history' && !window._historyChartsInit) {{
        setTimeout(() => {{ initHistoryCharts(); window._historyChartsInit = true; }}, 50);
    }}''' if H else ''}
}}

// Price analysis filter
function priceFilter(type) {{
    document.querySelectorAll('.pf-btn').forEach(b => {{
        b.classList.remove('active');
        b.style.background = 'transparent';
    }});
    const activeBtn = document.getElementById('pf-'+type);
    if (activeBtn) {{
        activeBtn.classList.add('active');
        activeBtn.style.background = 'var(--surface2)';
    }}
    const rows = document.querySelectorAll('#price-tbody tr');
    rows.forEach(r => {{
        const rType = r.dataset.type;
        r.style.display = (type==='all' || rType===type) ? '' : 'none';
    }});
}}

// Inventory sub-tabs
function showInvTab(name, btn) {{
    document.querySelectorAll('.inv-sub').forEach(d => d.style.display='none');
    document.getElementById('inv-'+name).style.display='block';
    document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    if (name === 'cost') initCostTable();
}}

// ===== Cost Query =====
const COST_DATA = {json.dumps(D.get('cost_data', []), ensure_ascii=False)};
let costExpandedRows = {{}};

function initCostTable() {{
    if (document.getElementById('cost-brand-filter').options.length > 1) return; // Already initialized
    const brands = [...new Set(COST_DATA.map(r => r.brand).filter(Boolean))].sort();
    const sel = document.getElementById('cost-brand-filter');
    brands.forEach(b => {{ const o = document.createElement('option'); o.value = b; o.textContent = b; sel.appendChild(o); }});
    filterCostTable();
}}

function filterCostTable() {{
    const q = document.getElementById('cost-search').value.toLowerCase();
    const brand = document.getElementById('cost-brand-filter').value;
    const tbody = document.getElementById('cost-tbody');
    costExpandedRows = {{}};
    let html = '';
    let count = 0;
    COST_DATA.forEach((r, i) => {{
        if (brand && r.brand !== brand) return;
        const matchModel = r.model.toLowerCase().includes(q);
        const matchBrand = r.brand.toLowerCase().includes(q);
        if (!matchModel && !matchBrand) return;
        count++;
        const rowId = 'cost-row-' + i;
        const costSpread = r.cost_spread;
        const spreadColor = costSpread > 10000 ? '#ef4444' : costSpread > 1000 ? '#f59e0b' : '#22c55e';
        html += '<tr id="'+rowId+'" onclick="toggleCostDetail(\\''+rowId+'\\','+i+')" style="cursor:pointer;transition:background .2s" onmouseover="this.style.background=\\'#1e293b\\'" onmouseout="this.style.background=\\'\\'">';
        html += '<td>'+r.brand+'</td>';
        html += '<td class="model-name">'+r.model+'</td>';
        html += '<td style="font-size:11px;color:var(--text2)">'+r.category+'</td>';
        html += '<td style="font-weight:700">'+r.total_stock.toLocaleString()+'</td>';
        html += '<td>'+r.batch_count+'</td>';
        html += '<td style="color:#3b82f6;font-weight:700">₦'+r.weighted_avg_cost_tax.toLocaleString()+'</td>';
        html += '<td style="color:#22c55e">₦'+r.min_cost_tax.toLocaleString()+'</td>';
        html += '<td style="color:#ef4444">₦'+r.max_cost_tax.toLocaleString()+'</td>';
        html += '<td style="color:'+spreadColor+';font-weight:600">₦'+costSpread.toLocaleString()+'</td>';
        html += '<td style="color:#a78bfa;font-weight:600">₦'+r.total_cost_value.toLocaleString()+'</td>';
        html += '<td><span style="font-size:11px;color:var(--text2)">▼ 查看批次</span></td>';
        html += '</tr>';
    }});
    tbody.innerHTML = html;
    document.getElementById('cost-result-count').textContent = '共 '+count+' 条';
}}

function toggleCostDetail(rowId, idx) {{
    const row = document.getElementById(rowId);
    const detailId = rowId + '-detail';
    const existing = document.getElementById(detailId);
    if (existing) {{ existing.remove(); return; }}
    const r = COST_DATA[idx];
    let detailHtml = '<tr id="'+detailId+'" style="background:#1e293b"><td colspan="11" style="padding:12px 20px">';
    detailHtml += '<div style="font-weight:700;margin-bottom:8px;color:#3b82f6">📦 '+r.model+' 批次进货明细</div>';
    detailHtml += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
    detailHtml += '<thead><tr style="border-bottom:1px solid #334155;color:var(--text2)">';
    detailHtml += '<th style="padding:6px 8px;text-align:left">进货日期</th>';
    detailHtml += '<th style="padding:6px 8px;text-align:right">含税单价 ₦</th>';
    detailHtml += '<th style="padding:6px 8px;text-align:right">无税单价 ₦</th>';
    detailHtml += '<th style="padding:6px 8px;text-align:right">结存数量</th>';
    detailHtml += '<th style="padding:6px 8px;text-align:right">库龄天数</th>';
    detailHtml += '<th style="padding:6px 8px;text-align:right">汇率</th>';
    detailHtml += '<th style="padding:6px 8px;text-align:right">结存金额 ₦</th>';
    detailHtml += '</tr></thead><tbody>';
    r.batches.forEach(b => {{
        const stockVal = b.stock * b.unit_cost_tax;
        const agingColor = b.aging_days > 180 ? '#ef4444' : b.aging_days > 90 ? '#f59e0b' : '#22c55e';
        detailHtml += '<tr style="border-bottom:1px solid #1e293b">';
        detailHtml += '<td style="padding:6px 8px">'+b.date+'</td>';
        detailHtml += '<td style="padding:6px 8px;text-align:right;font-weight:600">₦'+b.unit_cost_tax.toLocaleString()+'</td>';
        detailHtml += '<td style="padding:6px 8px;text-align:right;color:var(--text2)">₦'+b.unit_cost_notax.toLocaleString()+'</td>';
        detailHtml += '<td style="padding:6px 8px;text-align:right;font-weight:700">'+(b.stock||0)+'</td>';
        detailHtml += '<td style="padding:6px 8px;text-align:right;color:'+agingColor+'">'+b.aging_days+'天</td>';
        detailHtml += '<td style="padding:6px 8px;text-align:right;color:var(--text2)">'+b.rate+'</td>';
        detailHtml += '<td style="padding:6px 8px;text-align:right;color:#a78bfa;font-weight:600">₦'+stockVal.toLocaleString()+'</td>';
        detailHtml += '</tr>';
    }});
    detailHtml += '</tbody></table>';
    // Cost summary box
    detailHtml += '<div style="margin-top:10px;padding:10px;background:#0f172a;border-radius:8px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px">';
    detailHtml += '<span>📊 <b>加权均价：</b><span style="color:#3b82f6">₦'+r.weighted_avg_cost_tax.toLocaleString()+'</span></span>';
    detailHtml += '<span>📉 <b>最低进价：</b><span style="color:#22c55e">₦'+r.min_cost_tax.toLocaleString()+'</span></span>';
    detailHtml += '<span>📈 <b>最高进价：</b><span style="color:#ef4444">₦'+r.max_cost_tax.toLocaleString()+'</span></span>';
    detailHtml += '<span>💰 <b>库存总成本：</b><span style="color:#a78bfa">₦'+r.total_cost_value.toLocaleString()+'</span></span>';
    detailHtml += '</div>';
    detailHtml += '</td></tr>';
    row.insertAdjacentHTML('afterend', detailHtml);
}}

// Staff efficiency sub-tabs
function showEffTab(name, btn) {{
    document.getElementById('eff-store').style.display = name==='store'?'block':'none';
    document.getElementById('eff-top').style.display = name==='top'?'block':'none';
    document.getElementById('eff-bottom').style.display = name==='bottom'?'block':'none';
    // Only deselect sub-tabs within the M7 section
    const parent = btn.parentElement;
    parent.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
}}

// Sort table
function sortTable(id, col) {{
    const table = document.getElementById(id);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const asc = table.dataset.sortCol == col ? !table.dataset.sortAsc : true;
    table.dataset.sortCol = col;
    table.dataset.sortAsc = asc;
    rows.sort((a,b) => {{
        let va = a.cells[col].innerText.replace(/[^\\d.\\-]/g,'');
        let vb = b.cells[col].innerText.replace(/[^\\d.\\-]/g,'');
        return asc ? (parseFloat(va)||0) - (parseFloat(vb)||0) : (parseFloat(vb)||0) - (parseFloat(va)||0);
    }});
    rows.forEach(r => tbody.appendChild(r));
    m10CurrentPage = 1;
    m10UpdatePagination();
}}

// Chart defaults
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';
Chart.defaults.font.size = 11;
Chart.register(ChartDataLabels);

// Datalabels default: show values on all charts
const DL_DEFAULTS = {{
    color: '#cbd5e1',
    font: {{ size: 10, weight: 'bold' }},
    anchor: 'end',
    align: 'top',
    offset: 2
}};

function makeBarDl(display) {{
    return {{ ...DL_DEFAULTS, display: function(ctx) {{ return display !== false && ctx.dataset.data[ctx.dataIndex] > 0; }} }};
}}
function makeLineDl(display) {{
    return {{ ...DL_DEFAULTS, anchor:'end', align:'top', offset:4,
        font: {{ size: 9, weight: 'bold' }},
        display: function(ctx) {{ return display !== false; }} }};
}}
function makeHBarDl(display) {{
    return {{ ...DL_DEFAULTS, anchor:'end', align:'right', display: function(ctx) {{ return display !== false && ctx.dataset.data[ctx.dataIndex] > 0; }} }};
}}

function initReportCharts() {{
    // Report trend
    new Chart(document.getElementById('chart_report_trend'), {{
        type:'line',
        data:{{
            labels:{daily_labels},
            datasets:[
                {{label:'本月智能机',data:{daily_sq},borderColor:'#3b82f6',backgroundColor:'#3b82f622',fill:true,tension:.3}},
                {{label:'上月同期',data:{daily_may},borderColor:'#64748b',borderDash:[5,5],tension:.3,pointRadius:2}}
            ]
        }},
        options:{{responsive:true,plugins:{{legend:{{position:'bottom'}},datalabels:makeLineDl()}}}}
    }});
    // Report brand (dual axis: bar=quantity, line=profit rate)
    new Chart(document.getElementById('chart_report_brand'), {{
        type:'bar',
        data:{report_brand_data}
        options:{{responsive:true,plugins:{{legend:{{position:'bottom',labels:{{color:'#94a3b8',usePointStyle:true,padding:20}}}}}},scales:{{y:{{beginAtZero:true,grid:{{color:'rgba(51,65,85,0.35)',lineWidth:0.5}},ticks:{{color:'#94a3b8'}},title:{{text:'销量',display:true,color:'#94a3b8'}}}},y1:{{position:'right',beginAtZero:true,grid:{{display:false}},ticks:{{color:'#a78bfa',callback:v=>v+'%'}},title:{{text:'毛利率',display:true,color:'#a78bfa'}}}},x:{{grid:{{color:'rgba(51,65,85,0.35)',lineWidth:0.5}},ticks:{{color:'#94a3b8'}}}}}}}}
    }});
}}

function initAnalysisCharts() {{
    // M2 Category pie
    const catTotal = {int(cat_total)};
    new Chart(document.getElementById('chart_cat_pie'), {{
        type:'doughnut',
        data:{cat_pie_data_js}
        options:{{responsive:true,plugins:{{legend:{{position:'bottom'}},datalabels:{{color:'#fff',font:{{size:11,weight:'bold'}},formatter:(v,ctx)=>{{const pct=(v/catTotal*100);return pct>=3?pct.toFixed(1)+'%':'';}}}}}}}}
    }});

    // M2 Category revenue bar
    new Chart(document.getElementById('chart_cat_rev_bar'), {{
        type:'bar',
        data:{cat_rev_bar_js}
        options:{{responsive:true,plugins:{{legend:{{display:false}},datalabels:makeBarDl()}}}}
    }});

    // M3 brand qty
    new Chart(document.getElementById('chart_brand_qty'), {{
        type:'bar',
        data:{brand_qty_data_js},
        options:{{responsive:true,plugins:{{legend:{{position:'bottom'}},datalabels:makeBarDl()}}}}
    }});

    // M3 brand revenue + profit
    new Chart(document.getElementById('chart_brand_rev'), {{
        type:'bar',
        data:{brand_rev_data_js}
        options:{{responsive:true,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12}}}},datalabels:makeBarDl()}}}}
    }});

    // M5 daily smart vs may
    new Chart(document.getElementById('chart_m5_daily'), {{
        type:'line',
        data:{{
            labels:{m5_labels},
            datasets:[
                {{label:'本月智能机',data:{m5_sq},borderColor:'#3b82f6',backgroundColor:'#3b82f622',fill:true,tension:.3}},
                {{label:'上月同期',data:{json.dumps([r['may_smart'] for r in D['m5_company_daily']])},borderColor:'#64748b',borderDash:[5,5],tension:.3}}
            ]
        }},
        options:{{responsive:true,plugins:{{legend:{{position:'bottom'}},datalabels:makeLineDl()}}}}
    }});

    // M5 revenue
    new Chart(document.getElementById('chart_m5_rev'), {{
        type:'bar',
        data:{{labels:{m5_labels},datasets:[{{label:'营收(百万₦)',data:{m5_rev},backgroundColor:'#22c55e44',borderColor:'#22c55e',borderWidth:1}}]}},
        options:{{responsive:true,plugins:{{legend:{{display:false}},datalabels:makeBarDl()}}}}
    }});
}}

// Init report charts on load
window.addEventListener('DOMContentLoaded', () => {{
    initReportCharts();
}});

// ===== Model Analysis Filter & Sort =====
let m10SortCol = -1;
let m10SortAsc = true;
let m10CurrentPage = 1;
let m10FilteredCount = 0;
const m10PageSize = 50;

function m10UpdatePagination() {{
    const rows = document.querySelectorAll('#m10-tbody tr');
    // First: collect all non-filtered rows (show them all)
    let visible = [];
    rows.forEach(r => {{
        if (!r.dataset.m10Hidden) {{
            r.style.display = '';
            visible.push(r);
        }}
    }});
    const totalRows = visible.length;
    const totalPages = Math.ceil(totalRows / m10PageSize) || 1;
    if (m10CurrentPage < 1) m10CurrentPage = 1;
    if (m10CurrentPage > totalPages) m10CurrentPage = totalPages;
    const startIdx = (m10CurrentPage - 1) * m10PageSize;
    const endIdx = Math.min(startIdx + m10PageSize, totalRows);
    // Hide rows outside current page
    for (let i = 0; i < visible.length; i++) {{
        if (i < startIdx || i >= endIdx) {{
            visible[i].style.display = 'none';
        }}
    }}
    // Render page buttons
    let html = `<span style="font-size:13px;color:var(--text2);margin-right:12px;">第 ${{m10CurrentPage}} / ${{totalPages}} 页，共 ${{totalRows}} 条</span>`;
    html += `<button onclick="m10GoPage(1)" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:${{m10CurrentPage===1?'var(--accent)':'var(--card2)'}};color:${{m10CurrentPage===1?'#fff':'var(--text1)'}};cursor:pointer;font-size:13px;">首页</button>`;
    html += `<button onclick="m10GoPage(${{m10CurrentPage-1}})" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card2);color:var(--text1);cursor:pointer;font-size:13px;" ${{m10CurrentPage<=1?'disabled':''}}>上一页</button>`;
    let startP = Math.max(1, m10CurrentPage - 2);
    let endP = Math.min(totalPages, m10CurrentPage + 2);
    for (let p = startP; p <= endP; p++) {{
        html += `<button onclick="m10GoPage(${{p}})" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:${{p===m10CurrentPage?'var(--accent)':'var(--card2)'}};color:${{p===m10CurrentPage?'#fff':'var(--text1)'}};cursor:pointer;font-size:13px;min-width:36px;">${{p}}</button>`;
    }}
    html += `<button onclick="m10GoPage(${{m10CurrentPage+1}})" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:var(--card2);color:var(--text1);cursor:pointer;font-size:13px;" ${{m10CurrentPage>=totalPages?'disabled':''}}>下一页</button>`;
    html += `<button onclick="m10GoPage(${{totalPages}})" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:${{m10CurrentPage===totalPages?'var(--accent)':'var(--card2)'}};color:${{m10CurrentPage===totalPages?'#fff':'var(--text1)'}};cursor:pointer;font-size:13px;">末页</button>`;
    const pg = document.getElementById('m10-pagination');
    if (pg) pg.innerHTML = html;
}}

function m10GoPage(p) {{
    const rows = document.querySelectorAll('#m10-tbody tr');
    const totalRows = m10FilteredCount || rows.length;
    const totalPages = Math.ceil(totalRows / m10PageSize) || 1;
    p = Math.max(1, Math.min(p, totalPages));
    m10CurrentPage = p;
    m10UpdatePagination();
}}

function m10Filter() {{
    const search = document.getElementById('m10-search').value.toLowerCase();
    const brand = document.getElementById('m10-brand-filter').value;
    const tier = document.getElementById('m10-tier-filter').value;
    const rows = document.querySelectorAll('#m10-tbody tr');
    rows.forEach(r => {{
        const rbrand = r.getAttribute('data-brand');
        const rtier = r.getAttribute('data-tier');
        const model = r.cells[2].textContent.toLowerCase();
        let show = true;
        if (search && !model.includes(search)) show = false;
        if (brand !== '全部' && rbrand !== brand) show = false;
        if (tier !== '全部' && rtier !== tier) show = false;
        if (show) {{
            r.style.display = '';
            delete r.dataset.m10Hidden;
        }} else {{
            r.style.display = 'none';
            r.dataset.m10Hidden = '1';
        }}
    }});
    m10FilteredCount = Array.from(rows).filter(r => !r.dataset.m10Hidden).length;
    m10CurrentPage = 1;
    m10UpdatePagination();
}}

function m10Sort(col) {{
    const tbody = document.getElementById('m10-tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (m10SortCol === col) {{
        m10SortAsc = !m10SortAsc;
    }} else {{
        m10SortCol = col;
        m10SortAsc = true;
    }}
    rows.sort((a, b) => {{
        let va = a.cells[col].textContent;
        let vb = b.cells[col].textContent;
        // Try numeric sort
        const na = parseFloat(va.replace(/[^0-9.\-]/g, ''));
        const nb = parseFloat(vb.replace(/[^0-9.\-]/g, ''));
        if (!isNaN(na) && !isNaN(nb)) return m10SortAsc ? na - nb : nb - na;
        return m10SortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});
    rows.forEach(r => tbody.appendChild(r));
}};

function m10ResetFilters() {{
    document.getElementById('m10-search').value = '';
    document.getElementById('m10-brand-filter').value = '全部';
    document.getElementById('m10-tier-filter').value = '全部';
    m10Filter();
    m10CurrentPage = 1;
    m10UpdatePagination();
}}

// Bind filter events
m10UpdatePagination();
document.getElementById('m10-search')?.addEventListener('input', m10Filter);
document.getElementById('m10-brand-filter')?.addEventListener('change', m10Filter);
document.getElementById('m10-tier-filter')?.addEventListener('change', m10Filter);

// ===== M10: Model Daily Sales Detail =====
let m10DetailChart = null;
let m10DetailOpen = -1;

function toggleModelDetail(idx) {{
    if (m10DetailOpen === idx) {{
        closeModelDetail();
        return;
    }}
    m10DetailOpen = idx;
    const panel = document.getElementById('m10-detail-panel');
    const t = m11ModelTrends[idx];
    if (!t) return;
    panel.style.display = 'block';
    document.getElementById('m10-detail-title').textContent = t.brand + ' ' + t.model + ' · 日销量分析';
    // Stats
    const slope = t.trend_slope || 0;
    const trendLabel = slope < -2 ? '📉 明显下滑' : slope < 0 ? '↘ 缓慢下降' : slope > 2 ? '📈 明显上升' : '→ 基本稳定';
    const momLabel = t.mom_change !== undefined ? (t.mom_change > 0 ? '+' : '') + t.mom_change.toFixed(1) + '% vs ' + '{_cmp_m_label}' : '—';
    document.getElementById('m10-detail-stats').innerHTML =
        '<span>日均 <b style="color:var(--text)">' + t.avg_daily.toFixed(1) + '</b> 台</span>' +
        '<span>最高 <b style="color:var(--text)">' + t.max_daily + '</b> 台</span>' +
        '<span>波动CV <b style="color:var(--text)">' + t.cv_pct.toFixed(1) + '%</b></span>' +
        '<span>环比 <b style="color:var(--text)">' + momLabel + '</b></span>' +
        '<span>趋势 <b style="color:var(--text)">' + trendLabel + '</b></span>';
    // Chart
    const ctx = document.getElementById('m10-detail-chart').getContext('2d');
    if (m10DetailChart) m10DetailChart.destroy();
    // Build datasets - June solid, May dashed
    const datasets = [];
    datasets.push({{
        label: '6月日销',
        data: t.june_daily,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,.15)',
        borderWidth: 2.5,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        order: 0
    }});
    // Only show May if it has data
    const mayHasData = t.may_daily && t.may_daily.some(v => v > 0);
    if (mayHasData) {{
        datasets.push({{
            label: '{_cmp_m_label}同期',
            data: t.may_daily,
            borderColor: 'rgba(245,158,11,.7)',
            backgroundColor: 'rgba(245,158,11,.08)',
            borderWidth: 1.5,
            borderDash: [6, 3],
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 5,
            fill: false,
            order: 1
        }});
    }}
    // Labels - use June dates as base
    const labels = t.june_dates;
    m10DetailChart = new Chart(ctx, {{
        type: 'line',
        data: {{ labels: labels, datasets: datasets }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                legend: {{ display: true, position: 'top', labels: {{ color: '#94a3b8', font: {{ size: 11 }} }} }},
                tooltip: {{
                    backgroundColor: '#1e293b',
                    borderColor: '#334155',
                    borderWidth: 1,
                    titleColor: '#f1f5f9',
                    bodyColor: '#e2e8f0',
                    callbacks: {{
                        label: function(ctx) {{ return ctx.dataset.label + ': ' + ctx.parsed.y + '台'; }}
                    }}
                }}
            }},
            scales: {{
                x: {{ grid: {{ color: 'rgba(51,65,85,.4)' }}, ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }} }},
                y: {{ grid: {{ color: 'rgba(51,65,85,.4)' }}, ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }} }}
            }}
        }}
    }});
    // Highlight selected row
    document.querySelectorAll('#m10-tbody tr').forEach(tr => {{
        tr.style.background = tr.getAttribute('data-i') == idx ? 'var(--surface2)' : '';
    }});
    // Scroll to panel
    panel.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
}}

function closeModelDetail() {{
    m10DetailOpen = -1;
    document.getElementById('m10-detail-panel').style.display = 'none';
    if (m10DetailChart) {{ m10DetailChart.destroy(); m10DetailChart = null; }}
    document.querySelectorAll('#m10-tbody tr').forEach(tr => {{ tr.style.background = ''; }});
}}

// ===== M11: Model Sales Trend Chart =====
const trendColors = ['#3b82f6','#f59e0b','#22c55e','#ef4444','#8b5cf6'];
const trendMayColors = ['rgba(59,130,246,.35)','rgba(245,158,11,.35)','rgba(34,197,94,.35)','rgba(239,68,68,.35)','rgba(139,92,246,.35)'];
let trendSelected = [];
let trendChart = null;

function initTrendCombo() {{
    // Populate brand filter
    const brandSel = document.getElementById('trend-brand-filter');
    m11Brands.forEach(b => {{
        const opt = document.createElement('option');
        opt.value = b; opt.textContent = b;
        brandSel.appendChild(opt);
    }});
    // Populate tier filter
    const tierSel = document.getElementById('trend-tier-filter');
    m11Tiers.forEach(t => {{
        const opt = document.createElement('option');
        opt.value = t; opt.textContent = t;
        tierSel.appendChild(opt);
    }});
    // Populate combo list
    const list = document.getElementById('trend-combo-list');
    m11ModelTrends.forEach((t, i) => {{
        const div = document.createElement('div');
        div.style.cssText = 'padding:7px 12px;cursor:pointer;color:#e2e8f0;font-size:12px;border-bottom:1px solid #1e293b;display:flex;justify-content:space-between';
        div.innerHTML = '<span>'+t.model+'</span><span style="color:#475569;font-size:10px">月销'+t.total_june+'台</span>';
        div.onmouseenter = function() {{ this.style.background = '#334155'; }};
        div.onmouseleave = function() {{ this.style.background = ''; }};
        div.onclick = function(e) {{ e.stopPropagation(); addTrendModel(i); }};
        div.setAttribute('data-idx', i);
        div.setAttribute('data-model', t.model);
        div.setAttribute('data-brand', t.brand||'');
        div.setAttribute('data-tier', t.price_tier||'');
        list.appendChild(div);
    }});
}}
function toggleTrendCombo() {{
    const dd = document.getElementById('trend-combo-dropdown');
    const input = document.getElementById('trend-combo-search');
    if (dd.style.display === 'block') {{
        dd.style.display = 'none';
    }} else {{
        dd.style.display = 'block';
        input.value = '';
        filterTrendCombo();
        setTimeout(function(){{ input.focus(); }}, 50);
    }}
}}
function filterTrendCombo() {{
    const keyword = document.getElementById('trend-combo-search').value.toLowerCase().trim();
    const brandFilter = document.getElementById('trend-brand-filter').value;
    const tierFilter = document.getElementById('trend-tier-filter').value;
    const items = document.querySelectorAll('#trend-combo-list div[data-idx]');
    let visible = 0;
    items.forEach(d => {{
        const model = (d.getAttribute('data-model')||'').toLowerCase();
        const brand = d.getAttribute('data-brand')||'';
        const tier = d.getAttribute('data-tier')||'';
        const match = model.includes(keyword) && (!brandFilter || brand===brandFilter) && (!tierFilter || tier===tierFilter);
        if (match) {{ d.style.display = ''; visible++; }}
        else {{ d.style.display = 'none'; }}
    }});
    let noMatch = document.getElementById('trend-no-match');
    if (visible === 0) {{
        if (!noMatch) {{
            noMatch = document.createElement('div');
            noMatch.id = 'trend-no-match';
            noMatch.style.cssText = 'padding:8px 12px;color:#94a3b8;font-size:12px';
            noMatch.textContent = '未找到匹配型号';
            document.getElementById('trend-combo-list').appendChild(noMatch);
        }}
        noMatch.style.display = '';
    }} else {{
        if (noMatch) noMatch.style.display = 'none';
    }}
}}
function handleTrendComboKey(e) {{
    const dd = document.getElementById('trend-combo-dropdown');
    if (dd.style.display !== 'block') return;
    const items = Array.from(document.querySelectorAll('#trend-combo-list div[data-idx]')).filter(d => d.style.display !== 'none');
    if (e.key === 'Escape') {{ dd.style.display = 'none'; }}
    else if (e.key === 'Enter') {{
        e.preventDefault();
        const active = dd.querySelector('.combo-active-trend');
        if (active) addTrendModel(parseInt(active.getAttribute('data-idx')));
        else if (items.length > 0) addTrendModel(parseInt(items[0].getAttribute('data-idx')));
    }} else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {{
        e.preventDefault();
        const active = dd.querySelector('.combo-active-trend');
        let idx = active ? items.indexOf(active) : -1;
        if (e.key === 'ArrowDown') idx = (idx + 1) % items.length;
        else idx = (idx - 1 + items.length) % items.length;
        items.forEach(d => {{ d.style.background = ''; d.classList.remove('combo-active-trend'); }});
        if (items[idx]) {{
            items[idx].style.background = '#334155';
            items[idx].classList.add('combo-active-trend');
            items[idx].scrollIntoView({{block:'nearest'}});
        }}
    }}
}}
document.addEventListener('click', function(e) {{
    const combo = document.getElementById('trend-combo-dropdown');
    const btn = document.getElementById('trend-combo-btn');
    if (combo && btn && !btn.contains(e.target) && !combo.contains(e.target)) combo.style.display = 'none';
}});
function addTrendModel(idx) {{
    if (trendSelected.length >= 5) return;
    if (trendSelected.includes(idx)) return;
    trendSelected.push(idx);
    document.getElementById('trend-combo-dropdown').style.display = 'none';
    renderTrendTags();
    renderTrendChart();
}}
function removeTrendModel(idx) {{
    trendSelected = trendSelected.filter(i => i !== idx);
    renderTrendTags();
    renderTrendChart();
}}
function clearTrendSelection() {{
    trendSelected = [];
    renderTrendTags();
    renderTrendChart();
}}
function renderTrendTags() {{
    const container = document.getElementById('trend-selected-tags');
    container.innerHTML = '';
    trendSelected.forEach(i => {{
        const t = m11ModelTrends[i];
        const tag = document.createElement('span');
        tag.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:4px;font-size:11px;font-weight:600;background:'+trendColors[trendSelected.indexOf(i)]+'20;color:'+trendColors[trendSelected.indexOf(i)]+';border:1px solid '+trendColors[trendSelected.indexOf(i)]+'40';
        tag.innerHTML = t.model + ' <span onclick="removeTrendModel('+i+')" style="cursor:pointer;opacity:.7;font-size:14px">&times;</span>';
        container.appendChild(tag);
    }});
}}
function renderTrendChart() {{
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (trendChart) trendChart.destroy();
    if (trendSelected.length === 0) {{
        trendChart = new Chart(ctx, {{
            type: 'line',
            data: {{ labels: m11ModelTrends[0].june_dates, datasets: [] }},
            options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ display:false }} }} }}
        }});
        document.getElementById('trend-stats').innerHTML = '<span style="color:#64748b">请添加型号查看销量波动趋势</span>';
        return;
    }}
    const datasets = [];
    let statsHtml = '';
    trendSelected.forEach((idx, ci) => {{
        const t = m11ModelTrends[idx];
        // June data
        datasets.push({{
            label: t.model + ' (6月)',
            data: t.june_daily,
            borderColor: trendColors[ci],
            backgroundColor: trendColors[ci]+'15',
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 5,
            fill: false,
            order: 0
        }});
        // May data (dashed)
        datasets.push({{
            label: t.model + ' (5月)',
            data: t.may_daily.length === t.june_daily.length ? t.may_daily : t.may_daily.slice(0, t.june_daily.length),
            borderColor: trendColors[ci],
            borderDash: [6,3],
            borderWidth: 1,
            tension: 0.3,
            pointRadius: 0,
            fill: false,
            order: 1
        }});
        let trendIcon = t.trend_slope > 1 ? '📈' : (t.trend_slope < -1 ? '📉' : '➡️');
        statsHtml += '<span style="display:inline-block;margin-right:16px;margin-bottom:8px">'+
            '<b style="color:'+trendColors[ci]+'">'+t.model+'</b> '+
            '月销<b>'+t.total_june+'台</b> '+
            '日均<b>'+t.avg_daily+'台</b> '+
            '波动率<b>'+(t.cv_pct||0)+'%</b> '+
            trendIcon+'<b>'+(t.trend_slope>0?'+':'')+t.trend_slope+'</b>/天'+
            (t.mom_change !== null ? ' 环比<b style="color:'+(t.mom_change>=0?'#22c55e':'#ef4444')+'">'+(t.mom_change>=0?'+':'')+t.mom_change+'%</b>' : '')+
            '</span>';
    }});
    trendChart = new Chart(ctx, {{
        type: 'line',
        data: {{ labels: m11ModelTrends[0].june_dates, datasets: datasets }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{ mode: 'index', intersect: false }},
            plugins: {{
                legend: {{ labels: {{ color: '#94a3b8', font:{{size:10}}, usePointStyle:true, boxWidth:8 }} }},
                tooltip: {{ mode: 'index', intersect: false }}
            }},
            scales: {{
                x: {{ ticks: {{ color: '#64748b', font:{{size:10}}, maxTicksLimit:15, maxRotation:0 }} }},
                y: {{ ticks: {{ color: '#64748b', font:{{size:10}} }}, grid: {{ color: '#1e293b' }}, title: {{ display:true, text:'日销量(台)', color:'#64748b' }} }}
            }}
        }}
    }});
    document.getElementById('trend-stats').innerHTML = statsHtml;
}}
// Initialize trend combo on load
document.addEventListener('DOMContentLoaded', function() {{
    if (typeof m11ModelTrends !== 'undefined' && m11ModelTrends.length > 0) initTrendCombo();
    m12InitSelect();
    m12Sort(2, 'num');  // Default sort: 日均销量降序
}});

// ===== M12 Store Volatility Detail =====
function m12InitSelect() {{
    const sel = document.getElementById('m12_store_select');
    if (!sel) return;
    const stores = (D.m12_store_volatility || []);
    stores.forEach((s, i) => {{
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = s.short + ' (CV ' + s.cv.toFixed(1) + '%, ' + s.rating + ')';
        sel.appendChild(opt);
    }});
    const hint = document.getElementById('m12_filter_hint');
    if (hint) hint.textContent = '共 ' + stores.length + ' 家门店';
}}

// ===== M12 Table Sorting =====
var m12SortCol = -1, m12SortDir = 'desc';

function m12Sort(col, type) {{
    var tbl = document.getElementById('tbl_m12');
    if (!tbl) return;
    var tbody = tbl.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));

    if (m12SortCol === col) {{
        m12SortDir = m12SortDir === 'asc' ? 'desc' : 'asc';
    }} else {{
        m12SortCol = col;
        m12SortDir = 'desc';
    }}

    // Clear all arrows & active states
    for (var i = 1; i <= 10; i++) {{
        var sp = document.getElementById('m12_arrow_' + i);
        if (sp) sp.textContent = '';
        if (sp && sp.parentElement) sp.parentElement.classList.remove('m12-active');
    }}
    // Set current arrow
    var arrow = document.getElementById('m12_arrow_' + col);
    if (arrow) {{
        arrow.textContent = m12SortDir === 'asc' ? ' \u25B2' : ' \u25BC';
        if (arrow.parentElement) arrow.parentElement.classList.add('m12-active');
    }}

    // Sort rows by data-v attribute
    rows.sort(function(a, b) {{
        var va = a.cells[col].getAttribute('data-v');
        var vb = b.cells[col].getAttribute('data-v');
        var cmp;
        if (type === 'num') {{
            cmp = parseFloat(va) - parseFloat(vb);
        }} else {{
            cmp = String(va).localeCompare(String(vb), 'zh');
        }}
        return m12SortDir === 'asc' ? cmp : -cmp;
    }});

    // Re-append sorted rows, update rank numbers (keep data-idx for detail lookup)
    rows.forEach(function(r, i) {{
        r.cells[0].textContent = i + 1;
        r.cells[0].setAttribute('data-v', String(i + 1));
        tbody.appendChild(r);
    }});
}}

function m12ShowDetail(idx) {{
    const panel = document.getElementById('m12_detail_panel');
    const hint = document.getElementById('m12_filter_hint');
    if (idx === '' || idx === null) {{
        panel.style.display = 'none';
        if (hint) hint.textContent = '共 ' + (D.m12_store_volatility||[]).length + ' 家门店';
        return;
    }}
    const stores = D.m12_store_volatility || [];
    const s = stores[parseInt(idx)];
    if (!s) return;

    const curr = s.daily_series || [];
    const prev = s.may_daily_series || [];
    const dates = s.biz_dates || [];
    const n = curr.length;
    const maxBars = Math.max(n, prev.length);

    // --- Build larger SVG chart ---
    const chartW = 760, chartH = 280, padL = 36, padR = 12, padT = 18, padB = 36;
    const plotW = chartW - padL - padR;
    const plotH = chartH - padT - padB;
    const allVals = curr.concat(prev).filter(v => v !== null && v !== undefined);
    const yMax = Math.max(...allVals, 1) * 1.15;
    const barW = plotW / maxBars * 0.35;
    const gap = plotW / maxBars * 0.15;

    // Y axis grid lines
    let gridLines = '';
    const ySteps = 4;
    for (let i = 0; i <= ySteps; i++) {{
        const yVal = yMax * i / ySteps;
        const y = padT + plotH - (yVal / yMax) * plotH;
        gridLines += '<line x1="' + padL + '" y1="' + y.toFixed(1) + '" x2="' + (chartW - padR) + '" y2="' + y.toFixed(1) + '" stroke="' + (isDark ? '#334155' : '#e2e8f0') + '" stroke-width="0.5"/>';
        gridLines += '<text x="' + (padL - 4) + '" y="' + (y + 3).toFixed(1) + '" fill="' + (isDark ? '#64748b' : '#94a3b8') + '" font-size="9" text-anchor="end">' + Math.round(yVal) + '</text>';
    }}

    // Bars + trend line
    let bars = '';
    let trendPts = [];
    for (let i = 0; i < n; i++) {{
        const xCenter = padL + (i + 0.5) * (plotW / maxBars);
        const v = curr[i];
        const bh = (v / yMax) * plotH;
        const y = padT + plotH - bh;
        const color = v === 0 ? '#ef4444' : (s.rating_color || '#3b82f6');
        bars += '<rect x="' + (xCenter - barW - gap/2).toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + barW.toFixed(1) + '" height="' + bh.toFixed(1) + '" fill="' + color + '" rx="1"/>';
        // Data label on current month bar
        if (v > 0 && bh > 14) {{
            bars += '<text x="' + (xCenter - barW/2 - gap/2).toFixed(1) + '" y="' + (y - 3).toFixed(1) + '" fill="' + (isDark ? '#cbd5e1' : '#334155') + '" font-size="8" text-anchor="middle" font-weight="600">' + Math.round(v) + '</text>';
        }}
        // Previous month bar
        if (prev[i] !== undefined && prev[i] !== null) {{
            const pv = prev[i];
            const pbh = (pv / yMax) * plotH;
            const py = padT + plotH - pbh;
            bars += '<rect x="' + (xCenter + gap/2).toFixed(1) + '" y="' + py.toFixed(1) + '" width="' + barW.toFixed(1) + '" height="' + pbh.toFixed(1) + '" fill="' + (isDark ? '#475569' : '#cbd5e1') + '" rx="1"/>';
            // Data label on previous month bar
            if (pv > 0 && pbh > 14) {{
                bars += '<text x="' + (xCenter + barW/2 + gap/2).toFixed(1) + '" y="' + (py - 3).toFixed(1) + '" fill="' + (isDark ? '#64748b' : '#94a3b8') + '" font-size="8" text-anchor="middle">' + Math.round(pv) + '</text>';
            }}
        }}
        trendPts.push([xCenter, y]);
        // X label
        if (i < dates.length) {{
            bars += '<text x="' + xCenter.toFixed(1) + '" y="' + (chartH - padB + 14) + '" fill="' + (isDark ? '#64748b' : '#94a3b8') + '" font-size="8" text-anchor="middle">' + dates[i] + '</text>';
        }}
    }}

    // Trend line (current month)
    let trendLine = '';
    if (trendPts.length > 1) {{
        const pts = trendPts.map(p => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
        trendLine = '<polyline points="' + pts + '" fill="none" stroke="' + (s.trend_color || '#3b82f6') + '" stroke-width="1.5" stroke-dasharray="3,2" opacity="0.7"/>';
    }}

    // Legend
    const legendY = padT - 6;
    const legend = '<rect x="' + (chartW - padR - 180) + '" y="' + legendY + '" width="8" height="8" fill="' + (s.rating_color || '#3b82f6') + '" rx="1"/>' +
        '<text x="' + (chartW - padR - 168) + '" y="' + (legendY + 7) + '" fill="' + (isDark ? '#94a3b8' : '#64748b') + '" font-size="9">本月日销</text>' +
        '<rect x="' + (chartW - padR - 110) + '" y="' + legendY + '" width="8" height="8" fill="' + (isDark ? '#475569' : '#cbd5e1') + '" rx="1"/>' +
        '<text x="' + (chartW - padR - 98) + '" y="' + (legendY + 7) + '" fill="' + (isDark ? '#94a3b8' : '#64748b') + '" font-size="9">上月同期</text>' +
        '<line x1="' + (chartW - padR - 50) + '" y1="' + (legendY + 4) + '" x2="' + (chartW - padR - 38) + '" y2="' + (legendY + 4) + '" stroke="' + (s.trend_color || '#3b82f6') + '" stroke-width="1.5" stroke-dasharray="3,2"/>' +
        '<text x="' + (chartW - padR - 34) + '" y="' + (legendY + 7) + '" fill="' + (isDark ? '#94a3b8' : '#64748b') + '" font-size="9">趋势</text>';

    const chartSvg = '<svg viewBox="0 0 ' + chartW + ' ' + chartH + '" preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;display:block">' +
        gridLines + bars + trendLine + legend +
        '<text x="' + padL + '" y="' + (padT - 8) + '" fill="' + (isDark ? '#cbd5e1' : '#334155') + '" font-size="11" font-weight="600">' + s.short + ' 日销波动明细</text>' +
        '</svg>';

    // --- Day-by-day breakdown table ---
    let detailRows = '';
    let currTotal = 0, prevTotal = 0;
    for (let i = 0; i < maxBars; i++) {{
        const dt = dates[i] || '—';
        const cv = curr[i] !== undefined ? curr[i] : null;
        const pv = prev[i] !== undefined ? prev[i] : null;
        if (cv !== null) currTotal += cv;
        if (pv !== null) prevTotal += (pv || 0);
        const diff = (cv !== null && pv !== null) ? cv - pv : null;
        const cvStr = cv !== null ? (cv === 0 ? '<span style="color:#ef4444;font-weight:600">0</span>' : cv.toFixed(0)) : '—';
        const pvStr = pv !== null ? pv.toFixed(0) : '—';
        const diffStr = diff !== null ?
            (diff > 0 ? '<span style="color:#22c55e">+' + diff.toFixed(0) + '</span>' :
             diff < 0 ? '<span style="color:#ef4444">' + diff.toFixed(0) + '</span>' :
             '<span style="color:#6b7280">0</span>') : '—';
        const rowBg = cv === 0 ? 'background:rgba(239,68,68,0.06)' : '';
        detailRows += '<tr style="' + rowBg + '"><td>' + dt + '</td><td style="text-align:right">' + cvStr + '</td><td style="text-align:right">' + pvStr + '</td><td style="text-align:right">' + diffStr + '</td></tr>';
    }}
    // Total row
    const totalDiff = currTotal - prevTotal;
    const totalDiffStr = prevTotal > 0 ?
        (totalDiff > 0 ? '<span style="color:#22c55e;font-weight:600">+' + totalDiff.toFixed(0) + '</span>' :
         totalDiff < 0 ? '<span style="color:#ef4444;font-weight:600">' + totalDiff.toFixed(0) + '</span>' :
         '<span style="color:#6b7280">0</span>') : '—';
    detailRows += '<tr style="border-top:2px solid var(--border);font-weight:700"><td>合计</td><td style="text-align:right">' + currTotal.toFixed(0) + '</td><td style="text-align:right">' + (prevTotal > 0 ? prevTotal.toFixed(0) : '—') + '</td><td style="text-align:right">' + totalDiffStr + '</td></tr>';

    // --- Stats cards ---
    const cvChangeVal = s.cv_change || 0;
    const cvChangeStr = cvChangeVal !== 0 ?
        '<span style="color:' + (cvChangeVal > 0 ? '#ef4444' : '#22c55e') + '">' + (cvChangeVal > 0 ? '+' : '') + cvChangeVal.toFixed(1) + 'pp</span>' :
        '<span style="color:#6b7280">—</span>';

    const statsHtml = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:6px;margin-bottom:10px">' +
        m12DetailCard('日均销量', s.mean.toFixed(1) + ' 台', '总销 ' + (s.total_qty||0).toFixed(0) + ' 台', '#3b82f6') +
        m12DetailCard('CV变异系数', s.cv.toFixed(1) + '%', '标准差 ' + s.std.toFixed(1), s.rating_color || '#3b82f6') +
        m12DetailCard('波动评级', s.rating, 'CV环比 ' + cvChangeStr, s.rating_color || '#6b7280') +
        m12DetailCard('趋势方向', s.trend_dir, '斜率 ' + (s.slope||0).toFixed(2), s.trend_color || '#6b7280') +
        m12DetailCard('最高/最低日销', s.max.toFixed(0) + ' / ' + s.min.toFixed(0), '极差 ' + (s.max - s.min).toFixed(0), '#8b5cf6') +
        m12DetailCard('零销量天数', s.zero_days + ' 天', s.zero_days > 0 ? '⚠ 需排查运营异常' : '✓ 无零销日', s.zero_days > 0 ? '#ef4444' : '#22c55e') +
        '</div>';

    // --- Assemble panel ---
    // Brand donut chart
    const brandPalette = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#06b6d4','#a3e635','#6b7280'];
    const brands = s.brands || [];
    const totalBrandQty = brands.reduce((sum, b) => sum + b.qty, 0);
    const donutR = 42, donutCirc = 2 * Math.PI * donutR;
    let donutPaths = '';
    let brandLegend = '';
    let offset = 0;
    brands.forEach((b, i) => {{
        const color = brandPalette[i % brandPalette.length];
        const frac = b.qty / (totalBrandQty || 1);
        const dashLen = frac * donutCirc;
        donutPaths += '<circle cx="55" cy="55" r="' + donutR + '" fill="none" stroke="' + color + '" stroke-width="16" stroke-dasharray="' + dashLen.toFixed(1) + ' ' + (donutCirc - dashLen).toFixed(1) + '" stroke-dashoffset="' + (-offset).toFixed(1) + '" transform="rotate(-90 55 55)"/>';
        offset += dashLen;
        brandLegend += '<div style="display:flex;align-items:center;gap:3px;margin-bottom:1px">' +
            '<div style="width:7px;height:7px;border-radius:2px;background:' + color + ';flex-shrink:0"></div>' +
            '<span style="font-size:10px;color:var(--text);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + b.brand + '</span>' +
            '<span style="font-size:10px;color:var(--muted);min-width:32px;text-align:right">' + b.pct + '%</span>' +
            '</div>';
    }});
    const donutSvg = brands.length > 0 ?
        '<svg width="110" height="110" viewBox="0 0 110 110" style="flex-shrink:0;margin:0 auto;display:block">' +
        donutPaths +
        '<text x="55" y="52" text-anchor="middle" fill="var(--text)" font-size="16" font-weight="700">' + totalBrandQty + '</text>' +
        '<text x="55" y="66" text-anchor="middle" fill="var(--muted)" font-size="8">总销量</text>' +
        '</svg>' : '<div style="color:var(--muted);font-size:11px;padding:16px;text-align:center">无品牌数据</div>';

    // Top models table
    const topModels = s.top_models || [];
    let modelRows = '';
    topModels.forEach((m, i) => {{
        const pct = totalBrandQty > 0 ? (m.qty / totalBrandQty * 100).toFixed(1) : '0.0';
        modelRows += '<tr><td>' + (i+1) + '</td><td style="color:#3b82f6">' + m.model + '</td><td style="text-align:right">' + m.qty + '</td><td style="text-align:right;color:var(--muted)">' + pct + '%</td></tr>';
    }});

    // Store ranking by total qty
    const allStores = D.m12_store_volatility || [];
    const sortedByQty = [...allStores].sort((a, b) => (b.total_qty||0) - (a.total_qty||0));
    const storeRank = sortedByQty.findIndex(x => x.short === s.short) + 1;
    const companyAvg = allStores.length > 0 ? (allStores.reduce((sum, x) => sum + (x.total_qty||0), 0) / allStores.length) : 0;
    const vsAvg = ((s.total_qty||0) - companyAvg) / (companyAvg || 1) * 100;

    panel.innerHTML =
        '<div style="border:1px solid var(--border);border-radius:8px;padding:14px;background:var(--card)">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">' +
        '<div style="font-size:15px;font-weight:700;color:var(--text)">' + s.short + ' — 日销波动明细' +
        '<span style="font-size:11px;font-weight:400;color:var(--muted);margin-left:8px">销量排名 #' + storeRank + '/' + allStores.length +
        (vsAvg >= 0 ? '（高于均值' : '（低于均值') + Math.abs(vsAvg).toFixed(0) + '%）</span></div>' +
        '<button onclick="m12CloseDetail()" style="padding:4px 10px;border-radius:4px;border:1px solid var(--border);background:var(--surface2);color:var(--text2);cursor:pointer;font-size:12px">✕ 关闭</button>' +
        '</div>' +
        statsHtml +
        // 3-column: bar chart (flex:2) | brand donut+legend (auto) | top models (flex:1)
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;align-items:stretch">' +
        '<div style="flex:2;min-width:320px;overflow-x:auto;display:flex;align-items:stretch">' + chartSvg + '</div>' +
        '<div style="flex:0 0 auto;min-width:130px;max-width:180px">' +
            '<div style="font-size:11px;font-weight:600;color:var(--text);margin-bottom:4px;text-align:center">品牌销量占比</div>' +
            donutSvg +
            '<div style="margin-top:4px">' + brandLegend + '</div>' +
        '</div>' +
        (topModels.length > 0 ?
        '<div style="flex:1;min-width:150px">' +
            '<div style="font-size:11px;font-weight:600;color:var(--text);margin-bottom:4px">Top 10 畅销型号</div>' +
            '<table style="font-size:10px;width:100%;border-collapse:collapse"><thead><tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:2px 4px">#</th><th style="text-align:left;padding:2px 4px">型号</th><th style="text-align:right;padding:2px 4px">销量</th><th style="text-align:right;padding:2px 4px">占比</th></tr></thead><tbody>' + modelRows + '</tbody></table>' +
        '</div>'
        : '') +
        '</div>' +
        '</div>';
    panel.style.display = 'block';
    if (hint) hint.textContent = '';
}}

function m12CloseDetail() {{
    const sel = document.getElementById('m12_store_select');
    const panel = document.getElementById('m12_detail_panel');
    const hint = document.getElementById('m12_filter_hint');
    if (sel) sel.value = '';
    if (panel) panel.style.display = 'none';
    if (hint) hint.textContent = '共 ' + (D.m12_store_volatility||[]).length + ' 家门店';
}}

function m12DetailCard(label, value, sub, color) {{
    return '<div style="padding:6px 8px;border-radius:5px;border:1px solid var(--border);background:var(--surface2)">' +
        '<div style="font-size:10px;color:var(--muted);margin-bottom:1px">' + label + '</div>' +
        '<div style="font-size:14px;font-weight:700;color:' + (color || '#3b82f6') + '">' + value + '</div>' +
        '<div style="font-size:9px;color:var(--muted);margin-top:1px">' + sub + '</div>' +
        '</div>';
}}

{history_js}
</script>
</body>
</html>"""

with open(args.out, 'w', encoding='utf-8') as f:
    f.write(html)

import os
size = os.path.getsize(args.out)
print(f"Dashboard generated: {size/1024:.0f}KB")