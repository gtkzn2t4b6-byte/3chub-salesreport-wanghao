#!/usr/bin/env python3
"""给已有的月度存档看板 HTML 注入「历史趋势」增强模块：

1. 🔁 品牌同比 / 环比分析（新板块 + 月份下拉 + 明细表 + 分析文字）
2. 📊 营收毛利 & 品牌贡献：月份筛选 + 数据分析 + 环形图联动

数据按存档月份裁剪（如 6 月存档只用到 2026-06 的历史数据），避免出现"未来月份"。

用法:
    python scripts/patch_archive_history.py "月度看板存档/*.html"

注入的 JS/HTML 逻辑与 generate_dashboard.py 保持一致；若生成器改了逻辑，需同步本文件。
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------- HTML 片段 ----------
CSS_BLOCK = """
.hist-analysis { background:var(--surface2); border-radius:8px; padding:10px 14px; font-size:12px; color:var(--text); }
.hist-analysis .ai { padding:2px 0; }
"""

BRAND_YOY_SECTION = """
<!-- Brand YoY / MoM Analysis (injected) -->
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

"""

JS_BLOCK = """
// ===== [injected] Brand YoY/MoM & Month Filter =====
var _chartRevProfit = null, _chartBrandContrib = null;
var HIST = __HIST_DATA__;
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
        var revY = HIST.rev[py];
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
// ===== [injected] end =====
"""


def build_hist_data(cutoff_month):
    """按截止月份裁剪历史数据（cutoff_month 形如 '2026-06'），返回可直接注入 JS 的 dict。"""
    hist = json.load(open(os.path.join(ROOT, 'historical_data.json'), encoding='utf-8'))
    data, hsum, brand = hist['data'], hist['summaries'], hist['brand_data']

    rev_monthly, profit_monthly = {}, {}
    for store, months in data.get('revenue', {}).items():
        for m, v in months.items():
            if v is not None:
                rev_monthly[m] = rev_monthly.get(m, 0) + v
    for store, months in data.get('gross_profit', {}).items():
        for m, v in months.items():
            if v is not None:
                profit_monthly[m] = profit_monthly.get(m, 0) + v

    mt = hsum['monthly_total_phone_sales']
    months = [m for m in sorted(mt.keys()) if m <= cutoff_month]

    # 品牌：2025 全年保留；2026 仅保留到截止月
    def trim(year_data, keep_all=False):
        out = {}
        for b, md in year_data.items():
            out[b] = {m: v for m, v in md.items() if keep_all or m <= cutoff_month}
        return out

    brand_trim = {
        '2025': trim(brand.get('2025', {}), keep_all=True),
        '2026': trim(brand.get('2026', {}))
    }
    return {
        'months': months,
        'brand': brand_trim,
        'rev': {m: rev_monthly.get(m, 0) for m in months},
        'profit': {m: profit_monthly.get(m, 0) for m in months},
        'sales': {m: (mt.get(m, 0) or 0) for m in months}
    }


def patch_file(path, backup_dir):
    html = open(path, encoding='utf-8').read()
    # 已注入过的文件只做"自愈"：补齐缺失的 _initHistFilters() 调用
    repair_only = 'updateBrandYoY' in html and html.count('_initHistFilters();') < 2

    m = re.search(r'2026年(\d+)月', os.path.basename(path))
    if not m:
        print(f'[SKIP] 文件名无法识别月份: {path}')
        return False
    cutoff = '2026-%02d' % int(m.group(1))
    hist_js = json.dumps(build_hist_data(cutoff), ensure_ascii=False)

    steps = []

    # 1. CSS
    if repair_only:
        # 仅补齐 initHistoryCharts 末尾的 _initHistFilters() 调用
        # 注：注入块插在 switchBrandView 之前，故锚点改为「注入块之前的函数结尾」
        patterns = [
            r"\n(\s*)\}\);\n\}\n\n\n// ===== \[injected\] Brand YoY",
            r"\n(\s*)\}\);\n\}\n\nfunction switchBrandView\(name, btn\) \{",
        ]
        tails = {
            patterns[0]: '// ===== [injected] Brand YoY',
            patterns[1]: 'function switchBrandView(name, btn) {',
        }
        for pat in patterns:
            tail = tails[pat]
            html, n = re.subn(pat,
                              lambda mo: f"\n{mo.group(1)}}});\n{mo.group(1)}_initHistFilters();\n}}\n\n{tail}",
                              html, count=1)
            if n:
                break
        if not n:
            print(f'[FAIL] 修复失败，未找到锚点: {path}')
            return False
        steps.append('init-call(repair)')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[OK-REPAIR] {path} | {",".join(steps)}')
        return True

    if '.hist-analysis' not in html:
        assert html.count('</style>') >= 1, 'no </style>'
        html = html.replace('</style>', CSS_BLOCK + '</style>', 1)
        steps.append('css')

    # 2. 新增品牌同比/环比板块（插在 Chart 3 之前）
    marker = '<!-- Chart 3: YoY Growth + Revenue/Profit -->'
    if marker in html:
        html = html.replace(marker, BRAND_YOY_SECTION + marker, 1)
        steps.append('brand-section')

    # 3. 营收毛利板块：加月份筛选 + 分析框 + 动态标题
    pat_head = re.compile(r'<div class="section-header"[^>]*><div class="section-title"[^>]*>📊 营收毛利 & 品牌贡献</div></div>\s*<div class="section-body"[^>]*>')
    new_head = ('<div class="section-header"><div class="section-title">📊 营收毛利 & 品牌贡献</div>'
                '<select id="sel_rev_month" onchange="updateRevFilter(this.value)" style="margin-left:auto;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);font-size:12px;font-family:var(--font)"></select></div>'
                '<div class="section-body"><div id="rev_profit_analysis" class="hist-analysis" style="margin-bottom:12px"></div>')
    html, n = pat_head.subn(new_head, html, count=1)
    if n:
        steps.append('rev-header')

    # 4. 环形图标题动态化
    html, n = re.subn(r'品牌2026累计贡献 TOP8',
                      '品牌贡献 TOP8 <span id="brand_contrib_scope" style="font-weight:400">（2026累计）</span>',
                      html, count=1)
    if n:
        steps.append('contrib-title')

    # 5. JS: 保留图表实例引用
    html, n1 = re.subn(r"new Chart\(document\.getElementById\('chart_history_brand_contrib'\)",
                       "_chartBrandContrib = new Chart(document.getElementById('chart_history_brand_contrib')", html, count=1)
    html, n2 = re.subn(r"new Chart\(document\.getElementById\('chart_history_rev_profit'\)",
                       "_chartRevProfit = new Chart(document.getElementById('chart_history_rev_profit')", html, count=1)
    if n1 and n2:
        steps.append('chart-refs')

    # 6. JS: initHistoryCharts 末尾调用 _initHistFilters()
    html, n = re.subn(r"\n(\s*)\}\);\n\}\n\nfunction switchBrandView\(name, btn\) \{",
                      lambda mo: f"\n{mo.group(1)}}});\n{mo.group(1)}_initHistFilters();\n}}\n\nfunction switchBrandView(name, btn) {{",
                      html, count=1)
    if n:
        steps.append('init-call')
    else:
        print(f'[WARN] 未找到 initHistoryCharts 结尾锚点，改为在 switchBrandView 前兜底插入: {path}')

    # 7. 注入 JS 逻辑（放在 switchBrandView 函数之后）
    anchor = 'function switchBrandView(name, btn) {'
    if anchor in html:
        html = html.replace(anchor, JS_BLOCK.replace('__HIST_DATA__', hist_js) + '\n' + anchor, 1)
        steps.append('js-block')

    if len(steps) < 5:
        print(f'[FAIL] 步骤不完整 {steps}: {path}')
        return False

    shutil.copy2(path, os.path.join(backup_dir, os.path.basename(path)))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[OK] {path} | 截止{cutoff} | 步骤: {",".join(steps)} | {len(html)/1024:.0f}KB')
    return True


def main():
    ap = argparse.ArgumentParser(description='Inject history-trend enhancements into archived dashboards')
    ap.add_argument('files', nargs='+', help='HTML 文件（支持 glob）')
    ap.add_argument('--backup-dir', default=os.path.join(ROOT, '.workbuddy', 'backups'))
    args = ap.parse_args()

    os.makedirs(args.backup_dir, exist_ok=True)
    paths = []
    for pat in args.files:
        paths.extend(sorted(glob.glob(pat)))
    ok = sum(1 for p in paths if patch_file(p, args.backup_dir))
    print(f'\n完成 {ok}/{len(paths)} 个文件')


if __name__ == '__main__':
    main()
