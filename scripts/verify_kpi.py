#!/usr/bin/env python3
"""
verify_kpi.py — 年度 KPI 数据自检
独立重算原始 Excel 关键值, 与 kpi_annual.json 比对(不 import build_kpi, 独立实现).
用法: python scripts/verify_kpi.py --json kpi_annual.json --months-dir <月度目录> --current <当月文件>
"""

import pandas as pd
import re
import json
import os
import glob
import argparse

CLOSED = {'D_IGANDO-IKOTUN ROAD-LAGOS', 'D_MSL MUSHIN2-ISOLO ROAD-LAGOS'}
TRANSSION = {'TECNO', 'INFINIX', 'ITEL'}

_results = []


def check(name, got, expect, tol=0.0):
    ok = abs(float(got) - float(expect)) <= tol
    _results.append((name, ok, got, expect))
    print(f"  [{'OK' if ok else 'FAIL'}] {name}: 重算={got:,.4f} vs JSON={expect:,.4f}" + (f" (tol={tol})" if tol else ""))
    return ok


def load(fpath):
    df = pd.read_excel(fpath)
    df.columns = [re.sub(r'\s+', '', str(c)) for c in df.columns]
    df = df[~df['销售部门'].isin(CLOSED)]
    df['品牌'] = df['品牌'].astype(str).str.strip().str.upper()
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='kpi_annual.json')
    ap.add_argument('--months-dir', default='/Users/wanghao/Desktop/销售部/销售数据/月度数据')
    ap.add_argument('--current', default=None)
    ap.add_argument('--check-month', default='2026-08', help='独立重算哪个整月(默认8月)')
    args = ap.parse_args()

    K = json.load(open(args.json))
    ym = args.check_month
    mi = int(ym.split('-')[1])
    fpath = os.path.join(args.months_dir, f'{ym.split("-")[0]}-{mi}.xlsx')
    print(f"独立重算 {ym}: {fpath}\n")
    df = load(fpath)

    # ① 传音智能机台量(智能机+平板, 与 build_kpi.py INCLUDE_TABLET_IN_SMART=True 一致)
    SMART = ['智能机', '平板电脑']
    got = df[df['统计分类'].isin(SMART) & df['品牌'].isin(TRANSSION)]['销售数量'].sum()
    check(f'{ym} 传音智能机台量', got, K['module1_annual']['actual']['qty_monthly'][ym], tol=0.5)

    # ① 手机零售额(NGN, 手机三分类全品牌)
    got = df[df['统计分类'].isin(['智能机', '平板电脑', '功能机'])]['零售金额'].sum()
    check(f'{ym} 手机零售额NGN', got, K['module1_annual']['actual']['rev_ngn_monthly'][ym], tol=1)

    # ③ 服务类-运营商营收(TELECOMMUNICATION 双字段)
    svc = df[df['统计分类'] == '服务']
    cu = svc['商品分类'].astype(str) + ' ' + svc['商品名称'].astype(str)
    got = svc[cu.str.upper().str.contains('TELECOMMUNICATION')]['零售金额'].sum()
    m3row = [m for m in K['module3_value_added']['monthly'] if m['month'] == ym][0]
    check(f'{ym} 增值业务-运营商营收', got, m3row['operator'], tol=1)

    # ④ 配件配比率(智能机口径含平板)
    acc = df[df['统计分类'] == '手机配件']['销售数量'].sum()
    smt = df[df['统计分类'].isin(SMART)]['销售数量'].sum()
    got = acc / smt if smt else 0
    m4row = [m for m in K['module4_accessory']['monthly'] if m['month'] == ym][0]
    check(f'{ym} 配件配比率', got, m4row['ratio'], tol=0.0005)

    # 当月部分月(如有): 传音智能机台量
    if args.current and os.path.exists(args.current) and K['meta'].get('partial_month'):
        cdf = load(args.current)
        pym = K['meta']['partial_month']
        got = cdf[cdf['统计分类'].isin(SMART) & cdf['品牌'].isin(TRANSSION)]['销售数量'].sum()
        check(f'{pym}(部分月) 传音智能机台量', got, K['module1_annual']['actual']['qty_monthly'][pym], tol=0.5)

    n_fail = sum(1 for _, ok, _, _ in _results if not ok)
    print(f"\n===== 自检结果: {len(_results) - n_fail}/{len(_results)} 通过 =====")
    raise SystemExit(1 if n_fail else 0)


if __name__ == '__main__':
    main()
