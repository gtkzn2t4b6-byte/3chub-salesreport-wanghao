#!/usr/bin/env python3
"""Generate the full 9-module sales dashboard HTML"""
import argparse
import datetime
import json
import os

parser = argparse.ArgumentParser(description='Generate sales dashboard HTML')
parser.add_argument('--data', required=True, help='Path to dashboard_full.json')
parser.add_argument('--history', default=None, help='Path to historical_data.json (optional)')
parser.add_argument('--kpi', default='kpi_annual.json', help='Path to kpi_annual.json (optional, 年度任务页签; 不存在则隐藏)')
parser.add_argument('--out', default='dashboard_director.html', help='Output HTML file path')
parser.add_argument('--theme', default='light', choices=['dark', 'light'], help='Color theme (light default, dark available)')
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

# Load annual KPI data if available (年度任务四模块)
K = None
if args.kpi and os.path.exists(args.kpi):
    try:
        with open(args.kpi) as f:
            K = json.load(f)
    except Exception:
        K = None

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
# 奈拉→人民币换算 (2026-09-17 定: 1元≈205奈拉, 用户口径)
NGN_CNY_RATE = 1 / 205
def fmt_rmb(ngn):
    cny = ngn * NGN_CNY_RATE
    if abs(cny) >= 1e8: return f"≈¥{cny/1e8:.2f}亿"
    if abs(cny) >= 1e4: return f"≈¥{cny/1e4:.1f}万"
    return f"≈¥{cny:.0f}"

# ===== 浅色主题支持 =====
# 思路: 1) 定向替换 Chart.js 集中配色与网格色; 2) 注入浅色 CSS 补丁(:root 变量覆盖 + 结构规则覆盖 + 内联样式属性选择器覆盖)。
# SVG 手绘趋势图自带 isDark 判断(读 --bg 值), 变量变浅后自动切浅色分支, 无需处理。
LIGHT_THEME_CSS = """
/* ===== Light theme overrides ===== */
:root{--bg:#f1f5f9;--surface:#ffffff;--surface2:#f1f5f9;--border:#e2e8f0;--text:#0f172a;--text2:#64748b;--card:#ffffff;--card2:#f1f5f9;--text1:#0f172a;--muted:#64748b;--red:#dc2626;--green:#16a34a;--blue:#2563eb;--yellow:#d97706;--orange:#ea580c}
.header{background:linear-gradient(135deg,#ffffff,#f1f5f9) !important;color:#0f172a !important;border-bottom:1px solid #e2e8f0}
.header h1{color:#0f172a !important}
.header .date{color:#64748b !important}
.header .time-progress{background:rgba(37,99,235,0.08);color:#2563eb;border-color:rgba(37,99,235,0.25)}
.nav-btn{border-color:#cbd5e1;color:#64748b}
.nav-btn:hover{border-color:#2563eb;color:#0f172a}
.nav-btn.active{background:#2563eb;color:#fff;border-color:#2563eb}
.m6-table th{background:rgba(241,245,249,0.95) !important}
.sub-tab{background:#e2e8f0 !important;color:#334155 !important}
.sub-tab:hover{background:#dbe3ec !important}
.m12-sortable.m12-active{background:#dbeafe !important}
.summary-box p{color:#334155}
.summary-box p b{color:#0f172a}
.summary-box h3{color:#2563eb}
.report-block:first-child .report-title{color:#2563eb}
select,input[type=text]{background:#ffffff !important;color:#0f172a !important;border-color:#cbd5e1 !important}
div[style*="background:#1e293b"]{background:#ffffff !important;border-color:#e2e8f0 !important}
div[style*="border-bottom:1px solid #334155"]{border-bottom-color:#e2e8f0 !important}
div[style*="box-shadow:0 8px 24px"]{box-shadow:0 8px 24px rgba(15,23,42,0.12) !important}
#store-combo-list div,#trend-combo-list div{color:#334155 !important;border-bottom-color:#e2e8f0 !important}
#store-combo-list div:hover,#trend-combo-list div:hover{background:#f1f5f9 !important}
[style*="color:#22c55e"]{color:#16a34a !important}
[style*="color:#ef4444"]{color:#dc2626 !important}
[style*="color:#f59e0b"]{color:#b45309 !important}
[style*="color:#3b82f6"]{color:#2563eb !important}
[style*="color:#60a5fa"]{color:#2563eb !important}
[style*="color:#8b5cf6"]{color:#7c3aed !important}
[style*="color:#a78bfa"]{color:#7c3aed !important}
[style*="color:#f87171"]{color:#dc2626 !important}
[style*="color:#e2e8f0"]{color:#334155 !important}
[style*="color:#f1f5f9"]{color:#0f172a !important}
[style*="color:#cbd5e1"]{color:#475569 !important}
[style*="color:#94a3b8"]{color:#64748b !important}
[style*="color:#64748b"]{color:#475569 !important}
/* combo 下拉浅色兜底: 浏览器改写 style 属性后 div[style*=...] 选择器会失效, 必须用 ID 选择器 */
#trend-combo-dropdown,#store-combo-dropdown{background:#ffffff !important;border:1px solid #cbd5e1 !important;box-shadow:0 8px 24px rgba(15,23,42,0.12) !important}
#trend-combo-search,#store-combo-search{background:#ffffff !important;color:#0f172a !important;border:1px solid #cbd5e1 !important}
#store-combo-btn{background:#ffffff !important;color:#0f172a !important;border:1px solid #cbd5e1 !important}
#trend-combo-list > div,#store-combo-list > div{background:transparent !important;color:#334155 !important;border-bottom:1px solid #e2e8f0 !important}
#trend-combo-list > div:hover,#store-combo-list > div:hover,#trend-combo-list > div.combo-active-trend,#store-combo-list > div.combo-active{background:#eef2f7 !important}
/* ===== 视觉精修 (浅色, 不破坏 dark) ===== */
/* 卡片统一: 白底 + 轻阴影 + 弱边框 */
.kpi-card,.section,.chart-box,.tier-card,.summary-box,.report-block{box-shadow:0 1px 3px rgba(15,23,42,0.06)}
.kpi-card,.chart-box{border-radius:12px}
/* KPI 卡顶部强调色条 + 更大数值 */
.kpi-card{position:relative;overflow:hidden;padding-top:16px}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#2563eb,#60a5fa)}
.kpi-value{font-size:24px}
/* 间距节奏 */
.container{padding:20px}
.section{margin-bottom:20px}
.section-body{padding:16px 20px}
.section-header{padding:14px 20px}
/* 字体层级 */
.section-title{font-size:15px}
/* 表格斑马纹 + 表头 */
tbody tr:nth-child(even){background:rgba(15,23,42,0.02)}
th{background:#f8fafc}
/* 图表白卡 + 阴影 */
.chart-box{background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(15,23,42,0.06);padding:16px}
/* 导航按钮精致化 */
.nav-btn{border-radius:8px}
/* 分区标题 */
.zone-title{color:#0f172a}
.zone-note{color:#64748b}
/* 二级章节条降级为浅色轻量 */
.mod-nav{background:#ffffff}
.mod-nav-btn{background:#ffffff;color:#64748b;border-color:#e2e8f0;font-size:12px}
/* 数据汇报块改 2 列网格 (总览卡占满首行) */
.report-summary{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.report-block:first-child{grid-column:1/-1}
@media(max-width:768px){
    .report-summary{grid-template-columns:1fr}
}
"""
def apply_light_theme(html):
    # Chart.js 集中配置与网格/悬停底色: 精确令牌替换(不碰 SVG isDark 浅色分支里的 #334155/#e2e8f0 文本色)
    html = html.replace("Chart.defaults.color = '#94a3b8';", "Chart.defaults.color = '#64748b';")
    html = html.replace("Chart.defaults.borderColor = '#334155';", "Chart.defaults.borderColor = '#e2e8f0';")
    html = html.replace("rgba(51,65,85,", "rgba(148,163,184,")   # 图表网格线 + m6表格边框
    html = html.replace("rgba(255,255,255,0.05)", "rgba(15,23,42,0.045)")  # 表格行悬停
    html = html.replace("#cbd5e1", "#475569")  # 数据标签/说明文字(SVG浅色柱填色随之加深,浅底下更清晰)
    html = html.replace("#94a3b8", "#64748b")  # 次要文字全局加深一档保证浅底可读性
    # 注入 CSS 补丁(放在 </style> 前, 后声明覆盖同优先级规则)
    html = html.replace("</style>", LIGHT_THEME_CSS + "</style>")
    return html

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
            <td style="font-size:11px">{fmt_naira(s.get('fund_tied', 0))}</td>
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
    _fund_map = {x['品牌']: x for x in D.get('m14_inv_value', {}).get('brands', [])}
    _total_brand_fund = sum((x.get('fund') or 0) for x in _fund_map.values()) or 1
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
        _bf = _fund_map.get(b['品牌'], {})
        _avg_p = _bf.get('avg_price') or 0
        _fund = _bf.get('fund') or 0
        _fund_pct = (_fund / _total_brand_fund * 100)
        rows.append(f"""<tr style="background:{rating_color}10">
            <td>{i}</td>
            <td class="brand-name">{b['品牌']}</td>
            <td>{store_s:.0f}</td>
            <td style="color:#f59e0b">{gen_s:.0f}</td>
            <td>{da:.1f}</td>
            <td style="color:{rating_color};font-weight:700">{td_disp} 天</td>
            <td style="color:{rating_color};font-weight:600">{rating}</td>
            <td style="font-size:11px">{fmt_naira(_avg_p)}</td>
            <td style="font-size:11px">{fmt_naira(_fund)} <span style="color:var(--text3)">({_fund_pct:.1f}%)</span></td>
        </tr>""")
    return '\n'.join(rows)

def m6_model_turnover_rows():
    """Generate model-level turnover ranking table rows.
    Formula: 型号周转 = 所有门店仓总可卖数 / 型号日均销量，按日销降序"""
    models = D.get('m6_model_turnover', [])  # 全量(不截断): 截断会让部分品牌只显示少数机型
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
            div.style.cssText = 'padding:7px 12px;cursor:pointer;color:var(--text);font-size:12px;border-bottom:1px solid var(--border)';
            div.textContent = s;
            div.onmouseenter = function() {{ this.style.background = 'var(--surface2)'; }};
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
brand_qty_data_js = '{labels:' + brand_labels + ',datasets:[{label:\'本月销量\',data:' + brand_qty + ',backgroundColor:' + brand_colors + '},{label:\'上月销量\',data:' + brand_may_qty + ',backgroundColor:\'#CBD5E1\'}]}'
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
    <div class="report-text">智能机 <b>{today['smart_qty']:.0f}台</b> + 功能机 <b>{today['feature_qty']:.0f}台</b> = 总销量 <b>{today['total_qty']:.0f}台</b>。营收 <b>₦{today['revenue']/1e6:.1f}M</b>（{fmt_rmb(today['revenue'])}），毛利 <b>₦{today['profit']/1e6:.1f}M</b>（{fmt_rmb(today['profit'])}），毛利率 <b>{today['profit_rate']:.1f}%</b>。日目标完成度 <b style="color:{'#22c55e' if today_vs_target>=100 else '#ef4444'}">{today_vs_target:.0f}%</b>。</div>
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

# ============================================================
# ===== 经营驾驶舱 (Module 13) =====
# ============================================================
CF = D.get('m13_forecast', {}) or {}
IV = D.get('m14_inv_value', {}) or {}
PV = D.get('m15_price_volume', {}) or {}
HL = D.get('m16_store_health', {}) or {}
SO = D.get('m17_stockout', {}) or {}
BM = D.get('m18_brand_matrix', {}) or {}
AI = D.get('m19_ai_insights', {}) or {}

# --- 去年同期同比 (数据源: historical_data.json, 口径同为智能机+平板) ---
YO = {}
if H:
    _mt = (H.get('summaries', {}) or {}).get('monthly_total_phone_sales', {}) or {}
    _cm = int(M.get('current_month', 9))
    _prev_ym = f"2025-{_cm:02d}"
    _lm = f"2026-{_cm - 1:02d}"
    _pylm = f"2025-{_cm - 1:02d}"
    YO = {
        'prev_year_month': _prev_ym,
        'prev_year_full': _mt.get(_prev_ym),
        'last_month': _lm,
        'last_month_qty': _mt.get(_lm),
        'prev_year_last_month': _pylm,
        'prev_year_last_month_qty': _mt.get(_pylm),
        'history_latest': max(_mt.keys()) if _mt else None,
    }
    if YO['prev_year_full']:
        YO['target_vs_prev_year_pct'] = round((float(M['total_target']) - YO['prev_year_full']) / YO['prev_year_full'] * 100, 1)
    if YO['last_month_qty'] and YO['prev_year_last_month_qty']:
        YO['last_month_yoy_pct'] = round((YO['last_month_qty'] - YO['prev_year_last_month_qty']) / YO['prev_year_last_month_qty'] * 100, 1)

_CARD = 'background:var(--surface2);border-radius:10px;padding:14px 16px'
_CARD_T = 'font-size:12px;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:6px'
_MUT = 'color:var(--text2);font-size:12px'


def _sec(num, title, body, mod='cockpit', note=''):
    _n = f'<div style="font-size:11px;color:var(--text2)">{note}</div>' if note else ''
    return f"""<div class="section analysis-only" data-mod="{mod}">
    <div class="section-header">
        <div class="section-title"><span class="num">{num}</span> {title}</div>
        {_n}
    </div>
    <div class="section-body">{body}</div>
</div>"""


