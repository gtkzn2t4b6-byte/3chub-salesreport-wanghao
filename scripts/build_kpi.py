#!/usr/bin/env python3
"""
build_kpi.py — 年度 KPI 四模块数据聚合
  模块① 年度任务完成情况（传音智能机台量 + 手机零售额 RMB，目标=各部门任务拆解表）
  模块② 月度单店模型（非手机内占比>=15% 且 非手机毛利率>=20% 的门店数）
  模块③ 增值业务收入（统计分类=服务，细分 运营商/外租/售后/分期/其他）
  模块④ 配件配比率（手机配件数量 / 智能机数量, 目标>=60%）

输入: 桌面月度明细(2026-*.xlsx) + 当月期间文件(--current) + 任务拆解表(--targets) + 可选逐月汇率(--rates)
输出: kpi_annual.json

口径说明(与用户 2026-09-17 确认):
  - 年度目标 = 任务拆解表(王浩-传音智能手机台量 280,000 / 王浩-手机零售销售额RMB 346,760,000)
  - 增值业务 = 统计分类「服务」全部营收; 来源按 商品分类/商品名称 关键词分桶
  - 单店模型月目标 = 当月活跃门店数 × KPI_STORE_MODEL_RATIO(暂定 0.30, 可调)
  - 配件配比率 = 手机配件数量 ÷ 智能机数量(不含平板), >=60% 达标
  - 数量/营收/毛利均为净求和(含退货负值行), 与 process_data.py 一致
"""

import pandas as pd
import numpy as np
import json
import os
import re
import glob
import argparse
import math
from datetime import datetime, date
from pathlib import Path

# ============ 口径常量(集中可调) ============
TRANSSION_BRANDS = ['TECNO', 'INFINIX', 'ITEL']      # 传音三品牌
INCLUDE_TABLET_IN_SMART = True                        # 平板计入"智能机"口径(用户确认默认包含)
SMART_CATS = ['智能机'] + (['平板电脑'] if INCLUDE_TABLET_IN_SMART else [])
PHONE_CATS = {'智能机', '功能机', '平板电脑'}          # 手机类(非手机 = 全部 - PHONE_CATS, 含"不需要")
REVENUE_SCOPE = ['智能机', '平板电脑', '功能机']       # 模块①"手机零售销售额"口径(全品牌)
KPI_STORE_MODEL_RATIO = 0.30                          # 单店模型月目标占比(暂定, 可能调整)
NONPHONE_SHARE_TH = 0.15                              # 单店模型: 非手机内占比阈值
NONPHONE_MARGIN_TH = 0.20                             # 单店模型: 非手机毛利率阈值
ACCESSORY_RATIO_TARGET = 0.60                         # 配件配比率目标
NGN_CNY_RATE_FALLBACK = 1 / 205                       # 汇率兜底(2026-09-17 定, 1元≈205奈拉, 用户口径)
CLOSED_DEPTS = {'D_IGANDO-IKOTUN ROAD-LAGOS', 'D_MSL MUSHIN2-ISOLO ROAD-LAGOS'}  # 已关店剔除
YEAR = 2026

NEED_COLS = ['销售部门', '品牌', '统计分类', '销售数量', '零售金额', '毛利', '记账日期', '商品分类', '商品名称']

SOURCE_LABELS = {'operator': '运营商', 'rental': '租金'}   # 增值业务仅两来源(售后/分期无明细数据)


def normalize_spaces(df):
    df.columns = [re.sub(r'\s+', '', str(c)) for c in df.columns]
    return df


def clean_store_name(name):
    if not isinstance(name, str):
        return None
    name = name.strip().replace('\xa0', ' ')
    if name.startswith('D_'):
        name = name[2:]
    return name or None


def read_sales(fpath):
    """读销售明细, 只取需要的列, 基础清洗. 返回 df 或 None."""
    try:
        df = pd.read_excel(fpath)
    except Exception as e:
        print(f"  ❌ 读取失败 {fpath}: {e}")
        return None
    df = normalize_spaces(df)
    missing = [c for c in NEED_COLS if c not in df.columns]
    if missing:
        print(f"  ❌ {fpath} 缺列: {missing}")
        return None
    df = df[NEED_COLS].copy()
    df['品牌'] = df['品牌'].astype(str).str.strip().str.upper()
    df['store'] = df['销售部门'].apply(clean_store_name)
    df = df[~df['销售部门'].isin(CLOSED_DEPTS)]
    df = df[df['store'].notna()]
    df['记账日期'] = pd.to_datetime(df['记账日期'], errors='coerce')
    df['商品分类'] = df['商品分类'].astype(str)
    df['商品名称'] = df['商品名称'].astype(str)
    return df


def classify_service(cat, name):
    """服务类来源分桶(2026-09-17 修订口径):
    增值业务只算 = 运营商(电信) + 租金。排除: 订金(PREORDER)、软件下载(SOFTWARE)、配送费、分期等。
    注意: TELECOMMUNICATION- 前缀可能出现在商品分类或商品名称任一字段(各月不同), 双字段联合判断。
    返回 'exclude' 表示不计入增值业务(归入 excluded, 不显示在四来源里)。"""
    cu = f'{cat} {name}'.upper()
    if 'TELECOMMUNICATION' in cu:
        return 'operator'
    # 租金 = 摊位租金(MONTHLY RENTAL) + 下载服务(DOWNLOAD)
    if 'MONTHLY RENTAL' in cu or 'DOWNLOAD' in cu:
        return 'rental'
    # 其余(订金/配送费/分期等)一律不计入增值业务
    return 'exclude'


def load_targets(fpath):
    """解析任务拆解表: 返回 (qty_monthly[12], rev_rmb_monthly[12])"""
    t = pd.read_excel(fpath, engine='calamine', header=None)
    qty_m = rev_m = None
    for i in range(len(t) - 1):
        label = str(t.iloc[i, 0])
        if '王浩' in label and '传音智能手机' in label:
            qty_m = [float(t.iloc[i + 1, j]) for j in range(1, 13)]
        if '王浩' in label and '手机零售销售额' in label:
            rev_m = [float(t.iloc[i + 1, j]) for j in range(1, 13)]
    if qty_m is None or rev_m is None:
        raise SystemExit(f"❌ 拆解表中未找到王浩的目标行: {fpath}")
    return qty_m, rev_m


def load_rates(fpath):
    """可选逐月汇率 CSV: month,rate_ngn_cny"""
    rates = {}
    if fpath and os.path.exists(fpath):
        r = pd.read_csv(fpath)
        for _, row in r.iterrows():
            rates[str(row['month']).strip()] = float(row['rate_ngn_cny'])
    return rates


def half_up(x):
    return int(math.floor(x + 0.5))


def process_month(df, ym, acc):
    """单月聚合: 把结果累计进 acc(跨月共享字典). df 已清洗."""
    is_phone_cat = df['统计分类'].isin(PHONE_CATS)
    is_smart = df['统计分类'].isin(SMART_CATS)

    # ---- 模块① 传音智能机台量 + 手机零售额 ----
    trans = df[is_smart & df['品牌'].isin(TRANSSION_BRANDS)]
    acc['m1_qty'][ym] = float(trans['销售数量'].sum())
    acc['m1_rev_ngn'][ym] = float(df[df['统计分类'].isin(REVENUE_SCOPE)]['零售金额'].sum())
    for b in TRANSSION_BRANDS:
        acc['m1_brand_qty'][b][ym] = float(trans[trans['品牌'] == b]['销售数量'].sum())

    # ---- 模块② 单店模型(门店×非手机) ----
    df['_is_nonphone'] = ~is_phone_cat
    g = df.groupby('store').apply(lambda x: pd.Series({
        'total_rev': x['零售金额'].sum(),
        'nonphone_rev': x.loc[x['_is_nonphone'], '零售金额'].sum(),
        'nonphone_gp': x.loc[x['_is_nonphone'], '毛利'].sum(),
    }), include_groups=False)
    g['share'] = np.where(g['total_rev'] != 0, g['nonphone_rev'] / g['total_rev'], 0.0)
    g['margin'] = np.where(g['nonphone_rev'] != 0, g['nonphone_gp'] / g['nonphone_rev'], 0.0)
    g['qualified'] = (g['share'] >= NONPHONE_SHARE_TH) & (g['margin'] >= NONPHONE_MARGIN_TH)
    detail = []
    for store, r in g.sort_values('share', ascending=False).iterrows():
        detail.append({
            'store': store,
            'total_rev': round(float(r['total_rev']), 2),
            'nonphone_rev': round(float(r['nonphone_rev']), 2),
            'nonphone_share': round(float(r['share']), 4),
            'nonphone_margin': round(float(r['margin']), 4),
            'qualified': bool(r['qualified']),
        })
    n_active = len(g)
    n_qual = int(g['qualified'].sum())
    acc['m2_monthly'][ym] = {
        'active_stores': n_active,
        'target_stores': half_up(n_active * KPI_STORE_MODEL_RATIO),
        'qualified_stores': n_qual,
        'detail': detail,
    }
    df.drop(columns=['_is_nonphone'], inplace=True)

    # ---- 模块③ 增值业务(服务类分桶, 只算电信+租金) ----
    svc = df[df['统计分类'] == '服务']
    buckets = {k: 0.0 for k in SOURCE_LABELS}
    for cat, name, rev in zip(svc['商品分类'], svc['商品名称'], svc['零售金额']):
        b = classify_service(cat, name)
        if b == 'exclude':
            acc['m3_excluded'].add((cat, name))
        else:
            buckets[b] += float(rev)
    acc['m3_monthly'][ym] = {k: round(v, 2) for k, v in buckets.items()}

    # ---- 模块④ 配件配比率 ----
    acc_qty = float(df[df['统计分类'] == '手机配件']['销售数量'].sum())
    smt_qty = float(df[is_smart]['销售数量'].sum())
    ratio = (acc_qty / smt_qty) if smt_qty else 0.0
    acc['m4_monthly'][ym] = {
        'accessory_qty': acc_qty, 'smart_qty': smt_qty,
        'ratio': round(ratio, 4), 'qualified': bool(ratio >= ACCESSORY_RATIO_TARGET),
    }