def cockpit_summary():
    """一屏经营摘要: 亮点 / 风险 / 建议动作"""
    if not CF:
        return ''
    _st = HL.get('stores', [])
    _tiers = {t['tier']: t for t in D.get('m1_tier_summary', [])}
    _over = _tiers.get('超额', {})
    _top_store = (sorted(D.get('m1_store_target', []), key=lambda x: -x.get('rate', 0)) or [{}])[0]
    _bm = [b for b in BM.get('brands', []) if b['qty'] >= BM.get('qty_cut', 0)]
    _best_margin = max(_bm, key=lambda x: x['profit_rate']) if _bm else None
    _aging = {a['bucket']: a for a in IV.get('aging', [])}
    _fresh = _aging.get('≤30天', {})
    _risk = CF.get('risk', {})
    _light = CF.get('progress_light', {})
    _sc3 = (CF.get('scenarios') or [{}])[0]
    _worst = _st[-1] if _st else None
    _so_top = (SO.get('top_models') or [{}])[0]

    highlights = []
    if _over:
        highlights.append(f"<b>{_over.get('count', 0)} 家</b>门店超额达标，<b>{_top_store.get('short', '-')}</b> 以 <b style=\"color:#16a34a\">{_top_store.get('rate', 0):.1f}%</b> 领跑")
    if _best_margin:
        highlights.append(f"高毛利品牌 <b>{_best_margin['brand']}</b>（量 <b>{_best_margin['qty']:.0f}</b> 台 · 毛利率 <b style=\"color:#16a34a\">{_best_margin['profit_rate']:.1f}%</b>）")
    if _fresh:
        highlights.append(f"库存结构健康：<b>{_fresh.get('fund_pct', 0):.1f}%</b> 资金集中在 30 天内新库龄，<b>{fmt_naira(_fresh.get('fund', 0))}</b>")

    risks = []
    risks.append(f"<b style=\"color:#dc2626\">趋势下行</b>：近 3 日日均 <b>{_sc3.get('daily_avg', 0):.0f}</b> 台 &lt; 需完成 <b>{CF.get('daily_needed', 0):.0f}</b> 台，月底预测 <b>{_sc3.get('proj_rate', 0):.1f}%</b>（缺口 <b>{_sc3.get('gap', 0):.0f}</b> 台）")
    risks.append(f"<b style=\"color:#dc2626\">资金占用</b>：门店库存 <b>₦{IV.get('total_fund', 0) / 1e6:,.0f}M</b>（{fmt_rmb(IV.get('total_fund', 0))}），其中 91 天以上 <b>₦{IV.get('aging_over90_fund', 0) / 1e6:.0f}M</b>（{IV.get('aging_over90_pct', 0):.1f}%）")
    if _worst:
        risks.append(f"<b style=\"color:#dc2626\">门店健康</b>：<b>{HL.get('attention', 0)} 家</b>需关注，最弱 <b>{_worst.get('short', '-')}</b>（{_worst.get('score', 0):.1f} 分）")
    if SO.get('total_lost_units'):
        risks.append(f"<b style=\"color:#dc2626\">缺货损失</b>：{SO.get('model_count', 0)} 个型号断货风险，估算损失 <b>{SO.get('total_lost_units', 0):.0f} 台</b> / <b>₦{SO.get('total_lost_revenue', 0) / 1e6:.1f}M</b>")

    actions = []
    if _so_top:
        actions.append(f"① 紧急补货 <b>{SO.get('model_count', 0)} 个低周转型号</b>，优先 <b>{_so_top.get('brand', '')} {_so_top.get('model', '')}</b>（覆盖仅 {_so_top.get('turnover_days', 0):.1f} 天）")
    if IV.get('aging_over90_fund'):
        actions.append(f"② 清理 91 天以上老库存 <b>₦{IV.get('aging_over90_fund', 0) / 1e6:.0f}M</b>，释放资金")
    if HL.get('attention'):
        actions.append(f"③ 对 <b>{HL.get('attention', 0)} 家</b>需关注门店安排区域经理驻店帮扶")
    if PV.get('benchmark_pct') is not None:
        actions.append(f"④ 调价后 2 日大盘 <b>{PV.get('benchmark_pct', 0):+.1f}%</b>，需持续跟踪调价机型（样本尚小）")

    def _block(title, color, items):
        lis = ''.join(f'<div style="padding:4px 0;line-height:1.65;font-size:12px">• {x}</div>' for x in items) or '<div style="color:var(--text2);font-size:12px">—</div>'
        return f"""<div style="{_CARD}">
            <div style="{_CARD_T};color:{color}">{title}</div>
            {lis}
        </div>"""

    return f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px">
        {_block('✅ 亮点', '#16a34a', highlights)}
        {_block('⚠️ 风险', '#dc2626', risks)}
        {_block('🎯 建议动作', '#2563eb', actions)}
    </div>"""


def cockpit_ai_insights():
    """AI 智能分析: 跨模块交叉关联推理引擎产出的经营洞察"""
    _list = AI.get('insights', [])
    if not _list:
        return ''
    _SEV_META = {
        'high': {'label': '高优先', 'color': '#dc2626', 'bg': 'rgba(220,38,38,0.08)', 'icon': '🔴'},
        'mid': {'label': '关注', 'color': '#ea580c', 'bg': 'rgba(234,88,12,0.08)', 'icon': '🟠'},
        'low': {'label': '机会', 'color': '#2563eb', 'bg': 'rgba(37,99,235,0.08)', 'icon': '🔵'},
        'good': {'label': '健康', 'color': '#16a34a', 'bg': 'rgba(22,163,74,0.08)', 'icon': '🟢'},
    }
    _tag_color = {
        '目标达成': '#dc2626', '库存结构': '#2563eb', '价量归因': '#7c3aed',
        '缺货损失': '#ea580c', '门店健康': '#0891b2', '品牌结构': '#ca8a04',
    }
    _cards = []
    for _i in _list:
        _sev = _SEV_META.get(_i.get('severity'), _SEV_META['low'])
        _tc = _tag_color.get(_i.get('tag'), '#64748b')
        _ev = ''.join(
            f'<div style="padding:2px 0;color:var(--text2);font-size:12px">▸ {e}</div>'
            for e in _i.get('evidence', []))
        _cards.append(f"""<div style="{_CARD};border-left:3px solid {_sev['color']}">
            <div style="{_CARD_T}">
                <span style="font-size:14px">{_sev['icon']}</span>
                <span style="background:{_tc};color:#fff;font-size:10px;padding:2px 8px;border-radius:10px">{_i.get('tag')}</span>
                <span style="background:{_sev['bg']};color:{_sev['color']};font-size:10px;padding:2px 8px;border-radius:10px">{_sev['label']}</span>
            </div>
            <div style="font-size:14px;font-weight:700;line-height:1.5;margin:4px 0 8px">{_i.get('title')}</div>
            <div style="font-size:12.5px;color:var(--text);line-height:1.7;margin-bottom:8px">{_i.get('finding')}</div>
            {_ev}
            <div style="margin-top:8px;padding:8px 10px;background:var(--surface1);border-radius:8px;font-size:12px;line-height:1.6">
                <b style="color:{_sev['color']}">💡 建议：</b>{_i.get('action')}
            </div>
        </div>""")
    _sum = f"""<div style="{_CARD};display:flex;align-items:center;justify-content:center;gap:16px;margin-bottom:12px;flex-wrap:wrap">
        <div style="font-size:13px;color:var(--text2)">共 <b style="color:var(--text);font-size:16px">{AI.get('total', 0)}</b> 条智能洞察</div>
        <span style="color:#dc2626;font-size:12px">🔴 高优先 {AI.get('high', 0)}</span>
        <span style="color:#ea580c;font-size:12px">🟠 关注 {AI.get('mid', 0)}</span>
        <span style="color:#2563eb;font-size:12px">🔵 机会 {AI.get('low', 0)}</span>
        <span style="color:#16a34a;font-size:12px">🟢 健康 {AI.get('good', 0)}</span>
    </div>"""
    return _sum + f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px">{"".join(_cards)}</div>'


def cockpit_forecast():
    """月底达成预测"""
    if not CF:
        return ''
    _risk = CF.get('risk', {})
    _light = CF.get('progress_light', {})
    _scen = CF.get('scenarios', [])
    _cards = ''
    for i, s in enumerate(_scen):
        _col = '#16a34a' if s['proj_rate'] >= 100 else ('#d97706' if s['proj_rate'] >= 97 else '#dc2626')
        _tag = '可完成' if s['proj_rate'] >= 100 else f"缺口 {s['gap']:.0f} 台"
        _hl = 'border:2px solid #2563eb' if i == 0 else 'border:1px solid var(--border)'
        _cards += f"""<div class="kpi-card" style="{_hl}">
            <div class="kpi-label">{s['label']}{' · 当前动能' if i == 0 else ''}</div>
            <div class="kpi-value" style="color:{_col}">{s['proj_rate']:.1f}%</div>
            <div class="kpi-sub">日均 {s['daily_avg']:.0f} 台 → 月底 <b>{s['proj_qty']:,.0f}</b> 台<br>{_tag}</div>
        </div>"""

    _rows = ''.join(
        f"""<tr><td>{c['date']}</td><td style="font-weight:600">{c['smart_qty']:.0f}</td>
        <td style="color:var(--text2)">{c['may_smart']:.0f}</td>
        <td style="color:{'#16a34a' if c['smart_qty'] >= c['may_smart'] else '#dc2626'}">{'▲' if c['smart_qty'] >= c['may_smart'] else '▼'} {abs(c['smart_qty'] - c['may_smart']):.0f}</td></tr>"""
        for c in D.get('m5_company_daily', []))

    return f"""<div class="kpi-row" style="margin-bottom:12px">{_cards}</div>
    <div style="{_CARD};margin-bottom:12px;display:flex;flex-wrap:wrap;gap:18px;align-items:center">
        <div><span style="{_MUT}">完成率 vs 时间进度</span><br>
            <b style="font-size:20px;color:{_light.get('color', '#f59e0b')}">{CF.get('completion_rate', 0):.1f}%</b>
            <span style="{_MUT}"> vs {CF.get('time_progress', 0):.1f}%</span>
            <b style="margin-left:8px;color:{_light.get('color', '#f59e0b')}">{CF.get('progress_diff', 0):+.1f}pp</b>
            <span style="margin-left:6px;font-size:11px;padding:2px 8px;border-radius:10px;background:{_light.get('color', '#f59e0b')}1a;color:{_light.get('color', '#f59e0b')}">{_light.get('level', '-')}灯 · {_light.get('desc', '')}</span>
        </div>
        <div><span style="{_MUT}">趋势</span><br><b style="color:{'#dc2626' if CF.get('trend_dir') == '下行' else '#16a34a'}">{CF.get('trend_dir', '-')}</b>
            <span style="{_MUT}">（斜率 {CF.get('trend_slope', 0):+.1f}/日）</span></div>
        <div><span style="{_MUT}">达成风险</span><br>
            <b style="color:{_risk.get('color', '#f59e0b')}">{_risk.get('level', '-')}</b>
            <span style="{_MUT}"> · {_risk.get('desc', '')}</span></div>
        <div><span style="{_MUT}">需提速</span><br><b style="color:#d97706">{CF.get('needed_uplift_pct', 0):+.1f}%</b>
            <span style="{_MUT}">（{CF.get('daily_avg_now', 0):.0f} → {CF.get('daily_needed', 0):.0f} 台/日）</span></div>
    </div>
    <div class="tbl-wrap" style="max-height:300px"><table>
        <thead><tr><th>日期</th><th>本月智能机</th><th>上月同期</th><th>差异</th></tr></thead>
        <tbody>{_rows}</tbody></table></div>"""


def cockpit_inv_value():
    """库存资金占用 + 库龄"""
    if not IV:
        return ''
    _brands = IV.get('brands', [])
    _brows = ''.join(
        f"""<tr><td class="brand-name">{b['品牌']}</td><td>{b.get('qty', 0):,.0f}</td>
        <td style="font-size:11px">{fmt_naira(b.get('avg_price', 0))}</td>
        <td style="font-weight:600">{fmt_naira(b.get('fund', 0))}</td>
        <td style="color:var(--text2)">{b.get('fund_pct', 0):.1f}%</td>
        <td>{'∞' if (b.get('turnover_days') or 9999) >= 9999 else f"{b.get('turnover_days', 0):.0f}"} 天</td></tr>"""
        for b in _brands)

    _maxfund = max([a.get('fund', 0) for a in IV.get('aging', [])] or [1]) or 1
    _abars = ''
    for a in IV.get('aging', []):
        _w = a.get('fund', 0) / _maxfund * 100
        _col = '#16a34a' if a['bucket'] in ('≤30天', '31-60天') else ('#d97706' if a['bucket'] == '61-90天' else '#dc2626')
        _abars += f"""<div style="display:flex;align-items:center;gap:10px;padding:3px 0">
            <span style="width:70px;font-size:12px;color:var(--text2)">{a['bucket']}</span>
            <div style="flex:1;background:var(--border);height:16px;border-radius:4px;overflow:hidden">
                <div style="width:{_w:.1f}%;height:100%;background:{_col}"></div></div>
            <span style="width:150px;text-align:right;font-size:12px"><b>{fmt_naira(a.get('fund', 0))}</b> <span style="color:var(--text2)">{a.get('fund_pct', 0):.1f}%</span></span>
            <span style="width:80px;text-align:right;font-size:11px;color:var(--text2)">{a.get('qty', 0):,.0f} 台</span>
        </div>"""

    _srows = ''.join(
        f"""<tr><td class="store-name">{s['store']}</td><td>{s.get('stock', 0):,.0f}</td>
        <td style="font-weight:600">{fmt_naira(s.get('fund', 0))}</td>
        <td>{'∞' if s.get('turnover_days') is None else f"{s['turnover_days']:.1f}"} 天</td></tr>"""
        for s in IV.get('top_stores', []))

    return f"""<div class="kpi-row" style="margin-bottom:12px">
        <div class="kpi-card"><div class="kpi-label">门店库存资金占用</div>
            <div class="kpi-value" style="color:#2563eb">{fmt_naira(IV.get('total_fund', 0))}</div>
            <div class="kpi-sub">{fmt_rmb(IV.get('total_fund', 0))} · {IV.get('total_stock', 0):,.0f} 台</div></div>
        <div class="kpi-card"><div class="kpi-label">91 天以上老库存</div>
            <div class="kpi-value" style="color:#dc2626">{fmt_naira(IV.get('aging_over90_fund', 0))}</div>
            <div class="kpi-sub">占资金 {IV.get('aging_over90_pct', 0):.1f}% · {IV.get('aging_over90_qty', 0):,.0f} 台</div></div>
        <div class="kpi-card"><div class="kpi-label">压资金最多门店</div>
            <div class="kpi-value" style="font-size:18px">{IV.get('top_stores', [{}])[0].get('store', '-')}</div>
            <div class="kpi-sub">{fmt_naira(IV.get('top_stores', [{}])[0].get('fund', 0))}</div></div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px">
        <div style="{_CARD}">
            <div style="{_CARD_T}">库龄结构（按资金占用）</div>
            {_abars}
        </div>
        <div style="{_CARD}">
            <div style="{_CARD_T}">压资金 TOP10 门店</div>
            <div class="tbl-wrap" style="max-height:260px"><table><thead><tr><th>门店</th><th>库存</th><th>资金占用</th><th>周转</th></tr></thead><tbody>{_srows}</tbody></table></div>
        </div>
    </div>
    <div class="tbl-wrap" style="margin-top:12px;max-height:420px"><table>
        <thead><tr><th>品牌</th><th>库存台数</th><th>平均单价</th><th>资金占用</th><th>占比</th><th>周转天数</th></tr></thead>
        <tbody>{_brows}</tbody></table></div>"""


def cockpit_price_volume():
    """价量联动归因"""
    if not PV:
        return ''
    _up = PV.get('increases', {}) or {}
    _dn = PV.get('decreases', {}) or {}
    _bench = PV.get('benchmark_pct')
    _pd = PV.get('post_days') or 2

    def _rel(v):
        if v is None or _bench is None:
            return ''
        _r = v - _bench
        return f'<span style="color:{"#16a34a" if _r >= 0 else "#dc2626"};font-size:11px">相对大盘 {_r:+.1f}pp</span>'

    _rows = ''
    for c in PV.get('detail', []):
        _dir = '涨' if (c.get('pct') or 0) > 0 else '降'
        _dc = '#dc2626' if _dir == '涨' else '#16a34a'
        _pv = c.get('post_vs_pre')
        _pvc = '#16a34a' if (_pv or 0) >= 0 else '#dc2626'
        _rows += f"""<tr>
            <td>{c.get('brand', '')}</td><td class="model-name">{c.get('model', '')}</td>
            <td>{fmt_naira(c.get('cmp_price') or 0)} → {fmt_naira(c.get('cur_price') or 0)}</td>
            <td style="color:{_dc};font-weight:700">{_dir} {abs(c.get('pct') or 0):.1f}%</td>
            <td>{c.get('june_sales_qty') if c.get('june_sales_qty') is not None else '—'}</td>
            <td>{c.get('pre_daily_avg') if c.get('pre_daily_avg') is not None else '—'}</td>
            <td>{c.get('post_daily_avg') if c.get('post_daily_avg') is not None else '—'}</td>
            <td style="color:{_pvc};font-weight:600">{f"{_pv:+.1f}%" if _pv is not None else '—'}</td>
            <td>{f"{c.get('mom_sales_change'):+.1f}%" if c.get('mom_sales_change') is not None else '—'}</td>
        </tr>"""

    return f"""<div class="kpi-row" style="margin-bottom:8px">
        <div class="kpi-card"><div class="kpi-label">涨价机型</div>
            <div class="kpi-value" style="color:#dc2626">{_up.get('count', 0)}<small>个</small></div>
            <div class="kpi-sub">平均涨价 {_up.get('avg_price_pct') or 0:+.1f}% · 调价后日均变化 <b style="color:{'#16a34a' if (_up.get('avg_post_vs_pre') or 0) >= 0 else '#dc2626'}">{f"{_up.get('avg_post_vs_pre'):+.1f}%" if _up.get('avg_post_vs_pre') is not None else '—'}</b><br>{_rel(_up.get('avg_post_vs_pre'))}</div></div>
        <div class="kpi-card"><div class="kpi-label">降价机型</div>
            <div class="kpi-value" style="color:#16a34a">{_dn.get('count', 0)}<small>个</small></div>
            <div class="kpi-sub">平均降价 {_dn.get('avg_price_pct') or 0:+.1f}% · 调价后日均变化 <b style="color:{'#16a34a' if (_dn.get('avg_post_vs_pre') or 0) >= 0 else '#dc2626'}">{f"{_dn.get('avg_post_vs_pre'):+.1f}%" if _dn.get('avg_post_vs_pre') is not None else '—'}</b><br>{_rel(_dn.get('avg_post_vs_pre'))}</div></div>
        <div class="kpi-card"><div class="kpi-label">同期大盘基准</div>
            <div class="kpi-value" style="color:{'#16a34a' if (_bench or 0) >= 0 else '#dc2626'}">{f"{_bench:+.1f}%" if _bench is not None else '—'}</div>
            <div class="kpi-sub">调价前后 {_pd} 日整体变化<br>需扣除大盘因素再判断调价效果</div></div>
    </div>
    <div style="font-size:11px;color:var(--text2);margin-bottom:10px;line-height:1.7">
        ⚠️ 口径说明：调价生效日为价格表更新日（本次 {PS.get('current_price_date', '-')}），"调价后日均"样本仅 {_pd} 个营业日，波动较大，仅供初步跟踪；
        "相对大盘" = 机型变化 − 同期大盘变化，用于剥离市场整体涨跌的影响。
    </div>
    <div class="tbl-wrap" style="max-height:460px"><table>
        <thead><tr><th>品牌</th><th>型号</th><th>价格变化</th><th>调价幅度</th><th>本月销量</th><th>调价前日均</th><th>调价后日均</th><th>调价后变化</th><th>本月同比</th></tr></thead>
        <tbody>{_rows}</tbody></table></div>"""


def cockpit_health():
    """门店健康度综合评分"""
    if not HL:
        return ''
    _stores = HL.get('stores', [])
    _dist = [('优秀', HL.get('excellent', 0), '#16a34a'), ('良好', HL.get('good', 0), '#2563eb'),
             ('一般', HL.get('normal', 0), '#d97706'), ('需关注', HL.get('attention', 0), '#dc2626')]
    _dcards = ''.join(
        f"""<div class="kpi-card"><div class="kpi-label">{n}</div>
        <div class="kpi-value" style="color:{c}">{v}<small>家</small></div>
        <div class="kpi-sub">{v / max(len(_stores), 1) * 100:.0f}% 的门店</div></div>""" for n, v, c in _dist)

    def _row(s):
        _col = s.get('color', '#64748b')
        _td = s.get('turnover_days')
        return f"""<tr>
            <td style="font-weight:700">{s.get('short', '-')}</td>
            <td style="color:{_col};font-weight:700">{s.get('score', 0):.1f}</td>
            <td><span style="font-size:11px;padding:2px 8px;border-radius:10px;background:{_col}1a;color:{_col}">{s.get('level', '-')}</span></td>
            <td>{f"{s.get('rate', 0):.1f}%" if s.get('rate') is not None else '—'}</td>
            <td>{'∞' if _td is None else f"{_td:.1f} 天"}</td>
            <td>{f"{s.get('cv', 0):.1f}%" if s.get('cv') is not None else '—'}</td>
            <td>{f"{s.get('eff', 0):.1f}" if s.get('eff') is not None else '—'}</td>
            <td style="color:var(--text2)">{s.get('staff_count') or '—'}</td>
        </tr>"""

    _rows = ''.join(_row(s) for s in _stores)
    return f"""<div class="kpi-row" style="margin-bottom:8px">{_dcards}</div>
    <div style="font-size:11px;color:var(--text2);margin-bottom:10px;line-height:1.7">
        评分口径：四维度按全公司百分位排名后加权 —— <b>达成率 40%</b> + <b>库存周转 25%</b>（越快越高）+ <b>日销稳定性 20%</b>（CV 越低越高）+ <b>人均产出 15%</b>。满分 100。
    </div>
    <div class="tbl-wrap" style="max-height:520px"><table id="tbl_health">
        <thead><tr><th>门店</th><th>健康分</th><th>评级</th><th>达成率</th><th>周转</th><th>日销CV</th><th>人均台数</th><th>人数</th></tr></thead>
        <tbody>{_rows}</tbody></table></div>"""


def cockpit_stockout():
    """缺货损失估算"""
    if not SO:
        return ''
    _mrows = ''.join(
        f"""<tr><td>{m.get('brand', '')}</td><td class="model-name">{m.get('model', '')}</td>
        <td>{m.get('turnover_days', 0):.1f} 天</td><td>{m.get('daily_avg_sales', 0):.1f}</td>
        <td style="color:#dc2626">{m.get('short_days', 0):.1f} 天</td>
        <td style="color:#dc2626;font-weight:700">{m.get('lost_units', 0):.0f} 台</td>
        <td>{fmt_naira(m.get('lost_revenue', 0))}</td></tr>"""
        for m in SO.get('top_models', []))
    _brows = ''.join(
        f"""<tr><td class="brand-name">{b['brand']}</td><td>{b.get('models', 0)}</td>
        <td>{b.get('lost_units', 0):.0f} 台</td><td>{fmt_naira(b.get('lost_revenue', 0))}</td></tr>"""
        for b in SO.get('brands', []))
    _days = SO.get('assumption_days', 7)
    return f"""<div class="kpi-row" style="margin-bottom:12px">
        <div class="kpi-card"><div class="kpi-label">估算损失销量</div>
            <div class="kpi-value" style="color:#dc2626">{SO.get('total_lost_units', 0):,.0f}<small>台</small></div>
            <div class="kpi-sub">占月目标 {SO.get('total_lost_units', 0) / max(float(M['total_target']), 1) * 100:.1f}%</div></div>
        <div class="kpi-card"><div class="kpi-label">估算损失营收</div>
            <div class="kpi-value" style="color:#dc2626">{fmt_naira(SO.get('total_lost_revenue', 0))}</div>
            <div class="kpi-sub">{fmt_rmb(SO.get('total_lost_revenue', 0))}</div></div>
        <div class="kpi-card"><div class="kpi-label">缺货风险型号</div>
            <div class="kpi-value">{SO.get('model_count', 0)}<small>个</small></div>
            <div class="kpi-sub">周转 &lt; {_days:.0f} 天（补货周期）</div></div>
    </div>
    <div style="font-size:11px;color:var(--text2);margin-bottom:10px;line-height:1.7">
        ⚠️ 估算口径：假设补货周期 <b>{_days:.0f} 天</b>，型号当前库存覆盖天数 &lt; 补货周期即为缺货风险。
        损失台数 = (补货周期 − 当前周转) × 日均销量 × (剩余 {CF.get('remaining_days', 0)} 天 ÷ 补货周期)，上限为剩余天数。价格为库存平均单价。
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px">
        <div><div style="{_CARD_T}">按品牌汇总</div>
            <div class="tbl-wrap" style="max-height:300px"><table><thead><tr><th>品牌</th><th>型号数</th><th>损失台数</th><th>损失营收</th></tr></thead><tbody>{_brows}</tbody></table></div></div>
        <div><div style="{_CARD_T}">TOP 缺货型号</div>
            <div class="tbl-wrap" style="max-height:300px"><table><thead><tr><th>品牌</th><th>型号</th><th>周转</th><th>日均</th><th>缺口天数</th><th>损失台数</th><th>损失营收</th></tr></thead><tbody>{_mrows}</tbody></table></div></div>
    </div>"""


def cockpit_brand_matrix():
    """品牌毛利结构象限"""
    if not BM:
        return ''
    _cut_q = BM.get('qty_cut', 0)
    _cut_p = BM.get('margin_cut', 0)
    _order = {'双优（明星）': 0, '走量低利': 1, '高利小众': 2, '双低（调整）': 3}
    _quads = {}
    for b in BM.get('brands', []):
        _quads.setdefault(b['quadrant'], []).append(b)
    _cells = ''
    for q in sorted(_quads.keys(), key=lambda x: _order.get(x, 9)):
        _items = _quads[q]
        _col = _items[0].get('color', '#64748b')
        _chips = ''.join(
            f"""<div style="display:flex;justify-content:space-between;gap:8px;padding:4px 8px;border-radius:6px;background:var(--surface);margin:3px 0;font-size:12px">
                <span style="font-weight:600">{b['brand']}</span>
                <span style="color:var(--text2)">{b['qty']:.0f} 台 · {b['profit_rate']:.1f}%</span></div>""" for b in _items)
        _cells += f"""<div style="{_CARD};border-left:3px solid {_col}">
            <div style="{_CARD_T};color:{_col}">{q} <span style="color:var(--text2);font-weight:400">({len(_items)} 个品牌)</span></div>
            {_chips}</div>"""

    _rows = ''.join(
        f"""<tr><td class="brand-name">{b['brand']}</td><td>{b['qty']:,.0f}</td>
        <td>{fmt_naira(b['revenue'])}</td><td>{fmt_naira(b['profit'])}</td>
        <td style="font-weight:600">{b['profit_rate']:.1f}%</td>
        <td><span style="font-size:11px;padding:2px 8px;border-radius:10px;background:{b.get('color', '#64748b')}1a;color:{b.get('color', '#64748b')}">{b['quadrant']}</span></td></tr>"""
        for b in BM.get('brands', []))

    return f"""<div style="font-size:11px;color:var(--text2);margin-bottom:10px">
        切分线：销量均值 <b>{_cut_q:,.0f} 台</b>｜毛利率均值 <b>{_cut_p:.1f}%</b>。右上=量利双优，左上=高利小众，右下=走量低利，左下=需调整。
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-bottom:12px">{_cells}</div>
    <div class="tbl-wrap" style="max-height:340px"><table>
        <thead><tr><th>品牌</th><th>销量</th><th>营收</th><th>毛利</th><th>毛利率</th><th>象限</th></tr></thead>
        <tbody>{_rows}</tbody></table></div>"""


def cockpit_yoy():
    """去年同期同比"""
    if not YO:
        return ''
    _tgt = float(M['total_target'])
    _pf = YO.get('prev_year_full')
    def _card(label, cur, prev, cur_label, prev_label, pct, pct_label):
        _col = '#16a34a' if (pct or 0) >= 0 else '#dc2626'
        return f"""<div class="kpi-card"><div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{_col}">{f"{pct:+.1f}%" if pct is not None else '—'}</div>
        <div class="kpi-sub">{cur_label} <b>{cur:,.0f}</b> vs {prev_label} <b>{prev:,.0f}</b><br>{pct_label}</div></div>"""
    _c1 = _card(f"{M.get('current_month', 9)}月目标 vs 去年同期全月", _tgt, _pf or 0,
                f"{M.get('current_month', 9)}月目标", f"2025-{int(M.get('current_month', 9)):02d} 实际",
                YO.get('target_vs_prev_year_pct'), '目标同比')
    _c2 = _card(f"{int(M.get('current_month', 9)) - 1}月实际同比", YO.get('last_month_qty') or 0,
                YO.get('prev_year_last_month_qty') or 0, YO.get('last_month', ''), YO.get('prev_year_last_month', ''),
                YO.get('last_month_yoy_pct'), '整月对比')
    _c3 = f"""<div class="kpi-card"><div class="kpi-label">去年同期全月销量</div>
        <div class="kpi-value">{(_pf or 0):,.0f}<small>台</small></div>
        <div class="kpi-sub">{YO.get('prev_year_month', '')} 全月（智能机+平板）<br>可作为本月目标对标基准</div></div>"""
    return f"""<div class="kpi-row" style="margin-bottom:8px">{_c1}{_c2}{_c3}</div>
    <div style="font-size:11px;color:#b45309;background:#fef3c7;border-radius:8px;padding:8px 12px;line-height:1.7">
        ⚠️ 口径提示：同比数据来自历史月度文件（智能机+平板口径），历史月份包含当时仍营业、现已关闭的门店（IGANDO、MSL MUSHIN2），
        因此同比基数略偏高；本月目标已按现营 72 家门店重算。历史数据最新月份为 {YO.get('history_latest', '-')}。
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

    # Raw monthly data for JS-side month filter & YoY/MoM analysis
    hist_data_js = json.dumps({
        'months': sorted_months,
        'brand': hbrand,
        'rev': {m: rev_monthly.get(m, 0) for m in sorted_months},
        'profit': {m: profit_monthly.get(m, 0) for m in sorted_months},
        'sales': {m: (mt.get(m, 0) or 0) for m in sorted_months}
    })

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