def main():
    ap = argparse.ArgumentParser(description='年度 KPI 四模块数据聚合')
    ap.add_argument('--months-dir', default='/Users/wanghao/Desktop/销售部/销售数据/月度数据')
    ap.add_argument('--current', default=None, help='当月期间销售文件(部分月)')
    ap.add_argument('--targets', default='/Users/wanghao/Desktop/销售部/kpi/kpi2026/各部门任务拆解(1).xls')
    ap.add_argument('--rates', default=None, help='可选: 逐月汇率 CSV (month,rate_ngn_cny)')
    ap.add_argument('--out', default='kpi_annual.json')
    args = ap.parse_args()

    qty_t, rev_t = load_targets(args.targets)
    rates = load_rates(args.rates)
    rate_source = 'per_month' if rates else 'fixed_fallback'

    def rate_of(ym):
        return rates.get(ym, NGN_CNY_RATE_FALLBACK)

    # ---- 收集月度文件 ----
    files = []
    for f in sorted(glob.glob(os.path.join(args.months_dir, f'{YEAR}-*.xlsx'))):
        base = os.path.basename(f)
        if '副本' in base or base.startswith('~') or base.startswith('.'):
            continue
        m = re.match(rf'{YEAR}-(\d+)\.xlsx$', base)
        if m:
            files.append((f, f'{YEAR}-{int(m.group(1)):02d}'))

    acc = {
        'm1_qty': {}, 'm1_rev_ngn': {}, 'm1_brand_qty': {b: {} for b in TRANSSION_BRANDS},
        'm2_monthly': {}, 'm3_monthly': {}, 'm3_excluded': set(), 'm4_monthly': {},
    }
    current_ym = None
    cutoff = None

    for fpath, ym in files:
        df = read_sales(fpath)
        if df is None:
            continue
        print(f"处理 {ym}: {os.path.basename(fpath)} ({len(df)} 行)")
        process_month(df, ym, acc)
        cutoff = max(cutoff, df['记账日期'].max()) if cutoff is not None else df['记账日期'].max()
        del df

    if args.current and os.path.exists(args.current):
        df = read_sales(args.current)
        if df is not None:
            dmax = df['记账日期'].max()
            current_ym = f'{dmax.year}-{dmax.month:02d}'
            if current_ym not in acc['m1_qty']:
                print(f"处理当月 {current_ym}(部分月): {os.path.basename(args.current)} ({len(df)} 行)")
                process_month(df, current_ym, acc)
                cutoff = max(cutoff, dmax) if cutoff is not None else dmax
            del df

    months = sorted(acc['m1_qty'].keys())
    if not months:
        raise SystemExit('❌ 没有任何月度数据可处理')
    if cutoff is None:
        cutoff = pd.Timestamp(date(YEAR, 12, 31))
    cutoff_str = str(cutoff.date())

    # ---- 年度时间进度(自然日) ----
    day_of_year = cutoff.timetuple().tm_yday if hasattr(cutoff, 'timetuple') else cutoff.date().timetuple().tm_yday
    time_progress = round(day_of_year / (366 if YEAR % 4 == 0 else 365), 4)

    # ===== 模块① 组装 =====
    qty_ytd = sum(acc['m1_qty'].values())
    rev_ngn_ytd = sum(acc['m1_rev_ngn'].values())
    rev_rmb_monthly = {ym: round(acc['m1_rev_ngn'][ym] * rate_of(ym), 2) for ym in months}
    rev_rmb_ytd = sum(rev_rmb_monthly.values())
    qty_annual_target = sum(qty_t)
    rev_annual_target = sum(rev_t)
    m1 = {
        'target': {
            'qty_annual': qty_annual_target, 'rev_rmb_annual': rev_annual_target,
            'qty_monthly': qty_t, 'rev_rmb_monthly': rev_t,
        },
        'actual': {
            'qty_monthly': {ym: round(acc['m1_qty'][ym], 1) for ym in months},
            'qty_ytd': round(qty_ytd, 1),
            'rev_ngn_monthly': {ym: round(acc['m1_rev_ngn'][ym], 2) for ym in months},
            'rev_ngn_ytd': round(rev_ngn_ytd, 2),
            'rev_rmb_monthly': rev_rmb_monthly, 'rev_rmb_ytd': round(rev_rmb_ytd, 2),
        },
        'completion': {
            'qty_ytd_rate': round(qty_ytd / qty_annual_target, 4) if qty_annual_target else 0,
            'rev_rmb_ytd_rate': round(rev_rmb_ytd / rev_annual_target, 4) if rev_annual_target else 0,
            'time_progress': time_progress,
            'qty_progress_diff_pp': round(qty_ytd / qty_annual_target * 100 - time_progress * 100, 1),
            'rev_progress_diff_pp': round(rev_rmb_ytd / rev_annual_target * 100 - time_progress * 100, 1),
        },
    }

    # 分品牌: 传音月度任务三品牌均分(月均口径, 用户 2026-09-17 确认)
    brand_ytd = {b: sum(acc['m1_brand_qty'][b].values()) for b in TRANSSION_BRANDS}
    brand_total = sum(brand_ytd.values()) or 1
    n_brand = len(TRANSSION_BRANDS)
    rows = []
    for b in TRANSSION_BRANDS:
        share = 1.0 / n_brand
        monthly = []
        for mi in range(1, 13):
            ym = f'{YEAR}-{mi:02d}'
            tgt = qty_t[mi - 1] / n_brand
            act = acc['m1_brand_qty'][b].get(ym, 0.0)
            monthly.append({
                'month': mi, 'target': round(tgt, 1), 'actual': round(act, 1),
                'rate': round(act / tgt, 4) if tgt else None,
            })
        alloc_ytd = qty_annual_target / n_brand
        rows.append({
            'brand': b, 'ytd_qty': round(brand_ytd[b], 1), 'ytd_share': round(brand_ytd[b] / brand_total, 4),
            'alloc_target_ytd': round(alloc_ytd, 1),
            'alloc_completion_rate': round(brand_ytd[b] / alloc_ytd, 4) if alloc_ytd else 0,
            'monthly': monthly,
        })
    m1['brand'] = {'alloc_note': '分品牌任务 = 传音月度任务 ÷ 3 均分(月均口径)', 'rows': rows}

    # ===== 模块② 组装 =====
    m2_monthly = []
    for ym in months:
        d = acc['m2_monthly'][ym]
        m2_monthly.append({
            'month': ym, 'active_stores': d['active_stores'],
            'target_stores': d['target_stores'], 'qualified_stores': d['qualified_stores'],
            'qualified_rate': round(d['qualified_stores'] / d['target_stores'], 4) if d['target_stores'] else 0,
            'is_partial': ym == current_ym,
        })
    last_ym = months[-1]
    m2 = {
        'ratio': KPI_STORE_MODEL_RATIO, 'share_th': NONPHONE_SHARE_TH, 'margin_th': NONPHONE_MARGIN_TH,
        'monthly': m2_monthly,
        'latest': m2_monthly[-1],
        'latest_detail': acc['m2_monthly'][last_ym]['detail'],
    }

    # ===== 模块③ 组装 =====
    m3_monthly = []
    cum = {k: 0.0 for k in SOURCE_LABELS}
    for ym in months:
        b = acc['m3_monthly'][ym]
        for k in cum:
            cum[k] += b[k]
        m3_monthly.append({'month': ym, **b, 'total': round(sum(b.values()), 2)})
    total_ngn = sum(cum.values())
    m3 = {
        'source_labels': SOURCE_LABELS,
        'cumulative': {
            'by_source': {k: round(v, 2) for k, v in cum.items()},
            'total_ngn': round(total_ngn, 2),
            'total_rmb': round(total_ngn * rate_of(months[-1]), 2),
        },
        'monthly': m3_monthly,
        'excluded_service_cats': sorted([f'{c} | {n}' for c, n in acc['m3_excluded']]),
    }

    # ===== 模块④ 组装 =====
    m4_monthly = [{'month': ym, **acc['m4_monthly'][ym]} for ym in months]
    m4 = {
        'target': ACCESSORY_RATIO_TARGET,
        'current': m4_monthly[-1] if m4_monthly else None,
        'monthly': m4_monthly,
    }

    output = {
        'meta': {
            'data_cutoff': cutoff_str,
            'partial_month': current_ym,
            'months_available': months,
            'rate_default': round(NGN_CNY_RATE_FALLBACK, 6),
            'rate_source': rate_source,
            'rate_note': '全年按固定 1 元≈205 奈拉(用户口径)' if not rates else '使用逐月汇率',
            'brand_alloc_source': 'missing',
            'revenue_scope': REVENUE_SCOPE,
            'include_tablet_in_smart': INCLUDE_TABLET_IN_SMART,
            'store_model_ratio': KPI_STORE_MODEL_RATIO,
            'nonphone_share_th': NONPHONE_SHARE_TH,
            'nonphone_margin_th': NONPHONE_MARGIN_TH,
            'accessory_ratio_target': ACCESSORY_RATIO_TARGET,
            'closed_depts_excluded': sorted(CLOSED_DEPTS),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
        'module1_annual': m1,
        'module2_store_model': m2,
        'module3_value_added': m3,
        'module4_accessory': m4,
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    # ---- 摘要 ----
    print(f"\n===== KPI 年度数据已生成: {args.out} =====")
    print(f"数据截止: {cutoff_str} | 月份: {', '.join(months)} | 时间进度 {time_progress*100:.1f}%")
    print(f"[①年度任务] 传音智能机 YTD {qty_ytd:,.0f}/{qty_annual_target:,.0f} = {m1['completion']['qty_ytd_rate']*100:.1f}%"
          f" (进度差 {m1['completion']['qty_progress_diff_pp']:+.1f}pp)")
    print(f"            手机零售额 YTD ₦{rev_ngn_ytd/1e6:,.0f}M ≈ ¥{rev_rmb_ytd/1e4:,.0f}万"
          f"/¥{rev_annual_target/1e6:,.0f}M = {m1['completion']['rev_rmb_ytd_rate']*100:.1f}%"
          f" (进度差 {m1['completion']['rev_progress_diff_pp']:+.1f}pp)")
    for r in rows:
        print(f"            {r['brand']:<8} YTD {r['ytd_qty']:,.0f} (占 {r['ytd_share']*100:.1f}%, 分摊完成率 {r['alloc_completion_rate']*100:.1f}%)")
    lm2 = m2['latest']
    print(f"[②单店模型] {lm2['month']}: 达标 {lm2['qualified_stores']}/{lm2['target_stores']} 家(活跃 {lm2['active_stores']}×{KPI_STORE_MODEL_RATIO:.0%}), 达成率 {lm2['qualified_rate']*100:.0f}%")
    print(f"[③增值业务] 累计 ₦{total_ngn/1e6:,.1f}M ≈ ¥{m3['cumulative']['total_rmb']/1e4:,.1f}万 | 来源: " +
          ' '.join(f"{SOURCE_LABELS[k]} {cum[k]/1e4:,.1f}万" for k in SOURCE_LABELS))
    if m3['excluded_service_cats']:
        print(f"            ⚠ 已排除服务类 {len(m3['excluded_service_cats'])} 项(订金/软件下载/配送费等, 不计入增值业务): ")
        for u in m3['excluded_service_cats'][:15]:
            print(f"               - {u}")
    if m4['current']:
        c = m4['current']
        print(f"[④配件配比] {c['month']}: {c['accessory_qty']:,.0f}/{c['smart_qty']:,.0f} = {c['ratio']*100:.1f}% (目标 ≥{ACCESSORY_RATIO_TARGET:.0%}, {'达标' if c['qualified'] else '未达标'})")


if __name__ == '__main__':
    main()