<!-- Brand YoY / MoM Analysis -->
<div class="section">
    <div class="section-header">
        <div class="section-title">🔁 品牌同比 / 环比分析</div>
        <select id="sel_brand_yoy_month" onchange="updateBrandYoY(this.value)" style="margin-left:auto;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);font-size:12px;font-family:var(--font)"></select>
    </div>
    <div class="section-body">
        <div id="brand_yoy_analysis" class="hist-analysis" style="margin-bottom:12px"></div>
        <div class="tbl-wrap" style="max-height:430px">
            <table id="tbl_brand_yoy"><thead><tr>
                <th>品牌</th><th>上月销量</th><th>环比</th><th>去年同月</th><th>本月销量</th><th>同比</th><th>2026累计</th><th>累计占比</th>
            </tr></thead><tbody></tbody></table>
        </div>
    </div>
</div>

<!-- Chart 3: YoY Growth + Revenue/Profit -->
<div class="section">
    <div class="section-header">
        <div class="section-title">📊 营收毛利 & 品牌贡献</div>
        <select id="sel_rev_month" onchange="updateRevFilter(this.value)" style="margin-left:auto;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);font-size:12px;font-family:var(--font)"></select>
    </div>
    <div class="section-body">
        <div id="rev_profit_analysis" class="hist-analysis" style="margin-bottom:12px"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
            <div><h4 style="margin:0 0 8px;font-size:13px;color:var(--text2)">月度销售额 & 毛利 (百万₦)</h4><div style="height:320px"><canvas id="chart_history_rev_profit"></canvas></div></div>
            <div><h4 style="margin:0 0 8px;font-size:13px;color:var(--text2)">品牌贡献 TOP8 <span id="brand_contrib_scope" style="font-weight:400">（2026累计）</span></h4><div style="height:320px"><canvas id="chart_history_brand_contrib"></canvas></div></div>
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
var _chartRevProfit = null, _chartBrandContrib = null;
var HIST = {hist_data_js};
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
    const _bgC = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
    const _isDarkC = _bgC.startsWith('#0') || _bgC.startsWith('#1');
    const _dlFont = {{ family: "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif" }};
    _chartBrandContrib = new Chart(document.getElementById('chart_history_brand_contrib'), {{
        type: 'doughnut',
        data: {{
            labels: {brand_rank_labels_js},
            datasets: [{{
                data: {brand_rank_pct_js},
                backgroundColor: ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16'],
                borderColor: _isDarkC ? '#1e293b' : '#ffffff',
                borderWidth: 2,
                hoverOffset: 6
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            cutout: '58%',
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', usePointStyle: true, boxWidth: 10, padding: 8, font: {{ size: 10, family: _dlFont.family }}, generateLabels: function(chart) {{
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
                tooltip: {{ callbacks: {{ label: ctx => ctx.label + ': ' + ctx.parsed + '%' }} }},
                datalabels: {{ color: '#fff', font: {{ size: 10, weight: 'bold', family: _dlFont.family }}, formatter: (v) => v >= 4 ? v.toFixed(1) + '%' : '' }}
            }}
        }}
    }});

    // Chart 4: Revenue & Profit
    _chartRevProfit = new Chart(document.getElementById('chart_history_rev_profit'), {{
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
    _initHistFilters();
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
    # Plain (non-f-string) JS for brand YoY/MoM & month filter — single braces OK
    history_js += """
// ===== Brand YoY/MoM & Month Filter =====
function _mLabel(m) { var p = m.split('-'); return p[0].slice(2) + '年' + parseInt(p[1], 10) + '月'; }
function _prevMonth(m) { var y = parseInt(m.split('-')[0], 10), mo = parseInt(m.split('-')[1], 10) - 1; if (mo === 0) { mo = 12; y--; } return y + '-' + (mo < 10 ? '0' + mo : mo); }
function _prevYear(m) { return (parseInt(m.split('-')[0], 10) - 1) + '-' + m.split('-')[1]; }
function _pctHtml(v) {
    if (v === null || v === undefined || !isFinite(v)) return '<span style="color:var(--text2)">—</span>';
    var c = v >= 0 ? '#22c55e' : '#ef4444';
    return '<span style="color:' + c + ';font-weight:600">' + (v >= 0 ? '+' : '') + v.toFixed(1) + '%</span>';
}
function _pctTxt(v) {
    if (v === null || v === undefined || !isFinite(v)) return '—';
    return (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
}
function _fmtM(v) { return '₦' + (v / 1e6).toLocaleString(undefined, { maximumFractionDigits: 1 }) + 'M'; }

window.updateBrandYoY = function(month) {
    var b26 = HIST.brand['2026'] || {}, b25 = HIST.brand['2025'] || {};
    var names = {};
    Object.keys(b26).forEach(function(b){ names[b] = 1; });
    Object.keys(b25).forEach(function(b){ names[b] = 1; });
    var pm = _prevMonth(month);
    var lyKey = _prevYear(month);
    var months26 = HIST.months.filter(function(m){ return m.indexOf('2026-') === 0; });
    var rows = [], ytdTotal = 0;
    Object.keys(names).forEach(function(b) {
        var cur = (b26[b] && b26[b][month]) || 0;
        var prev = ((b26[b] && b26[b][pm]) || (b25[b] && b25[b][pm])) || 0;
        var ly = (b25[b] && b25[b][lyKey]) || 0;
        var ytd = 0;
        months26.forEach(function(m){ ytd += (b26[b] && b26[b][m]) || 0; });
        ytdTotal += ytd;
        rows.push({ b: b, cur: cur, prev: prev, ly: ly, ytd: ytd });
    });
    rows.sort(function(a, b2) { return b2.cur - a.cur; });
    var tCur = 0, tPrev = 0, tLy = 0;
    rows.forEach(function(r){ tCur += r.cur; tPrev += r.prev; tLy += r.ly; });
    var html = '';
    rows.forEach(function(r) {
        var mom = r.prev > 0 ? (r.cur - r.prev) / r.prev * 100 : null;
        var yoy = r.ly > 0 ? (r.cur - r.ly) / r.ly * 100 : null;
        var share = ytdTotal > 0 ? r.ytd / ytdTotal * 100 : 0;
        html += '<tr><td style="font-weight:600">' + r.b + '</td><td>' + Math.round(r.prev).toLocaleString() + '</td><td>' + _pctHtml(mom) + '</td><td>' + Math.round(r.ly).toLocaleString() + '</td><td style="font-weight:700">' + Math.round(r.cur).toLocaleString() + '</td><td>' + _pctHtml(yoy) + '</td><td>' + Math.round(r.ytd).toLocaleString() + '</td><td>' + share.toFixed(1) + '%</td></tr>';
    });
    var tMom = tPrev > 0 ? (tCur - tPrev) / tPrev * 100 : null;
    var tYoy = tLy > 0 ? (tCur - tLy) / tLy * 100 : null;
    html += '<tr style="font-weight:700"><td>全品牌合计</td><td>' + Math.round(tPrev).toLocaleString() + '</td><td>' + _pctHtml(tMom) + '</td><td>' + Math.round(tLy).toLocaleString() + '</td><td>' + Math.round(tCur).toLocaleString() + '</td><td>' + _pctHtml(tYoy) + '</td><td>' + Math.round(ytdTotal).toLocaleString() + '</td><td>100%</td></tr>';
    document.querySelector('#tbl_brand_yoy tbody').innerHTML = html;

    var items = [];
    items.push('📅 <b>' + _mLabel(month) + '</b>：全品牌 <b>' + Math.round(tCur).toLocaleString() + '台</b>，环比 ' + _pctTxt(tMom) + '，同比 ' + _pctTxt(tYoy));
    var byYoy = rows.filter(function(r){ return r.ly >= 100 && r.cur > 0; }).map(function(r){ return { b: r.b, v: (r.cur - r.ly) / r.ly * 100 }; }).sort(function(a, b2){ return b2.v - a.v; });
    if (byYoy.length >= 2) {
        items.push('📈 <b>同比最佳</b>：' + byYoy[0].b + ' ' + _pctTxt(byYoy[0].v) + '；<b>同比最弱</b>：' + byYoy[byYoy.length - 1].b + ' ' + _pctTxt(byYoy[byYoy.length - 1].v));
    }
    var byMom = rows.filter(function(r){ return r.prev >= 100 && r.cur > 0; }).map(function(r){ return { b: r.b, v: (r.cur - r.prev) / r.prev * 100 }; }).sort(function(a, b2){ return b2.v - a.v; });
    if (byMom.length >= 2) {
        items.push('🔄 <b>环比最佳</b>：' + byMom[0].b + ' ' + _pctTxt(byMom[0].v) + '；<b>环比最弱</b>：' + byMom[byMom.length - 1].b + ' ' + _pctTxt(byMom[byMom.length - 1].v));
    }
    if (rows.length && rows[0].cur > 0) {
        items.push('🥇 <b>' + _mLabel(month) + '销量第一</b>：' + rows[0].b + ' ' + Math.round(rows[0].cur).toLocaleString() + '台，占当月 ' + (tCur > 0 ? (rows[0].cur / tCur * 100).toFixed(1) : '0') + '%');
    }
    document.getElementById('brand_yoy_analysis').innerHTML = items.map(function(i){ return '<div class="ai">' + i + '</div>'; }).join('');
};

function _contribData(month) {
    var b26 = HIST.brand['2026'] || {};
    var months26 = HIST.months.filter(function(m){ return m.indexOf('2026-') === 0; });
    var per = {}, tot = 0;
    if (month) {
        Object.keys(b26).forEach(function(b){ per[b] = (b26[b] && b26[b][month]) || 0; });
        tot = HIST.sales[month] || 0;
    } else {
        Object.keys(b26).forEach(function(b){ per[b] = months26.reduce(function(s, m){ return s + ((b26[b] && b26[b][m]) || 0); }, 0); });
        tot = months26.reduce(function(s, m){ return s + (HIST.sales[m] || 0); }, 0);
    }
    var arr = Object.keys(per).map(function(b){ return { b: b, v: per[b] }; }).sort(function(a, b2){ return b2.v - a.v; }).slice(0, 8);
    return {
        labels: arr.map(function(r){ return r.b; }),
        data: arr.map(function(r){ return tot > 0 ? +(r.v / tot * 100).toFixed(1) : 0; })
    };
}
function _updateContribChart(month) {
    if (!_chartBrandContrib) return;
    var d = _contribData(month);
    _chartBrandContrib.data.labels = d.labels;
    _chartBrandContrib.data.datasets[0].data = d.data;
    _chartBrandContrib.update();
    document.getElementById('brand_contrib_scope').textContent = month ? '（' + _mLabel(month) + '）' : '（2026累计）';
}

window.updateRevFilter = function(v) {
    var items = [];
    var months26 = HIST.months.filter(function(m){ return m.indexOf('2026-') === 0; });
    if (v === 'all') {
        var rev = 0, prof = 0, rev25 = 0, prof25 = 0;
        months26.forEach(function(m){
            rev += HIST.rev[m] || 0; prof += HIST.profit[m] || 0;
            var py = _prevYear(m);
            rev25 += HIST.rev[py] || 0; prof25 += HIST.profit[py] || 0;
        });
        var mg = rev > 0 ? prof / rev * 100 : 0;
        var rYoy = rev25 > 0 ? (rev - rev25) / rev25 * 100 : null;
        var pYoy = prof25 > 0 ? (prof - prof25) / prof25 * 100 : null;
        items.push('📊 <b>2026累计（' + months26.length + '个月）</b>：营收 ' + _fmtM(rev) + '，毛利 ' + _fmtM(prof) + '，毛利率 ' + mg.toFixed(1) + '%');
        items.push('📅 同比2025同期：营收 ' + _pctTxt(rYoy) + '，毛利 ' + _pctTxt(pYoy));
        var cd = _contribData(null);
        if (cd.labels.length) {
            items.push('🥇 <b>贡献第一</b>：' + cd.labels[0] + ' ' + cd.data[0].toFixed(1) + '%（2026累计份额）');
        }
        document.getElementById('rev_profit_analysis').innerHTML = items.map(function(i){ return '<div class="ai">' + i + '</div>'; }).join('');
        _updateContribChart(null);
        if (_chartRevProfit) {
            _chartRevProfit.data.datasets.forEach(function(ds){ ds.pointRadius = 3; ds.pointHoverRadius = 6; });
            _chartRevProfit.update();
        }
    } else {
        var m = v, pm = _prevMonth(m), py = _prevYear(m);
        var rev = HIST.rev[m] || 0, prof = HIST.profit[m] || 0;
        var revP = HIST.rev[pm], profP = HIST.profit[pm];
        var revY = HIST.rev[py], profY = HIST.profit[py];
        var sCur = HIST.sales[m] || 0, sPrev = HIST.sales[pm] || 0, sLy = HIST.sales[py] || 0;
        var rMom = revP ? (rev - revP) / revP * 100 : null;
        var rYoy = revY ? (rev - revY) / revY * 100 : null;
        var pMom = profP ? (prof - profP) / profP * 100 : null;
        var mg = rev > 0 ? prof / rev * 100 : 0;
        var sMom = sPrev > 0 ? (sCur - sPrev) / sPrev * 100 : null;
        var sYoy = sLy > 0 ? (sCur - sLy) / sLy * 100 : null;
        items.push('📅 <b>' + _mLabel(m) + '</b>：营收 ' + _fmtM(rev) + '（环比 ' + _pctTxt(rMom) + '｜同比 ' + _pctTxt(rYoy) + '），毛利 ' + _fmtM(prof) + '（环比 ' + _pctTxt(pMom) + '），毛利率 ' + mg.toFixed(1) + '%');
        items.push('📦 销量 ' + Math.round(sCur).toLocaleString() + '台（环比 ' + _pctTxt(sMom) + '｜同比 ' + _pctTxt(sYoy) + '）');
        var cd = _contribData(m);
        if (cd.labels.length && cd.labels.length > 1) {
            items.push('🥇 <b>当月第一</b>：' + cd.labels[0] + ' 占 ' + cd.data[0].toFixed(1) + '%；第二 ' + cd.labels[1] + ' 占 ' + (cd.data[1] || 0).toFixed(1) + '%');
        }
        document.getElementById('rev_profit_analysis').innerHTML = items.map(function(i){ return '<div class="ai">' + i + '</div>'; }).join('');
        _updateContribChart(m);
        if (_chartRevProfit) {
            var idx = HIST.months.indexOf(m);
            _chartRevProfit.data.datasets.forEach(function(ds){
                ds.pointRadius = HIST.months.map(function(_, i){ return i === idx ? 7 : 3; });
                ds.pointHoverRadius = 9;
            });
            _chartRevProfit.update();
        }
    }
};

function _initHistFilters() {
    if (window._histFiltersInit) return;
    window._histFiltersInit = true;
    var months26 = HIST.months.filter(function(m){ return m.indexOf('2026-') === 0; });
    var selB = document.getElementById('sel_brand_yoy_month');
    if (selB) selB.innerHTML = months26.slice().reverse().map(function(m){ return '<option value="' + m + '">' + _mLabel(m) + '</option>'; }).join('');
    var selR = document.getElementById('sel_rev_month');
    if (selR) selR.innerHTML = '<option value="all">2026累计</option>' + HIST.months.slice().reverse().map(function(m){ return '<option value="' + m + '">' + _mLabel(m) + '</option>'; }).join('');
    if (months26.length) window.updateBrandYoY(months26[months26.length - 1]);
    window.updateRevFilter('all');
}
"""
else:
    history_page_html = ''
    history_js = ''

# ===== 表格底部合计行 (通用模块) =====
# 说明: 用普通字符串定义(非 f-string), 避免 JS 花括号被 Python 转义
# 列规则: '' = 留空 | 含 {n} = 文本标签(n=行数) | 'sum'/'sum1' = 求和 |
#         'money'/'money0' = 金额 | 'tick' = 统计✓数量 |
#         ['ratio',分子列,分母列,'pct'|'num0'|'money0'] = 除法 |
#         ['wavg',权重列,'pct'|'num1'|'money0'] = 加权平均
TABLE_TOTALS_JS = """
<script>
/* ===== Table footer totals ===== */
(function(){
  function tfNum(td){
    if(!td) return null;
    var t=(td.textContent||'').trim();
    if(!t||t==='—'||t==='-'||t==='∞'||t==='N/A'||t==='已缺货') return null;
    var m=t.replace(/,/g,'').match(/-?\\d+(?:\\.\\d+)?\\s*[MK]?/);
    if(!m) return null;
    var s=m[0], v=parseFloat(s);
    if(isNaN(v)) return null;
    if(s.indexOf('M')>=0) v*=1e6; else if(s.indexOf('K')>=0) v*=1e3;
    return v;
  }
  function fNum(v,d){ return v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}); }
  function fmt(kind,v){
    if(v===null||v===undefined||isNaN(v)) return '';
    if(kind==='money'){ if(Math.abs(v)>=1e6) return '₦'+fNum(v/1e6,1)+'M'; if(Math.abs(v)>=1e3) return '₦'+fNum(v/1e3,0)+'K'; return '₦'+fNum(v,0); }
    if(kind==='money0') return '₦'+fNum(v,0);
    if(kind==='pct') return fNum(v,1)+'%';
    if(kind==='sum1'||kind==='num1') return fNum(v,1);
    return fNum(v,0);
  }
  var CFG=[
    {sel:'#tbl-model', vis:function(r){ return !r.dataset.m10Hidden; },
     cols:{2:'合计 {n} 个型号',3:'sum',4:'sum1',8:['wavg',3,'money0'],10:['wavg',3,'pct'],11:'sum',12:['ratio',11,4,'num0']}},
    {sel:'#tbl_m1', cols:{1:'合计 {n} 家门店',2:'sum',3:'sum',4:['ratio',3,2,'pct'],5:'sum',6:'sum'}},
    {sel:'#tbl_m3', cols:{1:'合计 {n} 个品牌',2:'sum',4:'money',5:'money',6:['ratio',4,2,'money0'],7:['ratio',5,2,'money0'],8:['ratio',5,4,'pct'],9:['wavg',2,'pct']}},
    {sel:'#tbl_m4', cols:{0:'合计 {n} 家门店',1:'sum',2:'sum',3:'sum',4:'sum',5:'sum',6:'sum',7:'tick',8:'sum'}},
    {sel:'#tbl_m5', cols:{0:'合计 {n} 天',1:'sum',2:'sum',3:'sum',4:'money',5:'money',6:['ratio',5,4,'pct'],7:'sum'}},
    {sel:'#tbl_m7', cols:{1:'合计 {n} 家门店',2:'sum',3:['wavg',2,'num1'],4:['wavg',2,'num1'],5:['wavg',2,'money0']}},
    {sel:'#tbl_m8', cols:{0:'合计 {n} 家门店',1:'sum',2:'sum',3:['ratio',2,1,'pct'],4:'sum'}},
    {sel:'#tbl_m12', cols:{1:'合计 {n} 家门店',2:'sum1',7:'sum'}},
    {sel:'#inv-brand table', cols:{1:'合计 {n} 个品牌',2:'sum',3:'sum',4:'sum1',5:['ratio',2,4,'num0'],7:['wavg',2,'money0'],8:'money'}},
    {sel:'#inv-model table', cols:{2:'合计 {n} 个型号',3:'sum',4:'sum',5:'sum1',6:['ratio',3,5,'num0'],8:'money'}},
    {sel:'#inv-turnover table', cols:{1:'合计 {n} 家门店',2:'sum',3:'sum1',4:['ratio',2,3,'num0'],6:'money'}},
    {sel:'#inv-overstock table', cols:{2:'合计 {n} 条',3:'sum',4:'money'}},
    {sel:'#inv-lowstock table', cols:{2:'合计 {n} 条',3:'sum',5:'sum',6:'sum'}},
    {sel:'#inv-general table', cols:{1:'合计 {n} 条',2:'sum',3:'money'}},
    {sel:'#inv-store-model table', cols:{3:'合计 {n} 条',4:'sum',5:'sum',6:'sum',7:['ratio',4,6,'num0'],8:'sum',11:'money'}},
    {sel:'#tbl_kpi_m1', cols:{0:'全年 {n} 个月',1:'sum',2:'sum',3:['ratio',2,1,'pct'],4:'sum',5:'sum',6:'sum',7:'sum',8:'sum',9:['ratio',8,7,'pct']}},
    {sel:'#tbl_kpi_brand', cols:{1:'合计 {n} 个品牌',2:'sum',3:'sum',4:['ratio',1,3,'pct']}},
    {sel:'#tbl_kpi_m2', cols:{0:'合计 {n} 个月',1:'sum',2:'sum',3:'sum',4:['ratio',3,2,'pct']}},
    {sel:'#tbl_kpi_m2d', cols:{1:'合计 {n} 家门店',2:'money',3:'money',4:['ratio',3,2,'pct'],5:['wavg',3,'pct']}},
    {sel:'#tbl_kpi_m3', cols:{0:'合计 {n} 个月',1:'money',2:'money',3:'money'}},
    {sel:'#tbl_kpi_m4', cols:{0:'合计 {n} 个月',1:'sum',2:'sum',3:['ratio',1,2,'pct']}}
  ];
  var TD_ST='font-weight:700;background:var(--surface2);color:var(--text);border-top:2px solid var(--border);position:sticky;bottom:0;z-index:3;white-space:nowrap';
  function build(table,cfg){
    if(!table||!table.tBodies[0]) return;
    var vis=cfg.vis||function(r){ return r.style.display!=='none'; };
    var rows=Array.prototype.slice.call(table.tBodies[0].rows).filter(vis);
    var n=rows.length;
    var need={};
    Object.keys(cfg.cols).forEach(function(k){
      need[k]=1;
      var v=cfg.cols[k];
      if(Object.prototype.toString.call(v)==='[object Array]'){
        if(v[0]==='ratio'){ need[v[1]]=1; need[v[2]]=1; }
        if(v[0]==='wavg'){ need[v[1]]=1; }
      }
    });
    var data={};
    Object.keys(need).forEach(function(k){
      var c=parseInt(k,10);
      data[c]=rows.map(function(r){ return tfNum(r.cells[c]); });
    });
    var ncol=table.tHead?table.tHead.rows[0].cells.length:0;
    var tds='';
    for(var i=0;i<ncol;i++){
      var spec=cfg.cols[i], txt='';
      if(typeof spec==='string'&&spec.indexOf('{n}')>=0){
        txt=spec.replace('{n}',n);
      } else if(spec==='tick'){
        var ok=rows.filter(function(r){ return (r.cells[i]&&(r.cells[i].textContent||'').indexOf('✓')>=0); }).length;
        txt=ok+' 家达标';
      } else if(spec&&typeof spec==='object'){
        if(spec[0]==='ratio'){
          var a=0,b=0;
          data[spec[1]].forEach(function(v,ix){ var d=data[spec[2]][ix]; if(v!=null&&d!=null){ a+=v; b+=d; } });
          txt=fmt(spec[3], b? (spec[3]==='pct'? a/b*100 : a/b) : null);
        } else if(spec[0]==='wavg'){
          var sw=0,sv=0;
          data[i].forEach(function(v,ix){ var w=data[spec[1]][ix];
            if(v!=null&&w!=null&&w>0&&(spec[2]!=='pct'||Math.abs(v)<1000)){ sv+=v*w; sw+=w; } });
          txt=fmt(spec[2], sw? sv/sw : null);
        }
      } else if(spec){
        var s=0,cnt=0;
        data[i].forEach(function(v){ if(v!=null){ s+=v; cnt++; } });
        txt=cnt?fmt(spec,s):'';
      }
      tds+='<td style="'+TD_ST+'">'+txt+'</td>';
    }
    var tf=table.tFoot;
    if(!tf){ tf=document.createElement('tfoot'); table.appendChild(tf); }
    tf.innerHTML='<tr>'+tds+'</tr>';
  }
  function refresh(sel){
    document.querySelectorAll(sel).forEach(function(t){
      for(var i=0;i<CFG.length;i++){ if(CFG[i].sel===sel){ build(t,CFG[i]); break; } }
    });
  }
  function init(){ CFG.forEach(function(c){ refresh(c.sel); }); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
  // 联动: 型号表筛选/翻页/重置
  ['m10-search','m10-brand-filter','m10-tier-filter'].forEach(function(id){
    var el=document.getElementById(id); if(!el) return;
    el.addEventListener('input',function(){ setTimeout(function(){ refresh('#tbl-model'); },0); });
    el.addEventListener('change',function(){ setTimeout(function(){ refresh('#tbl-model'); },0); });
  });
  var _r=window.m10ResetFilters; if(typeof _r==='function') window.m10ResetFilters=function(){ _r.apply(null,arguments); refresh('#tbl-model'); };
  var _g=window.m10GoPage; if(typeof _g==='function') window.m10GoPage=function(){ _g.apply(null,arguments); refresh('#tbl-model'); };
  // 联动: 库存品牌/品类筛选
  ['model-brand-filter','sm-brand-filter','sm-cat-filter'].forEach(function(id){
    var el=document.getElementById(id); if(!el) return;
    el.addEventListener('change',function(){ setTimeout(function(){ refresh('#inv-model table'); refresh('#inv-store-model table'); },0); });
  });
  // 联动: 单店型号表(JS动态渲染)
  var smtb=document.getElementById('store-model-tbody');
  if(smtb&&window.MutationObserver){ new MutationObserver(function(){ refresh('#inv-store-model table'); }).observe(smtb,{childList:true}); }
})();
</script>
"""

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
                <select id="trend-brand-filter" onchange="filterTrendCombo()" style="padding:5px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:11px;max-width:100px">
                    <option value="">全部品牌</option>
                </select>
                <label style="color:var(--text2);font-size:11px;white-space:nowrap;margin-left:4px">价位段：</label>
                <select id="trend-tier-filter" onchange="filterTrendCombo()" style="padding:5px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:11px;max-width:100px">
                    <option value="">全部价位</option>
                </select>
                <div style="position:relative;margin-left:4px">
                    <button id="trend-combo-btn" onclick="toggleTrendCombo()"
                     style="padding:6px 24px 6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--card2);color:var(--text1);font-size:12px;cursor:pointer;text-align:left;min-width:180px;white-space:nowrap">
                        + 添加型号 ▾
                    </button>
                    <div id="trend-combo-dropdown" style="display:none;position:absolute;top:100%;left:0;width:280px;background:var(--surface);border:1px solid var(--border);border-radius:6px;z-index:1000;margin-top:2px;box-shadow:0 8px 24px rgba(15,23,42,0.12)">
                        <div style="padding:6px 8px;border-bottom:1px solid var(--border)">
                            <input type="text" id="trend-combo-search" placeholder="输入型号搜索..."
                             style="width:100%;padding:6px 10px;border-radius:4px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box"
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

# ===== 日销售情况 / 月度完成情况 (Module 20/21) =====
dm_css = """
/* ===== 日销售情况 / 月度完成情况 (柔和浅色系) ===== */
.dm-hero{display:grid;grid-template-columns:1.05fr 1.5fr .85fr;gap:18px;align-items:center;border-radius:12px;padding:16px 20px;margin-bottom:14px;border:1px solid transparent}
.dm-hero-day{background:linear-gradient(135deg,#f8fafc 0%,#eef2f7 55%,#e9eef5 100%);border-color:#dbe2ea;color:#334155}
.dm-hero-mon{background:linear-gradient(135deg,#f8fafc 0%,#eef2f7 55%,#e9eef5 100%);border-color:#dbe2ea;color:#334155}
.dm-hero-label{font-size:12px;opacity:.78;margin-bottom:6px;font-weight:500;line-height:1.5}
.dm-hero-row{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
.dm-big{font-size:30px;font-weight:800;line-height:1.05;letter-spacing:-.5px}
.dm-sub{font-size:11px;opacity:.75;margin-top:2px;white-space:nowrap}
.dm-sub .dm-rmb{font-weight:700;opacity:1}
.dm-divider{width:1px;height:34px;background:rgba(15,23,42,.14);align-self:center}
.dm-chips{display:flex;flex-wrap:wrap;gap:6px}
.dm-chip{border-radius:8px;padding:3px 9px;font-size:11px;display:inline-flex;gap:5px;align-items:center;white-space:nowrap;font-weight:500}
.dm-hero-day .dm-chip{background:rgba(100,116,139,.12);color:#475569}
.dm-hero-mon .dm-chip{background:rgba(100,116,139,.12);color:#475569}
.dm-chip b{font-size:12px;font-weight:700}
.dm-hero-table-wrap{overflow-x:auto;min-width:0}
.dm-hero-table{width:100%;border-collapse:collapse;font-size:11.5px}
.dm-hero-table th{font-weight:500;opacity:.75;padding:4px 6px;text-align:right;white-space:nowrap}
.dm-hero-table td{padding:4.5px 6px;text-align:right;white-space:nowrap}
.dm-hero-day .dm-hero-table th{border-bottom:1px solid rgba(100,116,139,.22)}
.dm-hero-day .dm-hero-table td{border-bottom:1px solid rgba(100,116,139,.1)}
.dm-hero-mon .dm-hero-table th{border-bottom:1px solid rgba(100,116,139,.22)}
.dm-hero-mon .dm-hero-table td{border-bottom:1px solid rgba(100,116,139,.1)}
.dm-hero-table tr:last-child td{border-bottom:none;font-weight:700}
.dm-hero-table th:first-child,.dm-hero-table td:first-child{text-align:left}
.dm-gauges{display:flex;gap:8px;justify-content:center}
.dm-gauge{width:118px;text-align:center}
.dm-gauge canvas{height:94px !important;width:118px !important}
.dm-gauge-cap{font-size:10.5px;opacity:.85;margin-top:-4px;line-height:1.35;font-weight:500}
.dm-toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:2px 0 10px}
.dm-btn{padding:5px 12px;border-radius:7px;border:1px solid var(--border);background:var(--surface2);color:var(--text);font-size:12px;cursor:pointer;font-weight:600}
.dm-btn:hover{border-color:#3b82f6;color:#3b82f6}
.dm-select{padding:5px 10px;border-radius:7px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12.5px;font-weight:700;cursor:pointer}
.dm-note{font-size:11px;color:var(--text2)}
.dm-range{font-size:11px;font-weight:400;color:var(--text2);margin-left:8px}
.dm-two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.dm-two-col .chart-title{margin-bottom:6px}
.dm-tbl-wrap{max-height:330px;overflow:auto;border:1px solid var(--border);border-radius:8px}
.dm-tbl-wrap table{margin:0}
.dm-bname{font-weight:600;text-align:left}
.dm-up{color:#dc2626;font-weight:700;font-size:10.5px;font-style:normal}
.dm-down{color:#16a34a;font-weight:700;font-size:10.5px;font-style:normal}
.dm-flat{color:#94a3b8;font-size:10px;font-style:normal}
@media(max-width:960px){.dm-hero{grid-template-columns:1fr}.dm-two-col{grid-template-columns:1fr}.dm-gauges{justify-content:flex-start}}
"""

dm_zone_html = """
<!-- Z2B 日销售情况 (Module 20) -->
<div class="zone" id="zone-day">
<div class="zone-title"><span class="zone-bar"></span>日销售情况<span class="zone-note">手机口径（智能机+平板+功能机）· 切换日期查看单日明细 · 点击图表柱子跳转</span></div>
<div class="section report-only">
    <div class="section-body">

        <div class="dm-hero dm-hero-day">
            <div class="dm-hero-main">
                <div class="dm-hero-label">当日销量 · <span id="dm_day_date">—</span></div>
                <div class="dm-hero-row">
                    <div><div class="dm-big" id="dm_day_qty">—</div><div class="dm-sub">件</div></div>
                    <div class="dm-divider"></div>
                    <div><div class="dm-big" id="dm_day_rev">—</div><div class="dm-sub">当日销售额 · <span class="dm-rmb" id="dm_day_rev_rmb">—</span></div></div>
                </div>
                <div class="dm-chips">
                    <span class="dm-chip">毛利率 <b id="dm_day_margin">—</b> <span id="dm_day_margin_d"></span></span>
                    <span class="dm-chip">单机毛利 <b id="dm_day_uprofit">—</b> <span id="dm_day_uprofit_d"></span></span>
                </div>
            </div>
            <div class="dm-hero-table-wrap">
                <table class="dm-hero-table">
                    <thead><tr><th></th><th>销量</th><th>销售额</th><th>总毛利</th><th>单机毛利</th><th>客单价</th></tr></thead>
                    <tbody id="dm_day_hero_body"></tbody>
                </table>
            </div>
            <div class="dm-gauges">
                <div class="dm-gauge"><canvas id="dm_gauge_time"></canvas><div class="dm-gauge-cap">时间进度</div></div>
                <div class="dm-gauge"><canvas id="dm_gauge_tsmart"></canvas><div class="dm-gauge-cap">传音智能机占比</div></div>
            </div>
        </div>

        <div class="dm-toolbar">
            <button class="dm-btn" onclick="dmShift(-1)">◀ 前一天</button>
            <select id="dm_day_select" class="dm-select" onchange="dmRenderDay(this.value)"></select>
            <button class="dm-btn" onclick="dmShift(1)">后一天 ▶</button>
            <span class="dm-note" id="dm_day_note"></span>
        </div>

        <div class="chart-box" style="margin:4px 0 16px">
            <div class="chart-title">每日销量波动<span style="font-size:11px;font-weight:400;color:var(--text2);margin-left:10px">点击柱子切换日期 · 虚线=目标日均线 / 7日均线 · 柱顶=当日总销量</span></div>
            <div style="height:260px"><canvas id="dm_chart_day"></canvas></div>
        </div>

        <div class="dm-two-col">
            <div>
                <div class="chart-title">品牌明细（日）<span class="dm-range" id="dm_day_brand_range"></span></div>
                <div class="tbl-wrap dm-tbl-wrap">
                    <table>
                        <thead><tr><th style="text-align:left">名称</th><th>销量</th><th>占比</th><th>客单价</th><th>单机毛利</th><th>毛利率</th></tr></thead>
                        <tbody id="dm_day_brand_body"></tbody>
                    </table>
                </div>
            </div>
            <div>
                <div class="chart-title">品类明细（日）<span class="dm-range" id="dm_day_cat_range"></span></div>
                <div class="tbl-wrap dm-tbl-wrap">
                    <table>
                        <thead><tr><th style="text-align:left">名称</th><th>销量</th><th>占比</th><th>客单价</th><th>单机毛利</th><th>毛利率</th></tr></thead>
                        <tbody id="dm_day_cat_body"></tbody>
                    </table>
                </div>
            </div>
        </div>

    </div>
</div>
</div>

<!-- Z2C 月度完成情况 (Module 21) -->
<div class="zone" id="zone-month">
<div class="zone-title"><span class="zone-bar"></span>月度完成情况<span class="zone-note">手机口径 · 环比对比上月同期 · <span id="dm_mon_range_note"></span></span></div>
<div class="section report-only">
    <div class="section-body">

        <div class="dm-hero dm-hero-mon">
            <div class="dm-hero-main">
                <div class="dm-hero-label">本月累计 · <span id="dm_mon_period">—</span></div>
                <div class="dm-hero-row">
                    <div><div class="dm-big" id="dm_mon_qty">—</div><div class="dm-sub">总销量 / 件</div></div>
                    <div class="dm-divider"></div>
                    <div><div class="dm-big" id="dm_mon_rev">—</div><div class="dm-sub">总销售额 · <span class="dm-rmb" id="dm_mon_rev_rmb">—</span></div></div>
                </div>
                <div class="dm-chips">
                    <span class="dm-chip">毛利率 <b id="dm_mon_margin">—</b></span>
                    <span class="dm-chip">单机毛利 <b id="dm_mon_uprofit">—</b></span>
                    <span class="dm-chip">销量环比 <span id="dm_mon_qty_mom">—</span></span>
                </div>
            </div>
            <div class="dm-hero-table-wrap">
                <table class="dm-hero-table">
                    <thead><tr><th></th><th>销量</th><th>销售额</th><th>总毛利</th><th>单机毛利</th><th>客单价</th></tr></thead>
                    <tbody id="dm_mon_hero_body"></tbody>
                </table>
            </div>
            <div class="dm-gauges">
                <div class="dm-gauge"><canvas id="dm_gauge_trans"></canvas><div class="dm-gauge-cap">传音智能机完成</div></div>
                <div class="dm-gauge"><canvas id="dm_gauge_rev"></canvas><div class="dm-gauge-cap">销售额完成率(月)</div></div>
            </div>
        </div>

        <div class="dm-two-col" style="margin-bottom:16px">
            <div>
                <div class="chart-title">品牌明细（月 · 环比）<span class="dm-range" id="dm_mon_brand_range"></span></div>
                <div class="tbl-wrap dm-tbl-wrap">
                    <table>
                        <thead><tr><th style="text-align:left">名称</th><th>销量</th><th>占比</th><th>客单价</th><th>单机毛利</th><th>毛利率</th></tr></thead>
                        <tbody id="dm_mon_brand_body"></tbody>
                    </table>
                </div>
            </div>
            <div>
                <div class="chart-title">品类明细（月 · 环比）<span class="dm-range" id="dm_mon_cat_range"></span></div>
                <div class="tbl-wrap dm-tbl-wrap">
                    <table>
                        <thead><tr><th style="text-align:left">名称</th><th>销量</th><th>占比</th><th>客单价</th><th>单机毛利</th><th>毛利率</th></tr></thead>
                        <tbody id="dm_mon_cat_body"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="chart-box">
            <div class="chart-title">品牌销量对比：本月 vs 上月同期<span style="font-size:11px;font-weight:400;color:var(--text2);margin-left:10px">Top 8 品牌</span></div>
            <div style="height:280px"><canvas id="dm_chart_mon"></canvas></div>
        </div>

    </div>
</div>
</div>
"""

dm_js = r"""
// ===== 日销售情况 / 月度完成情况 (Module 20/21) =====
var _dm = (function(){
    var days = (D.m20_daily_detail && D.m20_daily_detail.days) || [];
    var brandDaily = (D.m20_daily_detail && D.m20_daily_detail.brand_daily) || [];
    var mon = D.m21_month_detail || null;
    var meta = D.meta || {};
    var NGN_RATE = __NGN_RATE__;
    var _idx = days.length - 1;
    var _dayChart = null, _gTsmart = null, _monChart = null;
    var _barBase = ['#3b82f6', '#f59e0b', '#8b5cf6'];

    function fmtI(v){ return (v === null || v === undefined || isNaN(v)) ? '—' : Math.round(v).toLocaleString('en-US'); }
    function fmtN(v){ if (v === null || v === undefined || isNaN(v)) return '—';
        var a = Math.abs(v);
        if (a >= 1e6) return '₦' + (v / 1e6).toFixed(1) + 'M';
        if (a >= 1e3) return '₦' + (v / 1e3).toFixed(0) + 'K';
        return '₦' + Math.round(v); }
    function fmtRmb(ngn){ if (ngn === null || ngn === undefined || isNaN(ngn)) return '—';
        var c = ngn * NGN_RATE;
        if (Math.abs(c) >= 1e8) return '≈¥' + (c / 1e8).toFixed(2) + '亿';
        if (Math.abs(c) >= 1e4) return '≈¥' + (c / 1e4).toFixed(1) + '万';
        return '≈¥' + Math.round(c); }
    function pct(v, d){ if (v === null || v === undefined || isNaN(v)) return '—'; return v.toFixed(d === undefined ? 1 : d) + '%'; }
    function safeDiv(a, b){ return (b > 0) ? a / b : null; }
    function _wd(ds){ return '周' + '日一二三四五六'.charAt(new Date(ds.replace(/-/g, '/')).getDay()); }
    function _md(ds){ return ds.slice(5).replace('-', '/'); }

    function rowMetrics(o){
        return { qty: o.qty, price: safeDiv(o.revenue, o.qty), up: safeDiv(o.profit, o.qty),
            margin: o.revenue > 0 ? o.profit / o.revenue * 100 : null };
    }

    // 环比小箭头: kind = 'pct' | 'pp'; hero=true 时用白色(渐变底)
    function dSpan(cur, prev, kind, hero){
        if (cur === null || cur === undefined || prev === null || prev === undefined) return '';
        var diff, txt;
        if (kind === 'pp'){ diff = cur - prev; }
        else {
            if (!prev || prev <= 0) return hero ? '' : '<i class="dm-flat">新增</i>';
            diff = (cur - prev) / prev * 100;
            if (!isFinite(diff)) return '';
        }
        if (Math.abs(diff) < 0.05) return '<i class="dm-flat">±0.0</i>';
        txt = (diff > 0 ? '+' : '') + diff.toFixed(1) + (kind === 'pp' ? 'pp' : '%');
        var arrow = diff > 0 ? '▲' : '▼';
        // hero 浅色底与普通表格统一用涨红/跌绿
        if (hero) return '<i style="color:' + (diff > 0 ? '#dc2626' : '#16a34a') + ';font-style:normal;font-weight:700;font-size:10px">' + arrow + txt + '</i>';
        return '<i class="' + (diff > 0 ? 'dm-up' : 'dm-down') + '">' + arrow + txt + '</i>';
    }

    var gaugePlugin = {
        id: 'dmGaugeCenter',
        afterDraw: function(chart){
            if (!chart.$dmCenter) return;
            var area = chart.chartArea; if (!area) return;
            var ctx = chart.ctx;
            var cx = (area.left + area.right) / 2, cy = (area.top + area.bottom) / 2;
            ctx.save();
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.font = '700 16px -apple-system,BlinkMacSystemFont,sans-serif';
            ctx.fillStyle = chart.$dmCenter.color || '#0f172a';
            ctx.fillText(chart.$dmCenter.text, cx, cy - 4);
            if (chart.$dmCenter.sub){
                ctx.font = '500 8.5px -apple-system,BlinkMacSystemFont,sans-serif';
                ctx.fillStyle = chart.$dmCenter.subColor || '#64748b';
                ctx.fillText(chart.$dmCenter.sub, cx, cy + 11);
            }
            ctx.restore();
        }
    };

    function makeGauge(id, val, color, text, sub){
        var el = document.getElementById(id); if (!el) return null;
        var v = Math.max(0, Math.min(100, val || 0));
        var c = new Chart(el, {
            type: 'doughnut',
            data: { datasets: [{ data: [v, 100 - v], backgroundColor: [color, 'rgba(148,163,184,0.22)'],
                borderWidth: 0, cutout: '70%' }] },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false }, datalabels: { display: false } } },
            plugins: [gaugePlugin]
        });
        c.$dmCenter = { text: text, sub: sub || '' };
        return c;
    }

    function heroRows(o){
        var defs = [['smart', '智能手机'], ['feature', '功能机'], ['tablet', '平板'], ['total', '合计']];
        return defs.map(function(d){
            var k = d[0], m = rowMetrics(o[k]);
            return '<tr' + (k === 'total' ? ' style="font-weight:700"' : '') + '><td>' + d[1] + '</td>'
                + '<td>' + fmtI(o[k].qty) + '</td>'
                + '<td>' + fmtN(o[k].revenue) + '</td>'
                + '<td>' + fmtN(o[k].profit) + '</td>'
                + '<td>' + (m.up === null ? '—' : '₦' + fmtI(m.up)) + '</td>'
                + '<td>' + (m.price === null ? '—' : '₦' + fmtI(m.price)) + '</td></tr>';
        }).join('');
    }

    function brandRow(r, pv, totQty, prevTotQty){
        var m = rowMetrics(r);
        var mp = pv ? rowMetrics(pv) : null;
        var share = totQty > 0 ? r.qty / totQty * 100 : null;
        var pShare = (pv && prevTotQty > 0) ? pv.qty / prevTotQty * 100 : null;
        return '<tr><td class="dm-bname">' + r.brand + '</td>'
            + '<td>' + fmtI(r.qty) + ' ' + (mp ? dSpan(r.qty, pv.qty, 'pct') : '') + '</td>'
            + '<td>' + (share === null ? '—' : pct(share)) + ' ' + (mp && pShare !== null ? dSpan(share, pShare, 'pp') : '') + '</td>'
            + '<td>' + (m.price === null ? '—' : '₦' + fmtI(m.price)) + ' ' + (mp ? dSpan(m.price, mp.price, 'pct') : '') + '</td>'
            + '<td>' + (m.up === null ? '—' : '₦' + fmtI(m.up)) + ' ' + (mp ? dSpan(m.up, mp.up, 'pct') : '') + '</td>'
            + '<td>' + (m.margin === null ? '—' : pct(m.margin)) + ' ' + (mp ? dSpan(m.margin, mp.margin, 'pp') : '') + '</td></tr>';
    }

    function catRow(name, o, ov, totQty, prevTotQty){
        var m = rowMetrics(o);
        var mp = ov ? rowMetrics(ov) : null;
        var share = totQty > 0 ? o.qty / totQty * 100 : null;
        var pShare = (ov && prevTotQty > 0) ? ov.qty / prevTotQty * 100 : null;
        return '<tr><td class="dm-bname">' + name + '</td>'
            + '<td>' + fmtI(o.qty) + ' ' + (mp ? dSpan(o.qty, ov.qty, 'pct') : '') + '</td>'
            + '<td>' + (share === null ? '—' : pct(share)) + ' ' + (mp && pShare !== null ? dSpan(share, pShare, 'pp') : '') + '</td>'
            + '<td>' + (m.price === null ? '—' : '₦' + fmtI(m.price)) + ' ' + (mp ? dSpan(m.price, mp.price, 'pct') : '') + '</td>'
            + '<td>' + (m.up === null ? '—' : '₦' + fmtI(m.up)) + ' ' + (mp ? dSpan(m.up, mp.up, 'pct') : '') + '</td>'
            + '<td>' + (m.margin === null ? '—' : pct(m.margin)) + ' ' + (mp ? dSpan(m.margin, mp.margin, 'pp') : '') + '</td></tr>';
    }

    function highlightDay(i){
        if (!_dayChart) return;
        [0, 1, 2].forEach(function(di){
            _dayChart.data.datasets[di].backgroundColor = days.map(function(_, j){
                return j === i ? _barBase[di] : _barBase[di] + '59';
            });
        });
        _dayChart.update('none');
    }

    function renderDay(dateStr){
        if (!days.length) return;
        var i = dateStr ? days.findIndex(function(d){ return d.date === dateStr; }) : _idx;
        if (i < 0) i = days.length - 1;
        _idx = i;
        var cur = days[i], prev = i > 0 ? days[i - 1] : null;
        var sel = document.getElementById('dm_day_select');
        if (sel && sel.value !== cur.date) sel.value = cur.date;
        document.getElementById('dm_day_date').textContent = _md(cur.date) + ' ' + _wd(cur.date);

        var mCur = rowMetrics(cur.total);
        document.getElementById('dm_day_qty').textContent = fmtI(cur.total.qty);
        document.getElementById('dm_day_rev').textContent = fmtN(cur.total.revenue);
        document.getElementById('dm_day_rev_rmb').textContent = fmtRmb(cur.total.revenue);
        document.getElementById('dm_day_margin').textContent = pct(mCur.margin, 2);
        document.getElementById('dm_day_uprofit').textContent = mCur.up === null ? '—' : '₦' + fmtI(mCur.up);
        if (prev){
            var mPrev = rowMetrics(prev.total);
            document.getElementById('dm_day_margin_d').innerHTML = dSpan(mCur.margin, mPrev.margin, 'pp', true);
            document.getElementById('dm_day_uprofit_d').innerHTML = dSpan(mCur.up, mPrev.up, 'pct', true);
        } else {
            document.getElementById('dm_day_margin_d').innerHTML = '';
            document.getElementById('dm_day_uprofit_d').innerHTML = '';
        }
        document.getElementById('dm_day_hero_body').innerHTML = heroRows(cur);
        document.getElementById('dm_day_note').textContent = prev ? ('对比前一营业日 ' + _md(prev.date)) : '本期首个营业日';
        document.getElementById('dm_day_brand_range').textContent = prev
            ? (_md(prev.date) + ' → ' + _md(cur.date) + ' · 共 ' + days.length + ' 个营业日')
            : ('共 ' + days.length + ' 个营业日');
        document.getElementById('dm_day_cat_range').textContent = _md(cur.date) + ' 当日';

        // 品牌明细（当日全部有销量的品牌）
        var bdCur = brandDaily.filter(function(r){ return r.date === cur.date; }).sort(function(a, b){ return b.qty - a.qty; });
        var prevMap = {};
        if (prev) brandDaily.forEach(function(r){ if (r.date === prev.date) prevMap[r.brand] = r; });
        var totQty = cur.total.qty, pTotQty = prev ? prev.total.qty : 0;
        document.getElementById('dm_day_brand_body').innerHTML = bdCur.map(function(r){
            return brandRow(r, prevMap[r.brand] || null, totQty, pTotQty);
        }).join('') || '<tr><td colspan="6" style="text-align:center;color:#94a3b8">无数据</td></tr>';

        // 品类明细
        var catDefs = [['smart', '智能机'], ['feature', '功能机'], ['tablet', '平板电脑']];
        document.getElementById('dm_day_cat_body').innerHTML = catDefs.map(function(d){
            return catRow(d[1], cur[d[0]], prev ? prev[d[0]] : null, totQty, pTotQty);
        }).join('');

        // 传音占比仪表盘
        if (_gTsmart){
            _gTsmart.data.datasets[0].data = [Math.max(0, Math.min(100, cur.tsmart_share || 0)), 100 - Math.max(0, Math.min(100, cur.tsmart_share || 0))];
            _gTsmart.$dmCenter = { text: pct(cur.tsmart_share, 1), sub: '传音智能机/总智能机' };
            _gTsmart.update();
        }
        highlightDay(i);
    }

    function initDayChart(){
        if (!days.length) return;
        var labels = days.map(function(d){ return _md(d.date); });
        var totals = days.map(function(d){ return d.total.qty; });
        var smarts = days.map(function(d){ return d.smart.qty; });
        var feats = days.map(function(d){ return d.feature.qty; });
        var tabs = days.map(function(d){ return d.tablet.qty; });
        var dma = days.map(function(d, i){
            var s = days.slice(Math.max(0, i - 6), i + 1);
            return s.reduce(function(a, x){ return a + x.total.qty; }, 0) / s.length;
        });
        var need = meta.daily_needed || 0;
        _dayChart = new Chart(document.getElementById('dm_chart_day'), {
            type: 'bar',
            data: { labels: labels, datasets: [
                { label: '智能机', data: smarts, backgroundColor: '#3b82f659', stack: 's',
                  borderRadius: 3, barPercentage: .7, categoryPercentage: .8, datalabels: { display: false } },
                { label: '功能机', data: feats, backgroundColor: '#f59e0b59', stack: 's',
                  borderRadius: 3, barPercentage: .7, categoryPercentage: .8, datalabels: { display: false } },
                { label: '平板', data: tabs, backgroundColor: '#94a3b859', stack: 's',
                  borderRadius: 3, barPercentage: .7, categoryPercentage: .8, datalabels: { display: false } },
                { label: '7日均线', type: 'line', data: dma, stack: 'l1', borderColor: '#64748b',
                  borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, tension: .35, datalabels: { display: false } },
                { label: '目标日均 ' + fmtI(need), type: 'line', data: days.map(function(){ return need; }), stack: 'l2',
                  borderColor: '#475569', borderDash: [2, 3], borderWidth: 1.2, pointRadius: 0, datalabels: { display: false } },
                { label: '总量', type: 'line', data: totals, stack: 'lbl', borderColor: 'transparent', pointRadius: 0,
                  datalabels: { display: true, clip: false, anchor: 'end', align: 'top', offset: 1, color: '#475569',
                    font: { size: 9, weight: '600' }, formatter: function(v){ return fmtI(v); } } }
            ]},
            options: {
                responsive: true, maintainAspectRatio: false,
                layout: { padding: { top: 16 } },
                onClick: function(evt, els){ if (els.length) renderDay(days[els[0].index].date); },
                onHover: function(evt, els){ evt.native.target.style.cursor = els.length ? 'pointer' : 'default'; },
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 10 },
                        filter: function(item){ return item.text !== '总量'; } } },
                    tooltip: {
                        callbacks: {
                            title: function(items){ var d = days[items[0].dataIndex]; return d ? (d.date + ' ' + _wd(d.date)) : ''; },
                            label: function(c){
                                if (c.dataset.label === '总量' || c.dataset.label.indexOf('7日') === 0 || c.dataset.label.indexOf('目标') === 0)
                                    return c.dataset.label + ': ' + fmtI(c.parsed.y) + '件';
                                return c.dataset.label + ': ' + fmtI(c.parsed.y) + '件';
                            },
                            afterBody: function(items){
                                var d = days[items[0].dataIndex]; if (!d) return '';
                                var mg = d.total.revenue > 0 ? (d.total.profit / d.total.revenue * 100).toFixed(1) + '%' : '—';
                                return ['当日合计: ' + fmtI(d.total.qty) + '件', '毛利率: ' + mg,
                                    '销售额: ' + fmtN(d.total.revenue) + ' (' + fmtRmb(d.total.revenue) + ')'];
                            }
                        }
                    },
                    datalabels: { display: false }
                },
                scales: {
                    x: { stacked: true, grid: { display: false }, ticks: { font: { size: 9.5 } } },
                    y: { stacked: true, beginAtZero: true, suggestedMax: Math.max.apply(null, totals) * 1.12,
                        grid: { color: 'rgba(51,65,85,0.12)' }, ticks: { font: { size: 10 } } }
                }
            }
        });
    }

    function renderMonth(){
        var zone = document.getElementById('zone-month');
        if (!mon){ if (zone) zone.style.display = 'none'; return; }
        var cur = mon.cur, prev = mon.prev;
        var mC = rowMetrics(cur.total);
        var pl = (mon.prev_label || '').replace(/^\d{4}\//, '');
        document.getElementById('dm_mon_period').textContent = '09/01 → ' + _md(meta.report_date || '');
        document.getElementById('dm_mon_range_note').textContent = pl;
        document.getElementById('dm_mon_qty').textContent = fmtI(cur.total.qty);
        document.getElementById('dm_mon_rev').textContent = fmtN(cur.total.revenue);
        document.getElementById('dm_mon_rev_rmb').textContent = fmtRmb(cur.total.revenue);
        document.getElementById('dm_mon_margin').textContent = pct(mC.margin, 2);
        document.getElementById('dm_mon_uprofit').textContent = '₦' + fmtI(mC.up);
        document.getElementById('dm_mon_qty_mom').innerHTML = dSpan(cur.total.qty, prev.total.qty, 'pct', true);
        document.getElementById('dm_mon_hero_body').innerHTML = heroRows({
            smart: cur.cats.smart, feature: cur.cats.feature, tablet: cur.cats.tablet, total: cur.total
        });
        document.getElementById('dm_mon_brand_range').textContent = '较上月同期 ' + pl;
        document.getElementById('dm_mon_cat_range').textContent = '较上月同期 ' + pl;

        // 品牌环比表
        var pmap = {};
        prev.brands.forEach(function(b){ pmap[b.brand] = b; });
        var totQty = cur.total.qty, pTotQty = prev.total.qty;
        document.getElementById('dm_mon_brand_body').innerHTML = cur.brands.map(function(r){
            return brandRow(r, pmap[r.brand] || null, totQty, pTotQty);
        }).join('');

        // 品类环比表
        var catDefs = [['smart', '智能机'], ['feature', '功能机'], ['tablet', '平板电脑']];
        document.getElementById('dm_mon_cat_body').innerHTML = catDefs.map(function(d){
            return catRow(d[1], cur.cats[d[0]], prev.cats[d[0]], totQty, pTotQty);
        }).join('');

        // 仪表盘: 传音智能机完成率 + 销售额完成率(月)
        var mm = meta.current_month;
        var mk = '2026-' + (mm < 10 ? '0' + mm : '' + mm);
        var K = (typeof KPI !== 'undefined') ? KPI : null;
        var tRate = null, tSub = '', rRate = null, rSub = '';
        try {
            if (K && K.m1){
                var tTgt = K.m1.target[mm - 1], tAct = K.m1.actual[mm - 1];
                if (tTgt > 0 && tAct !== undefined && tAct !== null){ tRate = tAct / tTgt * 100; tSub = '目标 ' + fmtI(tTgt) + ' 台'; }
                var rTgt = K.m1.revTarget ? K.m1.revTarget[mm - 1] : null;
                var rAct = K.m1.revActual ? K.m1.revActual[mm - 1] : null;
                if (rTgt > 0 && rAct !== undefined && rAct !== null){ rRate = rAct / rTgt * 100; rSub = '目标 ¥' + fmtI(rTgt / 1e4) + '万'; }
            }
        } catch(e){}
        if (tRate === null){ tRate = meta.total_target > 0 ? meta.total_smart_qty / meta.total_target * 100 : 0; tSub = '目标 ' + fmtI(meta.total_target) + ' 台'; }
        if (rRate === null){ rRate = meta.time_progress_pct || 0; rSub = '时间进度'; }
        makeGauge('dm_gauge_trans', tRate, '#64748b', pct(tRate, 1), tSub);
        makeGauge('dm_gauge_rev', rRate, '#f59e0b', pct(rRate, 1), rSub);
    }

    function initMonChart(){
        if (!mon) return;
        var bs = mon.cur.brands.slice(0, 8);
        var pmap = {};
        mon.prev.brands.forEach(function(b){ pmap[b.brand] = b.qty; });
        var curVals = bs.map(function(b){ return b.qty; });
        var prevVals = bs.map(function(b){ return pmap[b.brand] || 0; });
        var allMax = Math.max.apply(null, curVals.concat(prevVals));
        _monChart = new Chart(document.getElementById('dm_chart_mon'), {
            type: 'bar',
            data: { labels: bs.map(function(b){ return b.brand; }), datasets: [
                { label: '本月', data: curVals, backgroundColor: '#64748b',
                  borderRadius: 4, barPercentage: .62, categoryPercentage: .72,
                  datalabels: { clip: false, anchor: 'end', align: 'top', color: '#475569', font: { size: 9, weight: '600' },
                    formatter: function(v){ return fmtI(v); } } },
                { label: '上月同期(' + mon.prev_label.split('·')[1].trim() + ')', data: prevVals,
                  backgroundColor: '#94a3b8', borderRadius: 4, barPercentage: .62, categoryPercentage: .72,
                  datalabels: { clip: false, anchor: 'end', align: 'top', color: '#64748b', font: { size: 9 },
                    formatter: function(v){ return v > 0 ? fmtI(v) : ''; } } }
            ]},
            options: { responsive: true, maintainAspectRatio: false,
                layout: { padding: { top: 16 } },
                plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 10 } } } },
                scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } },
                    y: { beginAtZero: true, suggestedMax: allMax * 1.12, grid: { color: 'rgba(51,65,85,0.12)' }, ticks: { font: { size: 10 } } } } }
        });
    }

    function dmShift(delta){
        var i = Math.min(days.length - 1, Math.max(0, _idx + delta));
        renderDay(days[i].date);
    }

    function init(){
        if (!document.getElementById('dm_day_select')) return;
        var zoneDay = document.getElementById('zone-day');
        if (!days.length){ if (zoneDay) zoneDay.style.display = 'none'; var zm = document.getElementById('zone-month'); if (zm) zm.style.display = 'none'; return; }
        var sel = document.getElementById('dm_day_select');
        sel.innerHTML = days.map(function(d){
            return '<option value="' + d.date + '">' + _md(d.date) + ' ' + _wd(d.date) + '</option>';
        }).join('');
        makeGauge('dm_gauge_time', meta.time_progress_pct || 0, '#f59e0b', pct(meta.time_progress_pct, 1), '已过 ' + (meta.elapsed_days || 0) + '/' + (meta.total_biz_days || 0) + ' 天');
        _gTsmart = makeGauge('dm_gauge_tsmart', 0, '#475569', '—', '');
        initDayChart();
        renderDay();
        renderMonth();
        initMonChart();
    }

    // 对外暴露(供 HTML onclick 使用)
    window.dmShift = dmShift;
    window.dmRenderDay = renderDay;

    if (document.readyState === 'loading'){
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
"""

# 汇率注入 (dm_js 为普通字符串, 用占位符带入 Python 常量 NGN_CNY_RATE)
dm_js = dm_js.replace('__NGN_RATE__', repr(NGN_CNY_RATE))


def overview_dm_section():
    """总览速览: 日/月销售核心摘要 (Module 20/21 精华, 静态渲染, 交互明细在汇报精简版)"""
    d20 = D.get('m20_daily_detail') or {}
    days = d20.get('days') or []
    mon = D.get('m21_month_detail') or {}
    if not days or not mon.get('cur'):
        return ''
    cur, prev = days[-1], (days[-2] if len(days) > 1 else None)
    mcur, mprev = mon['cur'], mon.get('prev') or {}

    def _wd(ds):
        return '周' + '一二三四五六日'[datetime.datetime.strptime(ds, '%Y-%m-%d').weekday()]

    def _md(ds):
        return ds[5:].replace('-', '/')

    def _naira(v):
        return fmt_naira(v) if v else '—'

    def _kv_rows(items, color):
        # items: [(label, value_html), ...] → 2 列网格
        cells = ''.join(
            f'<div style="background:rgba(255,255,255,.66);border-radius:8px;padding:7px 10px">'
            f'<div style="font-size:10.5px;opacity:.72;margin-bottom:2px">{lb}</div>'
            f'<div style="font-size:13px;font-weight:700;line-height:1.25">{vh}</div></div>'
            for lb, vh in items)
        return (f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:10px;color:{color}">{cells}</div>')

    # --- 日卡 ---
    dt, dp = cur['total'], (prev['total'] if prev else None)
    m_day = dt['revenue'] / dt['profit'] and (dt['profit'] / dt['revenue'] * 100 if dt['revenue'] else 0)
    up_day = dt['profit'] / dt['qty'] if dt['qty'] else 0
    m_prev = (dp['profit'] / dp['revenue'] * 100 if (dp and dp['revenue']) else None)
    up_prev = (dp['profit'] / dp['qty'] if (dp and dp['qty']) else None)
    m_pp = (f'<i style="color:{"#dc2626" if m_day >= m_prev else "#16a34a"};font-style:normal;font-size:10.5px">'
            f'{"▲" if m_day >= m_prev else "▼"}{abs(m_day - m_prev):.2f}pp</i>' if m_prev is not None else '')
    up_pct = (f'<i style="color:{"#dc2626" if up_day >= up_prev else "#16a34a"};font-style:normal;font-size:10.5px">'
              f'{"▲" if up_day >= up_prev else "▼"}{abs(up_day / up_prev - 1) * 100:.1f}%</i>'
              if up_prev else '<i style="color:#94a3b8;font-size:10.5px;font-style:normal">新增</i>')
    day_items = [
        ('销售额', f'{_naira(dt["revenue"])} <span style="font-weight:600;color:#475569">{fmt_rmb(dt["revenue"])}</span>'),
        ('总毛利', f'{_naira(dt["profit"])} <span style="font-weight:600;color:#475569">{fmt_rmb(dt["profit"])}</span>'),
        ('毛利率', f'{m_day:.2f}% {m_pp}'),
        ('单机毛利', f'₦{up_day:,.0f} {up_pct}'),
    ]
    day_card = f'''
        <div style="background:linear-gradient(135deg,#f8fafc,#eef2f7);border:1px solid #dbe2ea;border-radius:10px;padding:14px 16px;color:#334155">
            <div style="font-size:12px;opacity:.8;margin-bottom:6px">最近营业日 · {_md(cur["date"])} {_wd(cur["date"])}</div>
            <div style="display:flex;gap:14px;align-items:baseline;flex-wrap:wrap">
                <span style="font-size:26px;font-weight:800;letter-spacing:-.5px">{dt["qty"]:,}</span>
                <span style="font-size:11px;opacity:.75">件</span>
                <span style="font-size:19px;font-weight:800">{_naira(dt["revenue"])}</span>
                <span style="font-size:11.5px;font-weight:700;color:#475569">{fmt_rmb(dt["revenue"])}</span>
            </div>
            {_kv_rows(day_items, '#475569')}
        </div>'''

    # --- 月卡 ---
    mt, mp = mcur['total'], mprev.get('total') or {}
    m_mon = mt['profit'] / mt['revenue'] * 100 if mt['revenue'] else 0
    up_mon = mt['profit'] / mt['qty'] if mt['qty'] else 0
    mom = (mt['qty'] - mp['qty']) / mp['qty'] * 100 if mp.get('qty') else None
    mom_html = (f'<i style="color:{"#dc2626" if mom >= 0 else "#16a34a"};font-style:normal;font-size:10.5px">'
                f'{"▲" if mom >= 0 else "▼"}{abs(mom):.1f}%</i>' if mom is not None else '')
    pl = (mon.get('prev_label') or '').split('·')[-1].strip()
    mon_items = [
        ('销售额', f'{_naira(mt["revenue"])} <span style="font-weight:600;color:#475569">{fmt_rmb(mt["revenue"])}</span>'),
        ('总毛利', f'{_naira(mt["profit"])} <span style="font-weight:600;color:#475569">{fmt_rmb(mt["profit"])}</span>'),
        ('毛利率', f'{m_mon:.2f}%'),
        ('单机毛利', f'₦{up_mon:,.0f} <span style="font-size:10.5px;opacity:.75">销量环比 {mom_html}</span>'),
    ]
    mon_card = f'''
        <div style="background:linear-gradient(135deg,#f8fafc,#eef2f7);border:1px solid #dbe2ea;border-radius:10px;padding:14px 16px;color:#334155">
            <div style="font-size:12px;opacity:.8;margin-bottom:6px">本月累计 · 09/01 → {_md(M["report_date"])}<span style="opacity:.75"> · 环比 {pl}</span></div>
            <div style="display:flex;gap:14px;align-items:baseline;flex-wrap:wrap">
                <span style="font-size:26px;font-weight:800;letter-spacing:-.5px">{mt["qty"]:,}</span>
                <span style="font-size:11px;opacity:.75">件</span>
                <span style="font-size:19px;font-weight:800">{_naira(mt["revenue"])}</span>
                <span style="font-size:11.5px;font-weight:700;color:#475569">{fmt_rmb(mt["revenue"])}</span>
            </div>
            {_kv_rows(mon_items, '#475569')}
        </div>'''

    # --- 完成率进度条 (KPI 月度: 传音智能机 + 销售额) ---
    bars = ''
    try:
        mm = int(M.get('current_month') or int(M['report_date'][5:7]))
        mk = f'2026-{mm:02d}'
        m1 = (K or {}).get('module1_annual') or {}
        _t, _a = m1.get('target') or {}, m1.get('actual') or {}
        tq = (_t.get('qty_monthly') or [])[mm - 1] if len(_t.get('qty_monthly') or []) >= mm else None
        aq = (_a.get('qty_monthly') or {}).get(mk)
        rq = (_t.get('rev_rmb_monthly') or [])[mm - 1] if len(_t.get('rev_rmb_monthly') or []) >= mm else None
        ra = (_a.get('rev_rmb_monthly') or {}).get(mk)

        def _bar(title, rate, num_txt, c1, c2, txt_color):
            w = max(0, min(100, rate or 0))
            return f'''
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:12px">
                        <span style="font-weight:600;color:var(--text)">{title}</span>
                        <span style="font-weight:800;font-size:14px;color:{txt_color}">{rate:.1f}%</span>
                    </div>
                    <div style="margin-top:5px;height:10px;background:#e2e8f0;border-radius:6px;overflow:hidden">
                        <div style="width:{w:.1f}%;height:100%;background:linear-gradient(90deg,{c1},{c2});border-radius:6px"></div>
                    </div>
                    <div style="font-size:11px;color:var(--text2);margin-top:4px">{num_txt}</div>
                </div>'''

        if tq and aq is not None:
            bars += _bar('传音智能机完成率', aq / tq * 100, f'{aq:,.0f} / {tq:,.0f} 台 · 月度目标', '#94a3b8', '#64748b', '#475569')
        if rq and ra is not None:
            bars += _bar('销售额完成率(月)', ra / rq * 100, f'¥{ra/1e4:,.0f}万 / ¥{rq/1e4:,.0f}万 · 月度目标', '#fbbf24', '#f59e0b', '#b45309')
    except Exception:
        pass

    bars_html = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px">{bars}</div>' if bars else ''

    return f'''<div class="section analysis-only" data-mod="overview">
    <div class="section-header">
        <div class="section-title"><span class="num">📊</span> 日/月销售核心摘要</div>
        <div style="font-size:11px;color:var(--text2)">手机口径 · 完整交互明细见「汇报精简版」日销售情况 / 月度完成情况</div>
    </div>
    <div class="section-body">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">{day_card}{mon_card}</div>
        {bars_html}
    </div>
</div>'''


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
.top-nav {{ display:flex; gap:6px; align-items:center; }}
.nav-btn {{ padding:7px 16px; border-radius:8px; cursor:pointer; font-size:13px; font-weight:600; border:1px solid var(--border); color:var(--text2); background:transparent; transition:all .2s; white-space:nowrap; }}
.nav-btn:hover {{ border-color:var(--blue); color:var(--text); }}
.nav-btn.active {{ background:var(--blue); color:#fff; border-color:var(--blue); }}
.nav-badge {{ font-size:10px; background:var(--red); color:#fff; padding:1px 6px; border-radius:8px; margin-left:2px; }}
.pf-btn.active {{ background:var(--surface2); color:var(--text); border-color:var(--text2); }}
.container {{ max-width:1400px; margin:0 auto; padding:16px; }}

/* KPI Cards */
.kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:16px; }}
.kpi-card {{ background:var(--surface); border-radius:10px; padding:14px 16px; border:1px solid var(--border); }}
.kpi-label {{ color:var(--text2); font-size:11px; text-transform:uppercase; letter-spacing:.5px; }}
.kpi-value {{ font-size:22px; font-weight:800; margin:4px 0; }}
.kpi-sub {{ font-size:11px; color:var(--text2); }}

/* Zones (分区容器) */
.zone {{ margin-bottom:24px; }}
.zone.zone-kpi {{ margin-bottom:20px; }}
.zone-title {{ display:flex; align-items:center; gap:8px; font-size:16px; font-weight:700; color:var(--text); margin-bottom:14px; }}
.zone-bar {{ display:inline-block; width:4px; height:18px; border-radius:2px; background:var(--blue); flex:0 0 auto; }}
.zone-note {{ font-size:11px; font-weight:400; color:var(--text2); margin-left:4px; }}

/* Sections */
.section {{ background:var(--surface); border-radius:10px; margin-bottom:16px; border:1px solid var(--border); overflow:hidden; }}
.section-header {{ padding:12px 16px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }}
.section-title {{ font-size:14px; font-weight:700; display:flex; align-items:center; gap:8px; }}
.section-title .num {{ background:var(--blue); color:#fff; width:22px; height:22px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:11px; }}
.section-body {{ padding:12px 16px; }}
.hist-analysis {{ background:var(--surface2); border-radius:8px; padding:10px 14px; font-size:12px; color:var(--text); }}
.hist-analysis .ai {{ padding:2px 0; }}
.history-insight-box {{ background:var(--surface2); border-radius:8px; padding:12px 16px; margin-bottom:16px; font-size:12px; }}
.history-insight-box h4 {{ font-size:13px; margin-bottom:6px; }}
.history-insight-box .insight-item {{ padding:2px 0; }}

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
/* 年度任务页签: 表格数据居中(表头/数据/合计行) */
#page-kpi th, #page-kpi td {{ text-align:center !important; }}
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
.sub-tabs {{ display:flex; gap:2px; margin-bottom:12px; padding:3px; border:1px solid var(--border); border-radius:8px; }}
.sub-tab {{ padding:4px 12px; border-radius:6px; cursor:pointer; font-size:11px; color:var(--text2); background:var(--surface2); border:none; }}
.sub-tab.active {{ background:var(--blue); color:#fff; }}

/* Mode visibility */
.report-only {{ }}
.analysis-only {{ }}
#mode-analysis {{ min-height: 0; }}
#mode-analysis .chart-box canvas {{ width: 100% !important; }}

/* ===== 模块导航栏 (深度分析版分组切换) ===== */
.mod-nav {{ position:sticky; top:0; z-index:60; display:flex; gap:6px; overflow-x:auto;
    padding:10px 2px; margin-bottom:12px; background:var(--bg);
    border-bottom:1px solid var(--border); scrollbar-width:thin; }}
.mod-nav::-webkit-scrollbar {{ height:4px; }}
.mod-nav::-webkit-scrollbar-thumb {{ background:var(--border); border-radius:2px; }}
.mod-nav-btn {{ flex:0 0 auto; padding:7px 14px; border-radius:8px; border:1px solid var(--border);
    background:var(--surface); color:var(--text2); font-size:12.5px; font-weight:600;
    cursor:pointer; white-space:nowrap; transition:all .15s; }}
.mod-nav-btn:hover {{ border-color:var(--blue); color:var(--text); }}
.mod-nav-btn.active {{ background:var(--blue); color:#fff; border-color:var(--blue); }}
.mod-nav-btn.all {{ margin-left:auto; }}
@media(max-width:768px) {{
    .mod-nav {{ gap:5px; padding:8px 2px; }}
    .mod-nav-btn {{ padding:8px 12px; font-size:12px; min-height:40px; display:inline-flex; align-items:center; }}
    .mod-nav-btn.all {{ margin-left:0; }}
}}

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
    .top-nav {{ flex-wrap:nowrap; overflow-x:auto; gap:4px; width:100%; -webkit-overflow-scrolling:touch; }}
    .nav-btn {{ padding:8px 12px; font-size:12px; min-height:40px; display:inline-flex; align-items:center; white-space:nowrap; flex:0 0 auto; }}
    .nav-btn .nav-badge {{ font-size:9px; padding:1px 4px; }}

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
    .top-nav {{ width:100%; overflow-x:auto; }}
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

{dm_css}
</style>
</head>
<body>
<div class="header">
    <div>
        <h1>📊 销售部数据看板</h1>
        <div class="date">数据周期: {M['period']} <span class="time-progress">时间进度 {M['time_progress_pct']:.1f}%</span> | 已过{M['elapsed_days']:.0f}天 / 剩余{M['remaining_days']:.0f}天 | 生成时间: {M['report_date']}</div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
        <div class="top-nav" id="top-nav">
            <button class="nav-btn active" data-view="report" onclick="switchView('report')">📋 汇报精简版</button>
            <button class="nav-btn" data-view="analysis" onclick="switchView('analysis')">🔍 深度分析版</button>
            <button class="nav-btn" data-view="issues" onclick="switchView('issues')">📋 问题汇总 <span class="nav-badge">{len(D['m9_issues'])}</span></button>
            {f'''<button class="nav-btn" data-view="prices" onclick="switchView('prices')">💰 价格分析 <span class="nav-badge">{len(D.get("price_analysis", []))}</span></button>''' if D.get('price_analysis') else ''}
            {'''<button class="nav-btn" data-view="history" onclick="switchView('history')">📈 历史趋势</button>''' if H else ''}
            {'''<button class="nav-btn" data-view="kpi" onclick="switchView('kpi')">🎯 年度任务</button>''' if K else ''}
        </div>
    </div>
</div>

<div class="container">

<!-- ===== PAGE: 数据看板 ===== -->
<div id="page-dashboard">

<!-- Z1 核心指标 -->
<div class="zone zone-kpi">
<div class="zone-title"><span class="zone-bar"></span>核心指标</div>

<!-- KPI Row -->
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">智能机累计销量</div>
        <div class="kpi-value">{fmt_n(M['total_smart_qty'])}</div>
        <div class="kpi-sub">月度目标 {fmt_n(M['total_target'])} | 完成率 <b style="color:{CF.get('progress_light', {}).get('color', '#f59e0b')}">{M['completion_rate']:.1f}%</b>
            <div style="margin-top:3px">进度差 <b style="color:{CF.get('progress_light', {}).get('color', '#f59e0b')}">{CF.get('progress_diff', 0):+.1f}pp</b>
            <span style="font-size:10px;padding:1px 7px;border-radius:9px;background:{CF.get('progress_light', {}).get('color', '#f59e0b')}1a;color:{CF.get('progress_light', {}).get('color', '#f59e0b')}">{CF.get('progress_light', {}).get('level', '-')}灯</span>
            <span style="color:#94a3b8"> vs 时间进度 {M['time_progress_pct']:.1f}%</span></div>
        </div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">手机总销量</div>
        <div class="kpi-value">{fmt_n(M['total_all_qty'])}</div>
        <div class="kpi-sub">智能机{fmt_n(M['total_smart_qty'])} + 功能机{fmt_n(M['total_feature_qty'])}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">累计营收 <span style="font-weight:400;color:#94a3b8">(全品类)</span></div>
        <div class="kpi-value" style="color:#22c55e">{fmt_naira(M['total_revenue'])} <span style="font-size:0.42em;font-weight:500;color:#94a3b8">{fmt_rmb(M['total_revenue'])}</span></div>
        <div class="kpi-sub">毛利 {fmt_naira(M['total_profit'])} <span style="color:#94a3b8">{fmt_rmb(M['total_profit'])}</span> | 毛利率 {M['total_profit']/M['total_revenue']*100:.1f}%
            <div style="margin-top:3px;color:#94a3b8">手机口径: {fmt_naira(M.get('total_smart_revenue', 0))} · 毛利 {fmt_naira(M.get('total_smart_profit', 0))} ({(M.get('total_smart_profit',0)/M['total_smart_revenue']*100) if M.get('total_smart_revenue') else 0:.1f}%)</div>
        </div>
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
</div><!-- /Z1 核心指标 -->

<!-- ===== REPORT MODE ===== -->
<div id="mode-report">

<!-- Z2 经营全景 -->
<div class="zone">
<div class="zone-title"><span class="zone-bar"></span>经营全景</div>

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
</div><!-- /Z2 -->

{dm_zone_html}

<!-- Z3 经营洞察 -->
<div class="zone">
<div class="zone-title"><span class="zone-bar"></span>经营洞察<span class="zone-note">30 秒读懂「发生了什么、为什么、该做什么」</span></div>

<!-- ===== 一屏经营摘要 ===== -->
<div class="section report-only">
    <div class="section-header">
        <div class="section-title"><span class="num">🎯</span> 一屏经营摘要</div>
        <div style="font-size:11px;color:var(--text2)">亮点 / 风险 / 建议动作 — 30 秒读完</div>
    </div>
    <div class="section-body">{cockpit_summary()}</div>
</div>

<!-- ===== AI 智能分析 ===== -->
<div class="section report-only">
    <div class="section-header">
        <div class="section-title"><span class="num">🤖</span> AI 智能分析</div>
        <div style="font-size:11px;color:var(--text2)">跨模块交叉关联推理 — 自动挖掘「发生了什么、为什么、该做什么」</div>
    </div>
    <div class="section-body">{cockpit_ai_insights()}</div>
</div>

<!-- M8 Gap (Report) -->
<div class="summary-box report-only">
    <h3>🎯 月度追赶方案</h3>
    <p>{recovery_text}</p>
</div>
</div><!-- /Z3 -->

<!-- Z4 汇报文案 -->
<div class="zone">
<div class="zone-title"><span class="zone-bar"></span>汇报文案<span class="zone-note">可直接转发的完整数据汇报</span></div>

<!-- 数据汇报 (Report) -->
<div class="section report-only">
    <div class="section-header">
        <div class="section-title"><span class="num">📋</span> 数据汇报</div>
    </div>
    <div class="section-body">
        <div class="report-summary">{data_report}</div>
    </div>
</div>
</div><!-- /Z4 -->

</div><!-- end report mode -->

<!-- ===== ANALYSIS MODE ===== -->
<div id="mode-analysis" style="display:none">

<!-- 模块导航栏: 按主题分组, 一次只展开一组, 缩短单页长度 (按钮顺序与内容顺序一致: 总览→门店任务→驾驶舱) -->
<div class="mod-nav" id="mod-nav">
    <button class="mod-nav-btn" data-g="overview" onclick="switchModGroup('overview',this)">📊 总览速览</button>
    <button class="mod-nav-btn" data-g="task" onclick="switchModGroup('task',this)">🎯 门店任务</button>
    <button class="mod-nav-btn active" data-g="cockpit" onclick="switchModGroup('cockpit',this)">🎯 经营驾驶舱</button>
    <button class="mod-nav-btn" data-g="store" onclick="switchModGroup('store',this)">🏪 门店明细</button>
    <button class="mod-nav-btn" data-g="model" onclick="switchModGroup('model',this)">📱 型号分析</button>
    <button class="mod-nav-btn" data-g="stock" onclick="switchModGroup('stock',this)">📦 库存周转</button>
    <button class="mod-nav-btn" data-g="hr" onclick="switchModGroup('hr',this)">👥 人效诊断</button>
    <button class="mod-nav-btn all" data-g="all" onclick="switchModGroup('all',this)">📑 全部展开</button>
</div>

<!-- M1: Full Store Target Table -->
<div class="section analysis-only" data-mod="task">
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

<!-- ===== 经营驾驶舱 (排在门店任务之后) ===== -->
{_sec('🎯', '月底达成预测（趋势外推）', cockpit_forecast(), note='按近3日/近5日/全期日均三种口径预测月底销量')}
{_sec('📅', '去年同期同比（2025 vs 2026）', cockpit_yoy())}
{_sec('💰', '库存资金占用 & 库龄结构', cockpit_inv_value(), note='门店仓 手机+平板，不含总仓')}
{_sec('📊', '品牌毛利结构象限（销量 × 毛利率）', cockpit_brand_matrix())}
{_sec('❤️', '门店健康度综合评分', cockpit_health(), note='四维加权：达成40% / 周转25% / 稳定20% / 人效15%')}
{_sec('⚠️', '缺货损失估算', cockpit_stockout())}
{_sec('🏷️', '价量联动归因（调价效果跟踪）', cockpit_price_volume())}

<!-- 总览速览: 日/月销售核心摘要 (Module 20/21 精华) -->
{overview_dm_section()}

<!-- M2: Store Category -->
<div class="section analysis-only" data-mod="overview">
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
<div class="section analysis-only" data-mod="overview">
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
<div class="section analysis-only" data-mod="store">
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
<div class="section analysis-only" data-mod="overview">
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

<div data-mod="model">{model_section_html}</div>

<!-- M12: Store Daily Sales Volatility -->
<div class="section analysis-only" data-mod="store">
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
<div class="section analysis-only" data-mod="stock" style="background:transparent">
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
                <th>排名</th><th>品牌</th><th>门店可卖数</th><th>总仓可卖数</th><th>日均销量</th><th>周转天数</th><th>评级</th><th>平均单价</th><th>资金占用(占比)</th>
            </tr></thead><tbody>{m6_brand_turnover_rows()}</tbody></table></div>
        </div>
        <div id="inv-model" class="inv-sub" style="display:none">
            <h4>型号库存周转天数排名（所有门店仓可卖数 ÷ 日均销量，按日销降序，手机+平板）</h4>
            <div style="margin-bottom:10px;display:flex;align-items:center;gap:8px">
                <label style="color:var(--text2);font-size:12px">品牌筛选：</label>
                <select id="model-brand-filter" onchange="filterModelTurnover()" style="padding:6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px">
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
                <th>排名</th><th>门店</th><th>库存总数</th><th>日均销量</th><th>周转天数</th><th>评级</th><th>资金占用</th><th>建议</th>
            </tr></thead><tbody>{m6_turnover_rows()}</tbody></table></div>
        </div>
        <div id="inv-store-model" class="inv-sub" style="display:none">
            <h4>单店型号库存周转（手机+平板，按销量降序，不含总仓）</h4>
            <div style="margin-bottom:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <label style="color:var(--text2);font-size:12px">门店：</label>
                <div style="position:relative">
                    <button id="store-combo-btn" onclick="toggleStoreCombo()"
                     style="padding:6px 30px 6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px;cursor:pointer;text-align:left;min-width:180px;position:relative">
                        选择门店 ▾
                    </button>
                    <div id="store-combo-dropdown" style="display:none;position:absolute;top:100%;left:0;width:280px;background:var(--surface);border:1px solid var(--border);border-radius:6px;z-index:1000;margin-top:2px;box-shadow:0 8px 24px rgba(15,23,42,0.12)">
                        <div style="padding:6px 8px;border-bottom:1px solid var(--border)">
                            <input type="text" id="store-combo-search" placeholder="输入门店名搜索..."
                             style="width:100%;padding:6px 10px;border-radius:4px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box"
                             oninput="filterStoreCombo()" onkeydown="handleComboKey(event)" onclick="event.stopPropagation()">
                        </div>
                        <div id="store-combo-list" style="max-height:350px;overflow-y:auto"></div>
                    </div>
                </div>
                <input type="hidden" id="store-select" value="">
                <label style="color:var(--text2);font-size:12px">品类：</label>
                <select id="sm-cat-filter" onchange="filterStoreModels()" style="padding:6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px">
                    <option value="">全部品类</option>
                    <option value="手机">手机</option>
                    <option value="平板">平板</option>
                </select>
                <label style="color:var(--text2);font-size:12px">品牌：</label>
                <select id="sm-brand-filter" onchange="filterStoreModels()" style="padding:6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:12px">
                    <option value="">全部品牌</option>
                </select>
            </div>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>排名</th><th>品类</th><th>品牌</th><th>型号</th><th>可卖数</th><th>在途</th><th>当月销量</th><th>周转天数</th><th>总仓库存</th><th>评级</th><th>预警/建议</th><th>资金占用</th>
            </tr></thead><tbody id="store-model-tbody"></tbody></table></div>
        </div>
        <div id="inv-overstock" class="inv-sub" style="display:none">
            <h4>门店滞销积压机型 Top 10（有库存但全公司月销量为零，按库存降序）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>门店</th><th>品牌</th><th>型号</th><th>库存</th><th>资金占用</th><th>建议</th>
            </tr></thead><tbody>{m6_overstock_rows()}</tbody></table></div>
        </div>
        <div id="inv-lowstock" class="inv-sub" style="display:none">
            <h4>热门品牌缺货预警 Top 40（库存≤3台 或 周转天数&lt;4天，且全公司月销量&gt;0；按 0 库存优先、月销量降序取前 40）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>门店</th><th>品牌</th><th>型号</th><th>门店库存</th><th>周转天数</th><th>总仓库存</th><th>全公司月销</th><th>建议</th>
            </tr></thead><tbody>{m6_lowstock_rows()}</tbody></table></div>
        </div>
        <div id="inv-general" class="inv-sub" style="display:none">
            <h4>总仓死库 Top 10（GENERAL-PHONES，有库存但全公司月销量为零，按库存降序）</h4>
            <div class="tbl-wrap"><table class="m6-table"><thead><tr>
                <th>品牌</th><th>型号</th><th>库存</th><th>资金占用</th><th>建议</th>
            </tr></thead><tbody>{m6_general_rows()}</tbody></table></div>
        </div>
        <div id="inv-cost" class="inv-sub" style="display:none">
            <h4>商品成本价查询（按批次进货成本，加权均价 = Σ(结存×单价) ÷ 总结存）</h4>
            <div style="margin-bottom:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                <input type="text" id="cost-search" placeholder="输入型号名称搜索..." oninput="filterCostTable()" style="flex:1;min-width:220px;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:13px">
                <select id="cost-brand-filter" onchange="filterCostTable()" style="padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:13px">
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
<div class="section analysis-only" data-mod="hr">
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
<div class="section analysis-only" data-mod="task">
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
            <table id="tbl_m8"><thead><tr>
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
            <td style="text-align:left;max-width:200px;overflow:hidden;text-overflow:ellipsis">{r['model']}{promo_tag}</td>
            <td>{price_detail_cmp}</td>
            <td>{price_detail_cur}</td>
            <td style="color:{direction_color};font-weight:700">{direction} {abs(r['pct'])}%</td>
            <td style="color:{direction_color}">₦{abs(int(r['diff'])):,}</td>
            <td>{sales_tag}</td>
        </tr>'''

    price_page_html = f"""
<div id="page-prices" style="display:none">

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

# ===== 年度 KPI 四模块 (①年度任务 ②单店模型 ③增值业务 ④配件配比率) =====
kpi_page_html = ''
kpi_js = ''
if K:
    K1 = K.get('module1_annual', {})
    K2 = K.get('module2_store_model', {})
    K3 = K.get('module3_value_added', {})
    K4 = K.get('module4_accessory', {})
    KMETA = K.get('meta', {})
    _partial_ym = KMETA.get('partial_month')
    _cutoff = KMETA.get('data_cutoff', '')
    _cutoff_md = f"{int(_cutoff[5:7])}月{int(_cutoff[8:10])}日" if len(_cutoff) >= 10 else _cutoff

    def _rcol(rate, base):
        """完成率 vs 基准(时间进度) 着色: 达标绿 / 落后5pp内黄 / 更大落后红"""
        d = rate - base
        return '#16a34a' if d >= 0 else ('#d97706' if d >= -0.05 else '#dc2626')

    # ---------- 模块① 年度任务 ----------
    _t = K1.get('target', {})
    _a = K1.get('actual', {})
    _c = K1.get('completion', {})
    _qty_ytd = _a.get('qty_ytd', 0)
    _qty_annual = _t.get('qty_annual', 0)
    _qty_rate = _c.get('qty_ytd_rate', 0)
    _tp = _c.get('time_progress', 0)
    _qty_diff = _c.get('qty_progress_diff_pp', 0)
    _rev_ytd = _a.get('rev_rmb_ytd', 0)
    _rev_annual = _t.get('rev_rmb_annual', 0)
    _rev_rate = _c.get('rev_rmb_ytd_rate', 0)
    _rev_diff = _c.get('rev_progress_diff_pp', 0)
    _rev_ngn_ytd = _a.get('rev_ngn_ytd', 0)
    _sep_ym = _partial_ym or ''
    _sep_qty = _a.get('qty_monthly', {}).get(_sep_ym) if _sep_ym else None
    _sep_tgt = _t.get('qty_monthly', [0]*12)[int(_sep_ym[5:7])-1] if _sep_ym else 0

    # 分品牌行
    _brand_rows = K1.get('brand', {}).get('rows', [])
    _brand_tbl = ''
    for _b in _brand_rows:
        _br = _b.get('alloc_completion_rate', 0)
        _bc = _rcol(_br, _qty_rate)  # 与传音整体完成率比较着色
        _brand_tbl += f"""<tr><td style="font-weight:700;color:#2563eb">{_b['brand']}</td>
            <td style="text-align:right">{fmt_n(_b['ytd_qty'])}</td>
            <td style="text-align:right">{_b['ytd_share']*100:.1f}%</td>
            <td style="text-align:right">{fmt_n(_b['alloc_target_ytd'])}</td>
            <td style="text-align:right;font-weight:700;color:{_bc}">{_br*100:.1f}%</td></tr>"""

    # 月度表 (12个月, 全量)
    # 注意: brand.monthly 里 month 是整数(1-12), 查询时也用整数, 避免类型不匹配
    _bv = {r['brand']: {int(m['month']): m['actual'] for m in r.get('monthly', [])} for r in _brand_rows}
    _m1_rows = ''
    for mi in range(1, 13):
        ym = f'2026-{mi:02d}'
        _lb = f"{mi}月" + ("*" if ym == _partial_ym else "")
        qt = _t.get('qty_monthly', [0]*12)[mi-1]
        qa = _a.get('qty_monthly', {}).get(ym)
        rate = f"{qa/qt*100:.1f}%" if (qa is not None and qt) else '—'
        rt_wan = _t.get('rev_rmb_monthly', [0]*12)[mi-1] / 1e4
        ra = _a.get('rev_rmb_monthly', {}).get(ym)
        ra_wan = f"{ra/1e4:,.0f}" if ra is not None else '—'
        rr = f"{(ra/1e4)/rt_wan*100:.1f}%" if (ra is not None and rt_wan) else '—'
        def _bv_(b):
            v = _bv.get(b, {}).get(mi)
            return f"{v:,.0f}" if v is not None else '—'
        _m1_rows += f"""<tr><td style="font-weight:600">{_lb}</td>
            <td style="text-align:right">{qt:,.0f}</td>
            <td style="text-align:right">{f"{qa:,.0f}" if qa is not None else '—'}</td>
            <td style="text-align:right;{('color:'+_rcol(qa/qt, _tp)+';font-weight:700') if (qa is not None and qt) else ''}">{rate}</td>
            <td style="text-align:right">{_bv_('TECNO')}</td>
            <td style="text-align:right">{_bv_('INFINIX')}</td>
            <td style="text-align:right">{_bv_('ITEL')}</td>
            <td style="text-align:right">{rt_wan:,.0f}</td>
            <td style="text-align:right">{ra_wan}</td>
            <td style="text-align:right">{rr}</td></tr>"""

    # ---------- 模块② 单店模型 ----------
    _m2_ratio = K2.get('ratio', 0.30)
    _m2_monthly = K2.get('monthly', [])
    _m2_latest = K2.get('latest', {})
    _m2_detail = K2.get('latest_detail', [])
    _m2_detail_rows = ''
    for _d in _m2_detail:
        _q = '✓' if _d.get('qualified') else ''
        _qc = ' style="color:#16a34a;font-weight:700"' if _d.get('qualified') else ''
        _m2_detail_rows += f"""<tr><td>{_d['store']}</td>
            <td style="text-align:right">{fmt_naira(_d['total_rev'])}</td>
            <td style="text-align:right">{fmt_naira(_d['nonphone_rev'])}</td>
            <td style="text-align:right">{_d['nonphone_share']*100:.1f}%</td>
            <td style="text-align:right">{_d['nonphone_margin']*100:.1f}%</td>
            <td style="text-align:center"{_qc}>{_q}</td></tr>"""
    _m2_qlist = ', '.join(_d['store'].split('-')[0] for _d in _m2_detail if _d.get('qualified')) or '—'

    # ---------- 模块③ 增值业务 ----------
    _m3_cum = K3.get('cumulative', {})
    _m3_by = _m3_cum.get('by_source', {})
    _m3_labels = K3.get('source_labels', {})
    _m3_monthly = K3.get('monthly', [])
    _m3_total = _m3_cum.get('total_ngn', 0)
    _m3_total_rmb = _m3_cum.get('total_rmb', 0)
    _m3_rows = ''
    for _m in _m3_monthly:
        _lb = f"{int(_m['month'][5:7])}月" + ("*" if _m['month'] == _partial_ym else "")
        _m3_rows += f"""<tr><td style="font-weight:600">{_lb}</td>
            <td style="text-align:right">{fmt_naira(_m.get('operator', 0))}</td>
            <td style="text-align:right">{fmt_naira(_m.get('rental', 0))}</td>
            <td style="text-align:right;font-weight:700">{fmt_naira(_m.get('total', 0))}</td></tr>"""
    _m3_excluded = K3.get('excluded_service_cats', [])

    # ---------- 模块④ 配件配比率 ----------
    _m4_target = K4.get('target', 0.60)
    _m4_cur = K4.get('current', {})
    _m4_monthly = K4.get('monthly', [])
    _m4_ok_months = sum(1 for m in _m4_monthly if m.get('qualified'))
    _m4_rows = ''
    for _m in _m4_monthly:
        _lb = f"{int(_m['month'][5:7])}月" + ("*" if _m['month'] == _partial_ym else "")
        _qc = ' style="color:#16a34a;font-weight:700"' if _m.get('qualified') else ' style="color:#dc2626"'
        _m4_rows += f"""<tr><td style="font-weight:600">{_lb}</td>
            <td style="text-align:right">{fmt_n(_m.get('accessory_qty', 0))}</td>
            <td style="text-align:right">{fmt_n(_m.get('smart_qty', 0))}</td>
            <td style="text-align:right;font-weight:700"{_qc}>{_m.get('ratio', 0)*100:.1f}%</td>
            <td style="text-align:center"{_qc}>{'✓' if _m.get('qualified') else '✗'}</td></tr>"""

    _m2_rate_c = '#16a34a' if _m2_latest.get('qualified_rate', 0) >= 1 else ('#d97706' if _m2_latest.get('qualified_rate', 0) >= 0.6 else '#dc2626')
    _m4_cur_ok = _m4_cur.get('qualified', False)

    kpi_page_html = f"""
<!-- ===== PAGE: 年度任务 ===== -->
<div id="page-kpi" style="display:none">

<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-label">传音智能机 YTD <span style="font-weight:400">(TECNO+INFINIX+ITEL)</span></div>
        <div class="kpi-value">{fmt_n(_qty_ytd)} <span style="font-size:0.45em;color:#94a3b8">/ {_qty_annual/10000:.0f}万台</span></div>
        <div class="kpi-sub">完成率 <b style="color:{_rcol(_qty_rate, _tp)}">{_qty_rate*100:.1f}%</b>
            <div style="margin-top:3px">进度差 <b style="color:{_rcol(_qty_rate, _tp)}">{_qty_diff:+.1f}pp</b> <span style="color:#94a3b8">vs 时间进度 {_tp*100:.1f}%</span></div>
        </div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">手机零售额 YTD <span style="font-weight:400">(RMB)</span></div>
        <div class="kpi-value" style="color:#2563eb">¥{_rev_ytd/1e8:.2f}亿 <span style="font-size:0.45em;color:#94a3b8">/ ¥{_rev_annual/1e8:.2f}亿</span></div>
        <div class="kpi-sub">完成率 <b style="color:{_rcol(_rev_rate, _tp)}">{_rev_rate*100:.1f}%</b>（进度差 {_rev_diff:+.1f}pp）
            <div style="margin-top:3px;color:#94a3b8">奈拉口径 {fmt_naira(_rev_ngn_ytd)} · 固定汇率 1元≈205奈拉 折算</div>
        </div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">年度时间进度</div>
        <div class="kpi-value">{_tp*100:.1f}%</div>
        <div class="kpi-sub">数据截至 {_cutoff_md}（自然日口径）</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">{int(_sep_ym[5:7]) if _sep_ym else '-'}月任务 <span style="font-weight:400">(部分月*)</span></div>
        <div class="kpi-value" style="color:{'#d97706' if _sep_qty and _sep_qty < _sep_tgt else '#16a34a'}">{fmt_n(_sep_qty) if _sep_qty is not None else '—'}</div>
        <div class="kpi-sub">月目标 {fmt_n(_sep_tgt)} 台 · {(_sep_qty/_sep_tgt*100) if (_sep_qty and _sep_tgt) else 0:.1f}%（截至{_cutoff_md}）</div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <div class="section-title"><span class="num">①</span> 年度任务完成情况（传音智能机台量 & 手机零售额）</div>
        <div style="font-size:11px;color:var(--text2)">目标 =《各部门任务拆解》王浩口径 · 9月为部分月(标*)</div>
    </div>
    <div class="section-body">
        <div style="height:340px;margin-bottom:14px"><canvas id="chart_kpi_m1"></canvas></div>
        <div class="tbl-wrap" style="max-height:420px">
            <table id="tbl_kpi_m1"><thead><tr>
                <th>月份</th><th>传音目标(台)</th><th>传音实际(台)</th><th>台量完成率</th>
                <th>TECNO(台)</th><th>INFINIX(台)</th><th>ITEL(台)</th>
                <th>零售额目标(万¥)</th><th>零售额实际(万¥)</th><th>零售额完成率</th>
            </tr></thead><tbody>{_m1_rows}</tbody></table>
        </div>
        <div class="tbl-wrap" style="max-height:220px;margin-top:12px">
            <table id="tbl_kpi_brand"><thead><tr>
                <th>品牌</th><th>YTD实际(台)</th><th>销量占比</th><th>均分年目标(台)</th><th>均分完成率</th>
            </tr></thead><tbody>{_brand_tbl}</tbody></table>
        </div>
        <div style="font-size:11px;color:var(--text2);margin-top:8px;line-height:1.7">
            口径: 智能机含平板 · 分品牌任务 = 传音月度任务 ÷ 3 均分(月均口径) · RMB 按固定汇率 1元≈205奈拉 折算
            · 年度目标为任务拆解表口径, 与门店月度 TARGET 口径不同, 不可直接对比
        </div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <div class="section-title"><span class="num">②</span> 月度单店模型完成情况</div>
        <div style="font-size:11px;color:var(--text2)">达标 = 非手机内占比≥15% 且 非手机毛利率≥20% · 月目标 = 当月活跃门店×{_m2_ratio:.0%}(暂定算法)</div>
    </div>
    <div class="section-body">
        <div class="kpi-row" style="margin-bottom:14px">
            <div class="kpi-card"><div class="kpi-label">当月达标门店</div>
                <div class="kpi-value" style="color:var(--text)">{_m2_latest.get('qualified_stores', 0)} <span style="font-size:0.45em;color:#94a3b8">/ 目标 {_m2_latest.get('target_stores', 0)} 家</span></div>
                <div class="kpi-sub">活跃 {_m2_latest.get('active_stores', 0)} 家 × {_m2_ratio:.0%}（{(_m2_latest.get('month') or '')}{' 部分月' if _m2_latest.get('is_partial') else ''}）</div></div>
            <div class="kpi-card"><div class="kpi-label">当月达成率</div>
                <div class="kpi-value" style="color:{_m2_rate_c}">{_m2_latest.get('qualified_rate', 0)*100:.1f}%</div>
                <div class="kpi-sub">达标门店: {_m2_qlist}</div></div>
            <div class="kpi-card"><div class="kpi-label">判定标准</div>
                <div class="kpi-value" style="font-size:20px;line-height:1.5;padding-top:6px">非手机占比 ≥15%<br>非手机毛利率 ≥20%</div>
                <div class="kpi-sub">非手机 = 除智能机/功能机/平板外全部品类</div></div>
        </div>
        <div style="height:300px;margin-bottom:14px"><canvas id="chart_kpi_m2"></canvas></div>
        <div class="tbl-wrap" style="max-height:280px;margin-bottom:12px">
            <table id="tbl_kpi_m2"><thead><tr>
                <th>月份</th><th>活跃门店</th><th>目标门店</th><th>达标门店</th><th>达成率</th>
            </tr></thead><tbody>
            {''.join(f"""<tr><td style="font-weight:600">{int(m['month'][5:7])}月{'*' if m.get('is_partial') else ''}</td>
                <td style="text-align:right">{m['active_stores']}</td>
                <td style="text-align:right">{m['target_stores']}</td>
                <td style="text-align:right;font-weight:700">{m['qualified_stores']}</td>
                <td style="text-align:right">{m['qualified_rate']*100:.1f}%</td></tr>""" for m in _m2_monthly)}
            </tbody></table>
        </div>
        <div style="font-size:12px;font-weight:700;color:var(--text);margin-bottom:6px">当月门店明细（全量 {len(_m2_detail)} 家，按非手机占比降序）</div>
        <div class="tbl-wrap" style="max-height:420px">
            <table id="tbl_kpi_m2d"><thead><tr>
                <th>门店</th><th>总销售额</th><th>非手机销售额</th><th>非手机占比</th><th>非手机毛利率</th><th>达标</th>
            </tr></thead><tbody>{_m2_detail_rows}</tbody></table>
        </div>
        <div style="font-size:11px;color:var(--text2);margin-top:8px">口径: 非手机内占比 = 非手机销售额 ÷ 门店总销售额; 毛利率按非手机毛利÷非手机销售额; 月目标占比为暂定算法, 可随时调整</div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <div class="section-title"><span class="num">③</span> 增值业务收入汇总（运营商 / 租金）</div>
        <div style="font-size:11px;color:var(--text2)">口径 = 销售明细「服务」类 · 只含电信业务与租金 · {KMETA.get('months_available', [''])[0]} ~ {_cutoff_md}</div>
    </div>
    <div class="section-body">
        <div class="kpi-row" style="margin-bottom:14px">
            <div class="kpi-card"><div class="kpi-label">累计增值业务收入</div>
                <div class="kpi-value" style="color:#16a34a">{fmt_naira(_m3_total)} <span style="font-size:0.42em;font-weight:500;color:#94a3b8">{fmt_rmb(_m3_total)}</span></div>
                <div class="kpi-sub">{len(_m3_monthly)} 个月累计</div></div>
            <div class="kpi-card"><div class="kpi-label">运营商 <span style="font-weight:400">(SIM卡/话费/Modem)</span></div>
                <div class="kpi-value" style="color:#2563eb">{fmt_naira(_m3_by.get('operator', 0))}</div>
                <div class="kpi-sub">占比 {_m3_by.get('operator', 0)/_m3_total*100 if _m3_total else 0:.1f}%</div></div>
            <div class="kpi-card"><div class="kpi-label">租金 <span style="font-weight:400">(摊位/门店)</span></div>
                <div class="kpi-value" style="color:#d97706">{fmt_naira(_m3_by.get('rental', 0))}</div>
                <div class="kpi-sub">占比 {_m3_by.get('rental', 0)/_m3_total*100 if _m3_total else 0:.1f}%</div></div>
            <div class="kpi-card"><div class="kpi-label">已排除项</div>
                <div class="kpi-value" style="font-size:16px;line-height:1.5;padding-top:6px;color:#64748b">订金 / 软件下载<br>配送费 / 分期等</div>
                <div class="kpi-sub">不计入增值业务收入</div></div>
        </div>
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;margin-bottom:14px">
            <div style="height:320px"><canvas id="chart_kpi_m3"></canvas></div>
            <div style="height:320px"><canvas id="chart_kpi_m3_share"></canvas></div>
        </div>
        <div class="tbl-wrap" style="max-height:400px">
            <table id="tbl_kpi_m3"><thead><tr>
                <th>月份</th><th>运营商</th><th>租金</th><th>合计</th>
            </tr></thead><tbody>{_m3_rows}</tbody></table>
        </div>
        <div style="font-size:11px;color:var(--text2);margin-top:8px;line-height:1.7">
            来源识别: 运营商=TELECOMMUNICATION*(双字段) · 租金=MONTHLY RENTAL(摊位/门店) + DOWNLOAD(下载服务) · 排除订金/配送费 · 售后/分期无明细数据(暂不统计)
            {'· 已排除: ' + '; '.join(_m3_excluded[:5]) + (' 等' if len(_m3_excluded) > 5 else '') if _m3_excluded else ''}
        </div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <div class="section-title"><span class="num">④</span> 配件配比率情况（配件销售数量 ÷ 智能机销售数量）</div>
        <div style="font-size:11px;color:var(--text2)">考核口径 ≥{_m4_target:.0%} · 智能机含平板</div>
    </div>
    <div class="section-body">
        <div class="kpi-row" style="margin-bottom:14px">
            <div class="kpi-card"><div class="kpi-label">当月配比率</div>
                <div class="kpi-value" style="color:{'#16a34a' if _m4_cur_ok else '#dc2626'}">{_m4_cur.get('ratio', 0)*100:.1f}%</div>
                <div class="kpi-sub">目标 ≥{_m4_target:.0%} · {'达标' if _m4_cur_ok else '未达标'}（{(_m4_cur.get('month') or '')} 部分月）</div></div>
            <div class="kpi-card"><div class="kpi-label">当月配件 / 智能机数量</div>
                <div class="kpi-value">{fmt_n(_m4_cur.get('accessory_qty', 0))} <span style="font-size:0.45em;color:#94a3b8">/ {fmt_n(_m4_cur.get('smart_qty', 0))}</span></div>
                <div class="kpi-sub">件数口径（净销, 含退货冲减）</div></div>
            <div class="kpi-card"><div class="kpi-label">年度达标月份</div>
                <div class="kpi-value" style="color:{'#16a34a' if _m4_ok_months == len(_m4_monthly) else '#d97706'}">{_m4_ok_months}/{len(_m4_monthly)}</div>
                <div class="kpi-sub">月度配比率全部 ≥{_m4_target:.0%}</div></div>
        </div>
        <div style="height:300px;margin-bottom:14px"><canvas id="chart_kpi_m4"></canvas></div>
        <div class="tbl-wrap" style="max-height:400px">
            <table id="tbl_kpi_m4"><thead><tr>
                <th>月份</th><th>配件数量(件)</th><th>智能机数量(台)</th><th>配比率</th><th>达标</th>
            </tr></thead><tbody>{_m4_rows}</tbody></table>
        </div>
    </div>
</div>

</div><!-- end page-kpi -->
"""

    # ---------- 图表数据 + JS (普通字符串+占位符替换, 避免花括号转义) ----------
    _labels_m = [f"{int(m['month'][5:7])}月" + ("*" if m.get('is_partial') else '') for m in _m2_monthly]
    kpi_data = {
        'm1': {
            'labels': [f"{i}月" + ("*" if f"2026-{i:02d}" == _partial_ym else "") for i in range(1, 13)],
            'actual': [_a.get('qty_monthly', {}).get(f"2026-{i:02d}") for i in range(1, 13)],
            'target': _t.get('qty_monthly', []),
            'revActual': [_a.get('rev_rmb_monthly', {}).get(f"2026-{i:02d}") for i in range(1, 13)],
            'revTarget': _t.get('rev_rmb_monthly', []),
        },
        'm2': {
            'labels': _labels_m,
            'qualified': [m['qualified_stores'] for m in _m2_monthly],
            'targetStores': [m['target_stores'] for m in _m2_monthly],
        },
        'm3': {
            'labels': _labels_m,
            'operator': [round(m.get('operator', 0)/1e6, 2) for m in _m3_monthly],
            'rental': [round(m.get('rental', 0)/1e6, 2) for m in _m3_monthly],
            'shareLabels': [_m3_labels.get(k, k) for k in ['operator', 'rental']],
            'shareValues': [round(_m3_by.get(k, 0)/1e6, 2) for k in ['operator', 'rental']],
        },
        'm4': {
            'labels': _labels_m,
            'ratio': [round(m.get('ratio', 0)*100, 1) for m in _m4_monthly],
            'targetPct': round(_m4_target*100, 1),
        },
    }

    kpi_js = """
// ===== KPI ANNUAL CHARTS =====
var KPI = __KPI_DATA__;
var _kpiGrid = { color: 'rgba(51,65,85,0.18)' };
var _kpiTick = { color: '#94a3b8' };
function _kpiBaseOpts(yTitle, y1Cfg) {
    var opts = {
        responsive: true, maintainAspectRatio: false,
        layout: { padding: { top: 18 } },
        plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', usePointStyle: true } } },
        scales: {
            x: { grid: { display: false }, ticks: _kpiTick },
            y: { type: 'linear', position: 'left', beginAtZero: true, grid: _kpiGrid, ticks: Object.assign({ callback: v => v.toLocaleString() }, _kpiTick), title: { display: !!yTitle, text: yTitle || '', color: '#94a3b8', font: { size: 11 } } }
        }
    };
    if (y1Cfg) {
        opts.scales.y1 = { type: 'linear', position: 'right', beginAtZero: true, grid: { display: false }, ticks: Object.assign({}, _kpiTick, y1Cfg.ticks || {}) };
    }
    return opts;
}
function initKpiCharts() {
    // ① 年度任务: 月度台量 柱(实际) + 线(目标)
    var c1 = document.getElementById('chart_kpi_m1');
    if (c1) new Chart(c1, {
        type: 'bar',
        data: { labels: KPI.m1.labels, datasets: [
            { label: '传音实际(台)', data: KPI.m1.actual, backgroundColor: 'rgba(37,99,235,0.75)', borderRadius: 4, order: 2,
              datalabels: { anchor: 'center', align: 'center', color: '#ffffff', font: { size: 9, weight: 'bold' },
                  display: function(ctx) { return ctx.dataset.data[ctx.dataIndex] != null; },
                  formatter: function(v) { return v.toLocaleString(); } } },
            { label: '月度目标(台)', data: KPI.m1.target, type: 'line', borderColor: '#d97706', borderWidth: 2, borderDash: [6, 4], pointRadius: 2, backgroundColor: 'transparent', order: 1,
              datalabels: { anchor: 'end', align: 'top', offset: 4, color: '#cbd5e1', font: { size: 9, weight: 'bold' },
                  formatter: function(v) { return v.toLocaleString(); } } }
        ]},
        options: _kpiBaseOpts('台')
    });
    // ② 单店模型: 达标门店数 柱 + 目标 线
    var c2 = document.getElementById('chart_kpi_m2');
    if (c2) new Chart(c2, {
        type: 'bar',
        data: { labels: KPI.m2.labels, datasets: [
            { label: '达标门店数', data: KPI.m2.qualified, backgroundColor: 'rgba(22,163,74,0.75)', borderRadius: 4, order: 2,
              datalabels: { anchor: 'end', align: 'top', offset: 2, color: '#cbd5e1', font: { size: 10, weight: 'bold' },
                  formatter: function(v) { return v; } } },
            { label: '月度目标门店数', data: KPI.m2.targetStores, type: 'line', borderColor: '#d97706', borderWidth: 2, borderDash: [6, 4], pointRadius: 2, backgroundColor: 'transparent', order: 1,
              datalabels: { display: false } }
        ]},
        options: _kpiBaseOpts('家')
    });
    // ③ 增值业务: 月度堆叠柱(百万₦) + 来源占比环形
    var c3 = document.getElementById('chart_kpi_m3');
    if (c3) new Chart(c3, {
        type: 'bar',
        data: { labels: KPI.m3.labels, datasets: [
            { label: '运营商', data: KPI.m3.operator, backgroundColor: '#2563eb',
              datalabels: { anchor: 'center', align: 'center', color: '#ffffff', font: { size: 9, weight: 'bold' },
                  display: function(ctx) { return ctx.dataset.data[ctx.dataIndex] >= 0.5; },
                  formatter: function(v) { return v.toFixed(1); } } },
            { label: '租金', data: KPI.m3.rental, backgroundColor: '#16a34a',
              datalabels: { anchor: 'center', align: 'center', color: '#ffffff', font: { size: 9, weight: 'bold' },
                  display: function(ctx) { return ctx.dataset.data[ctx.dataIndex] >= 0.5; },
                  formatter: function(v) { return v.toFixed(1); } } }
        ]},
        options: { responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', usePointStyle: true } } },
            scales: { x: { stacked: true, grid: { display: false }, ticks: _kpiTick },
                      y: { stacked: true, beginAtZero: true, grid: _kpiGrid, ticks: Object.assign({ callback: v => v.toFixed(0) + 'M' }, _kpiTick), title: { display: true, text: '百万₦', color: '#94a3b8', font: { size: 11 } } } } }
    });
    var c3s = document.getElementById('chart_kpi_m3_share');
    if (c3s) new Chart(c3s, {
        type: 'doughnut',
        data: { labels: KPI.m3.shareLabels, datasets: [{ data: KPI.m3.shareValues, backgroundColor: ['#2563eb', '#16a34a'], borderWidth: 2, borderColor: '#ffffff' }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '58%',
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', usePointStyle: true } },
                datalabels: { color: '#ffffff', font: { size: 10, weight: 'bold' },
                    formatter: function(v, ctx) { var t = KPI.m3.shareValues.reduce(function(a, b) { return a + b; }, 0) || 1; var p = v / t * 100; return p >= 3 ? p.toFixed(1) + '%' : ''; } },
                tooltip: { callbacks: { label: function(ctx) { var t = KPI.m3.shareValues.reduce(function(a, b) { return a + b; }, 0) || 1; return ctx.label + ': ' + (ctx.parsed / t * 100).toFixed(1) + '% (₦' + ctx.parsed.toFixed(1) + 'M)'; } } } } }
    });
    // ④ 配件配比率: 月度配比率 柱 + 60% 目标线
    var c4 = document.getElementById('chart_kpi_m4');
    if (c4) new Chart(c4, {
        type: 'bar',
        data: { labels: KPI.m4.labels, datasets: [
            { label: '配件配比率(%)', data: KPI.m4.ratio, backgroundColor: KPI.m4.ratio.map(function(v) { return v >= KPI.m4.targetPct ? 'rgba(22,163,74,0.75)' : 'rgba(220,38,38,0.75)'; }), borderRadius: 4, order: 2,
              datalabels: { anchor: 'center', align: 'center', color: '#ffffff', font: { size: 9, weight: 'bold' },
                  formatter: function(v) { return v + '%'; } } },
            { label: '考核目标(' + KPI.m4.targetPct + '%)', data: KPI.m4.labels.map(function() { return KPI.m4.targetPct; }), type: 'line', borderColor: '#dc2626', borderWidth: 2, borderDash: [6, 4], pointRadius: 0, backgroundColor: 'transparent', order: 1,
              datalabels: { display: false } }
        ]},
        options: { responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', usePointStyle: true } } },
            scales: { x: { grid: { display: false }, ticks: _kpiTick },
                      y: { beginAtZero: true, grid: _kpiGrid, ticks: Object.assign({ callback: v => v + '%' }, _kpiTick) } } }
    });
}
""".replace('__KPI_DATA__', json.dumps(kpi_data, ensure_ascii=False))


html += f"""

{price_page_html}

{history_page_html}

{kpi_page_html}

<script>
// Data
const D = {json.dumps(D, ensure_ascii=False)};
const isDark = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim().startsWith('#0') || getComputedStyle(document.documentElement).getPropertyValue('--bg').trim().startsWith('#1');

// Mode switch
// 统一顶层视图切换: 汇报精简版 / 深度分析版 / 问题汇总 / 价格分析 / 历史趋势 / 年度任务
function switchView(view) {{
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-view') === view));
    var isReport = view === 'report';
    var isAnalysis = view === 'analysis';
    var isDashboard = isReport || isAnalysis;
    // 汇报/分析 都显示 page-dashboard; 其它视图显示对应 page
    document.getElementById('page-dashboard').style.display = isDashboard ? 'block' : 'none';
    document.getElementById('mode-report').style.display = isReport ? 'block' : 'none';
    document.getElementById('mode-analysis').style.display = isAnalysis ? 'block' : 'none';
    var nav = document.getElementById('mod-nav');
    if (nav) nav.style.display = isAnalysis ? 'flex' : 'none';
    if (isReport) {{
        switchPage('dashboard');
    }}
    if (isAnalysis) {{
        if(!window._analysisChartsInit) {{
            // 先展开全部分组, 保证图表初始化时容器有真实尺寸
            document.querySelectorAll('#mode-analysis [data-mod]').forEach(el => el.style.display = '');
            setTimeout(() => {{
                try {{ initAnalysisCharts(); }} catch(e) {{ console.warn('图表初始化失败(不影响表格内容):', e); }}
                window._analysisChartsInit = true;
                switchModGroup(window._modGroup || 'cockpit', null);
            }}, 50);
        }} else {{
            setTimeout(() => {{
                Chart.helpers.each(Chart.instances, c => c.resize());
            }}, 50);
        }}
    }}
    if(!isDashboard) {{
        switchPage(view);
    }}
}}

// 模块分组切换 (深度分析版): 一次只展开一组, 缩短单页长度
function switchModGroup(g, btn) {{
    window._modGroup = g;
    document.querySelectorAll('.mod-nav-btn').forEach(b => b.classList.remove('active'));
    var target = btn || document.querySelector('.mod-nav-btn[data-g="' + g + '"]');
    if (target) target.classList.add('active');
    document.querySelectorAll('#mode-analysis [data-mod]').forEach(el => {{
        el.style.display = (g === 'all' || el.getAttribute('data-mod') === g) ? '' : 'none';
    }});
    if (g !== 'all') window.scrollTo({{ top: 0, behavior: 'smooth' }});
    setTimeout(() => {{
        if (window.Chart && Chart.helpers) Chart.helpers.each(Chart.instances, c => c.resize());
    }}, 80);
}}

// 导航条吸顶位置 = header 实际高度 (header 本身 sticky; 切换视图后 header 高度可能变化, 用 ResizeObserver 跟踪)
(function() {{
    var h = document.querySelector('.header');
    var n = document.getElementById('mod-nav');
    if (!h || !n) return;
    function fitModNav() {{
        var sticky = getComputedStyle(h).position === 'sticky';
        n.style.top = sticky ? h.offsetHeight + 'px' : '0px';
    }}
    fitModNav();
    window.addEventListener('resize', fitModNav);
    window.addEventListener('load', fitModNav);
    if (window.ResizeObserver) new ResizeObserver(fitModNav).observe(h);
}})();

// Page switch (内部 helper, 由 switchView 调用): 只负责各 page 的显隐 + 各页懒初始化
function switchPage(page) {{
    document.getElementById('page-dashboard').style.display = page==='dashboard'?'block':'none';
    document.getElementById('page-issues').style.display = page==='issues'?'block':'none';
    {'''document.getElementById('page-prices').style.display = page==='prices'?'block':'none';''' if D.get('price_analysis') else ''}
    {'''document.getElementById('page-history').style.display = page==='history'?'block':'none';''' if H else ''}
    {'''document.getElementById('page-kpi').style.display = page==='kpi'?'block':'none';''' if K else ''}
    if(page==='dashboard') {{
        window._analysisChartsInit = false;
    }}
    {'''if(page==='history' && !window._historyChartsInit) {{
        setTimeout(() => {{ initHistoryCharts(); window._historyChartsInit = true; }}, 50);
    }}''' if H else ''}
    {'''if(page==='kpi' && !window._kpiChartsInit) {{
        setTimeout(() => {{ try {{ initKpiCharts(); }} catch(e) {{ console.warn("KPI图表初始化失败:", e); }} window._kpiChartsInit = true; }}, 50);
    }}''' if K else ''}
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
        html += '<tr id="'+rowId+'" onclick="toggleCostDetail(\\''+rowId+'\\','+i+')" style="cursor:pointer;transition:background .2s" onmouseover="this.style.background=\\'var(--surface2)\\'" onmouseout="this.style.background=\\'\\'">';
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
    let detailHtml = '<tr id="'+detailId+'" style="background:var(--surface2)"><td colspan="11" style="padding:12px 20px">';
    detailHtml += '<div style="font-weight:700;margin-bottom:8px;color:#3b82f6">📦 '+r.model+' 批次进货明细</div>';
    detailHtml += '<table style="width:100%;border-collapse:collapse;font-size:12px">';
    detailHtml += '<thead><tr style="border-bottom:1px solid var(--border);color:var(--text2)">';
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
        detailHtml += '<tr style="border-bottom:1px solid var(--border)">';
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
    detailHtml += '<div style="margin-top:10px;padding:10px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px">';
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
        options:{{responsive:true,layout:{{padding:{{top:18}}}},plugins:{{legend:{{position:'bottom'}},datalabels:makeLineDl()}}}}
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
        options:{{responsive:true,layout:{{padding:{{top:20}}}},plugins:{{legend:{{display:false}},datalabels:makeBarDl()}}}}
    }});

    // M3 brand qty
    new Chart(document.getElementById('chart_brand_qty'), {{
        type:'bar',
        data:{brand_qty_data_js},
        options:{{responsive:true,layout:{{padding:{{top:20}}}},plugins:{{legend:{{position:'bottom'}},datalabels:makeBarDl()}}}}
    }});

    // M3 brand revenue + profit
    new Chart(document.getElementById('chart_brand_rev'), {{
        type:'bar',
        data:{brand_rev_data_js}
        options:{{responsive:true,layout:{{padding:{{top:20}}}},plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12}}}},datalabels:makeBarDl()}}}}
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
        options:{{responsive:true,layout:{{padding:{{top:18}}}},plugins:{{legend:{{position:'bottom'}},datalabels:makeLineDl()}}}}
    }});

    // M5 revenue
    new Chart(document.getElementById('chart_m5_rev'), {{
        type:'bar',
        data:{{labels:{m5_labels},datasets:[{{label:'营收(百万₦)',data:{m5_rev},backgroundColor:'#22c55e44',borderColor:'#22c55e',borderWidth:1}}]}},
        options:{{responsive:true,layout:{{padding:{{top:20}}}},plugins:{{legend:{{display:false}},datalabels:makeBarDl()}}}}
    }});
}}

// Init report charts on load
window.addEventListener('DOMContentLoaded', () => {{
    initReportCharts();
}});

{dm_js}

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
        const na = parseFloat(va.replace(/[^0-9.\\-]/g, ''));
        const nb = parseFloat(vb.replace(/[^0-9.\\-]/g, ''));
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
        div.style.cssText = 'padding:7px 12px;cursor:pointer;color:var(--text);font-size:12px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between';
        div.innerHTML = '<span>'+t.model+'</span><span style="color:var(--text2);font-size:10px">月销'+t.total_june+'台</span>';
        div.onmouseenter = function() {{ this.style.background = 'var(--surface2)'; }};
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
{kpi_js}
</script>
{TABLE_TOTALS_JS}
</body>
</html>"""

if args.theme == 'light':
    html = apply_light_theme(html)

with open(args.out, 'w', encoding='utf-8') as f:
    f.write(html)

import os
size = os.path.getsize(args.out)
print(f"Dashboard generated: {size/1024:.0f}KB")