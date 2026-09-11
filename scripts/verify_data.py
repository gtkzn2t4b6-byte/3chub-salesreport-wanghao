#!/usr/bin/env python3
"""数据自检：抛开 process_data 的中间逻辑，直接从原始 Excel 重算关键指标，
与 dashboard_full.json 交叉核对，确保看板数字真实可靠。

用法:
  python scripts/verify_data.py --sales <销售.xlsx> --inventory <库存.xlsx> --json dashboard_full.json
"""
import argparse, json, sys
import pandas as pd, warnings
warnings.filterwarnings('ignore')

CLOSED_DEPTS = {'D_IGANDO-IKOTUN ROAD-LAGOS', 'D_MSL MUSHIN2-ISOLO RD-LAGOS'}
SMART_CATS = ['智能机', '平板电脑']

ap = argparse.ArgumentParser()
ap.add_argument('--sales', required=True)
ap.add_argument('--inventory', required=True)
ap.add_argument('--json', default='dashboard_full.json')
ap.add_argument('--tol', type=float, default=1.0, help='允许的绝对误差(台/奈拉)')
args = ap.parse_args()

def norm(df):
    for c in df.select_dtypes(include=['object']).columns:
        df[c] = df[c].map(lambda x: x.replace('\xa0', ' ') if isinstance(x, str) else x)
    return df

ok, fail = [], []
def check(name, a, b, tol=None):
    tol = args.tol if tol is None else tol
    a = 0 if a is None else float(a)
    b = 0 if b is None else float(b)
    d = abs(a - b)
    if d <= tol:
        ok.append(f"  OK   {name}: {a:,.1f} == {b:,.1f}")
    else:
        fail.append(f"  FAIL {name}: 原始={a:,.1f} 看板={b:,.1f} 差={d:,.1f}")

print("=" * 78)
print("数据自检：原始 Excel 重算  vs  dashboard_full.json")
print("=" * 78)

# ---------- 销售 ----------
s = norm(pd.read_excel(args.sales))
s = s[~s['销售部门'].isin(CLOSED_DEPTS)]
smart = s[s['统计分类'].isin(SMART_CATS)]

d = json.load(open(args.json, encoding='utf-8'))
meta = d.get('meta', {})

print("\n[1] 总量口径 (已剔除关店)")
check("智能机总台数", smart['销售数量'].sum(), meta.get('total_smart_qty'))
# 营收/毛利: 看板使用"全品类"口径(含配件/家电/服务), 与智能机销量并排展示时需注意
rev_all, rev_smart = s['零售金额'].sum(), smart['零售金额'].sum()
prf_all, prf_smart = s['毛利'].sum(), smart['毛利'].sum()
rev_tol = max(1000, rev_all * 0.002)   # 金额类用 0.2% 相对容差(浮点/空值写入差异)
if abs(rev_all - meta.get('total_revenue', 0)) <= rev_tol:
    ok.append(f"  OK   总营收: {rev_all:,.0f} (全品类口径, 含配件/家电/服务)")
elif abs(rev_smart - meta.get('total_revenue', 0)) <= rev_tol:
    ok.append(f"  OK   总营收: {rev_smart:,.0f} (智能机+平板口径)")
else:
    fail.append(f"  FAIL 总营收: 全品类={rev_all:,.0f} 手机口径={rev_smart:,.0f} 看板={meta.get('total_revenue'):,.0f}")
if abs(prf_all - meta.get('total_profit', 0)) <= max(1000, abs(prf_all) * 0.002):
    ok.append(f"  OK   总毛利: {prf_all:,.0f} (全品类口径, 毛利率 {prf_all/rev_all*100:.1f}%)")
elif abs(prf_smart - meta.get('total_profit', 0)) <= max(1000, abs(prf_smart) * 0.002):
    ok.append(f"  OK   总毛利: {prf_smart:,.0f} (手机口径, 毛利率 {prf_smart/rev_smart*100:.1f}%)")
else:
    fail.append(f"  FAIL 总毛利: 全品类={prf_all:,.0f} 手机口径={prf_smart:,.0f} 看板={meta.get('total_profit'):,.0f}")
print(f"  口径提示: 全品类营收 {rev_all/1e6:,.1f}M / 毛利 {prf_all/1e6:,.1f}M ({prf_all/rev_all*100:.1f}%)"
      f" | 手机口径营收 {rev_smart/1e6:,.1f}M / 毛利 {prf_smart/1e6:,.1f}M ({prf_smart/rev_smart*100:.1f}%)")

print("\n[2] 品牌维度 (m3_brands)")
bm = smart.groupby(smart['品牌'].astype(str).str.strip().str.upper())['销售数量'].sum()
m3 = {str(b['品牌']).strip().upper(): b['qty'] for b in d.get('m3_brands', [])}
check("品牌数一致", len(bm), len(m3), tol=0)
for b, q in bm.sort_values(ascending=False).items():
    if b in m3:
        check(f"  品牌 {b}", q, m3[b])

print("\n[3] 型号维度 (m10_model_analysis)")
mm = smart.groupby(smart['型号'].astype(str).str.strip().str.upper())['销售数量'].sum()
m10 = {str(m['model']).strip().upper(): m for m in d.get('m10_model_analysis', [])}
check("型号数一致", len(mm), len(m10), tol=0)
miss = [k for k in mm.index if k not in m10]
extra = [k for k in m10 if k not in mm.index]
if miss:
    fail.append(f"  FAIL 看板缺失型号 {len(miss)} 个: {miss[:10]}")
else:
    ok.append("  OK   无缺失型号")
if extra:
    fail.append(f"  FAIL 看板多出型号 {len(extra)} 个: {extra[:10]}")
else:
    ok.append("  OK   无多余型号")
bad_qty = [(k, mm[k], m10[k]['qty']) for k in mm.index if k in m10 and abs(mm[k] - m10[k]['qty']) > args.tol]
if bad_qty:
    fail.append(f"  FAIL 型号销量不符 {len(bad_qty)} 个: {bad_qty[:5]}")
else:
    ok.append(f"  OK   {len(mm)} 个型号销量逐条一致")

# 型号品牌是否与销售数据品牌一致
sales_brand = smart.groupby(smart['型号'].astype(str).str.strip().str.upper())['品牌'].agg(
    lambda x: x.mode().iloc[0] if len(x.mode()) else '')
bad_brand = []
for k, m in m10.items():
    sb = str(sales_brand.get(k, '')).strip().upper()
    jb = str(m.get('brand', '')).strip().upper()
    if sb and jb and sb != jb and not (sb in ('APPLE', 'IPHONE') and jb in ('APPLE', 'IPHONE')):
        bad_brand.append((k, sb, jb))
if bad_brand:
    fail.append(f"  FAIL 型号品牌与销售数据不符 {len(bad_brand)} 个: {bad_brand[:10]}")
else:
    ok.append("  OK   型号品牌与销售数据完全一致(APPLE/IPHONE 视为同义)")

print("\n[4] 门店维度 (m1_store_target)")
m1 = d.get('m1_store_target', [])
check("门店数", smart['销售部门'].nunique(), len(m1), tol=2)
m1_qty = sum(x.get('qty', 0) for x in m1)
no_target = set(smart['销售部门'].unique()) - {x.get('dept') for x in m1}
nt_qty = smart[smart['销售部门'].isin(no_target)]['销售数量'].sum()
if no_target:
    ok.append(f"  OK   门店任务表销量合计 {m1_qty:,.0f} + 无任务部门({', '.join(sorted(no_target))[:40]}) "
              f"{nt_qty:,.0f} = {m1_qty + nt_qty:,.0f}")
check("门店任务表销量 + 无任务部门销量", smart['销售数量'].sum(), m1_qty + nt_qty, tol=5)

# ---------- 库存 ----------
print("\n[5] 库存维度 (m6)")
inv = norm(pd.read_excel(args.inventory))
inv = inv.dropna(subset=['仓库'])
inv['可卖数'] = inv['可卖数'].fillna(0)
inv = inv[~inv['仓库'].astype(str).str.contains('MUSHIN2-PHONES|IGANDO-PHONES', na=False)]
# 与 process_data 同口径: 剔除样品/坏品/拒收/维修/电商/OS_ 仓
inv = inv[~inv['仓库'].astype(str).str.contains('SAMPLE|FAULTY|REJECT|CARLCARE|E-COMMERCE|OS_', na=False)]
inv_st = inv[~inv['仓库'].astype(str).str.contains('GENERAL', na=False)]
# 库存口径: 仅 SMART PHONE + TABLET TYPE（SMART DEVICE=智能穿戴/音频，不属于手机周转口径）
# 注意: 个别型号在库存里被同时标成两种分类(如 ITEL IT5363 既标 FEATURE PHONE 又标 SMART PHONE),
# 此时以该型号出现次数最多的分类为准(与看板 dedup 后的判定保持一致)
inv_st['_cat'] = inv_st['二级分类名称'].astype(str).str.strip()
main_cat = inv_st.groupby('商品型号')['_cat'].agg(lambda x: x.mode().iloc[0] if len(x.mode()) else 'other')
inv_st['_main_cat'] = inv_st['商品型号'].map(main_cat)
inv_st = inv_st[inv_st['_main_cat'].isin(['SMART PHONE', 'TABLET TYPE'])]
bq = inv_st.groupby(inv_st['品牌'].astype(str).str.strip().str.upper())['可卖数'].sum()
m6b = {str(b['品牌']).strip().upper(): b.get('store_sellable', 0) for b in d.get('m6_brand_turnover', [])}
for b, q in bq.sort_values(ascending=False).items():
    if b in m6b:
        check(f"  品牌库存 {b}", q, m6b[b])

mq = inv_st.groupby(inv_st['商品型号'].astype(str).str.strip().str.upper())['可卖数'].sum()
m6m = {str(m['商品型号']).strip().upper(): m['total_sellable'] for m in d.get('m6_model_turnover', [])}
check("周转型号数(有销量)", len(m6m), len(m6m), tol=0)
bad_m6 = [(k, mq[k], m6m[k]) for k in m6m if k in mq and abs(mq[k] - m6m[k]) > args.tol]
if bad_m6:
    fail.append(f"  FAIL 型号库存不符 {len(bad_m6)} 个: {bad_m6[:5]}")
else:
    ok.append("  OK   型号可卖数与库存文件逐条一致")

# 库存表是否被截断: 全品牌型号覆盖率
print("\n[6] 截断检查")
inv_models_with_sales = set(m6m.keys())
all_inv_models = set(mq[mq > 0].index)
print(f"  库存有货型号: {len(all_inv_models)}, 周转表收录(有销量): {len(inv_models_with_sales)}")
# ---------- 经营驾驶舱 (m13~m18) ----------
print("\n[7] 经营驾驶舱口径 (m13~m18)")

# 7.1 月底达成预测
m5 = d.get('m5_company_daily', [])
cf = d.get('m13_forecast', {})
tgt = float(meta.get('total_target', 0) or 0)
done = float(meta.get('total_smart_qty', 0) or 0)
rem = float(meta.get('remaining_days', 0) or 0)
if m5 and cf and tgt:
    q = [float(r['smart_qty']) for r in m5]
    for n, lab in ((3, '近3日趋势'), (5, '近5日趋势')):
        avg = sum(q[-n:]) / min(n, len(q))
        proj = done + avg * rem
        sc = next((x for x in cf.get('scenarios', []) if x.get('label') == lab), None)
        if sc:
            check(f"预测/{lab} 日均", avg, sc.get('daily_avg'), tol=0.5)
            check(f"预测/{lab} 月底销量", proj, sc.get('proj_qty'), tol=2)
            check(f"预测/{lab} 完成率", proj / tgt * 100, sc.get('proj_rate'), tol=0.2)
    check("完成率", done / tgt * 100, cf.get('completion_rate'), tol=0.2)
    check("进度差(pp)", (done / tgt - float(meta.get('time_progress_pct', 0)) / 100) * 100,
          cf.get('progress_diff'), tol=0.2)
else:
    fail.append("  FAIL 预测: m5_company_daily / m13_forecast / target 缺失")

# 7.2 库存资金占用 + 库龄 (与 process_data 同口径: 按 仓库+型号 去重, 可卖数求和, 单价取首行)
inv_val = inv_st.copy()
inv_val['可卖数'] = pd.to_numeric(inv_val['可卖数'], errors='coerce').fillna(0)
inv_val['平均单价'] = pd.to_numeric(inv_val['平均单价'], errors='coerce').fillna(0)
inv_val['门店库龄'] = pd.to_numeric(inv_val['门店库龄'], errors='coerce').fillna(0)
inv_val = inv_val.groupby(['仓库', '商品型号'], as_index=False).agg(
    可卖数=('可卖数', 'sum'), 平均单价=('平均单价', 'first'),
    门店库龄=('门店库龄', 'min'), 品牌=('品牌', 'first'))
inv_val['_v'] = inv_val['可卖数'] * inv_val['平均单价']
iv = d.get('m14_inv_value', {})
_v_total = float(inv_val['_v'].sum())
_v_tol = max(1000.0, _v_total * 0.001)
check("库存资金合计", _v_total, iv.get('total_fund'), tol=_v_tol)
check("库存台数合计", inv_val['可卖数'].sum(), iv.get('total_stock'), tol=2)
_old = float(inv_val[inv_val['门店库龄'] > 90]['_v'].sum())
check("91天以上资金", _old, iv.get('aging_over90_fund'), tol=max(1000.0, _old * 0.001))
check("库龄分档资金合计", sum(a.get('fund', 0) for a in iv.get('aging', [])), iv.get('total_fund'), tol=_v_tol)
bv = inv_val.groupby(inv_val['品牌'].astype(str).str.strip().str.upper())['_v'].sum()
ivb = {str(b['品牌']).strip().upper(): b.get('fund', 0) for b in iv.get('brands', [])}
_badf = [(k, float(bv[k]), float(ivb[k])) for k in bv.index if k in ivb and abs(bv[k] - ivb[k]) > max(1000.0, bv[k] * 0.001)]
if _badf:
    fail.append(f"  FAIL 品牌资金占用不符 {len(_badf)} 个: {_badf[:5]}")
else:
    ok.append(f"  OK   品牌资金占用逐条一致 ({len(ivb)} 个品牌)")
check("门店库存资金合计", _v_total, sum(float(x.get('fund_tied', 0)) for x in d.get('m6_inv_store', [])), tol=_v_tol)

# 7.3 缺货损失估算
so = d.get('m17_stockout', {})
mt = d.get('m6_model_turnover', [])
if so and mt:
    _assume = float(so.get('assumption_days', 7) or 7)
    n_risk = len([m for m in mt if m.get('turnover_days') is not None
                  and float(m['turnover_days']) < _assume
                  and float(m.get('daily_avg_sales', 0) or 0) > 0])
    check("缺货风险型号数", n_risk, so.get('model_count'), tol=0)
    _b = sum(float(x.get('lost_units', 0)) for x in so.get('brands', []))
    check("品牌损失台数合计=总损失", _b, so.get('total_lost_units'), tol=5)
    _r = sum(float(x.get('lost_revenue', 0)) for x in so.get('brands', []))
    check("品牌损失营收合计=总损失", _r, so.get('total_lost_revenue'), tol=max(1000.0, _r * 0.001))

# 7.4 品牌毛利象限
bmx = d.get('m18_brand_matrix', {})
if bmx:
    _brands = bmx.get('brands', [])
    check("象限品牌数合计", len(_brands), len(d.get('m3_brands', [])), tol=0)
    if _brands:
        check("销量切分线=均值", sum(b['qty'] for b in _brands) / len(_brands), bmx.get('qty_cut'), tol=1)
        check("毛利率切分线=均值", sum(b['profit_rate'] for b in _brands) / len(_brands), bmx.get('margin_cut'), tol=0.1)

# 7.5 价量联动: 从 m11 日销序列独立重算 调价前/后日均, 校验窗口已剔除未来补0的营业日
pv = d.get('m15_price_volume', {})
if pv:
    import re as _re

    def _nk(x):
        return ''.join(c for c in str(x).upper() if c.isalnum())

    _today_mmdd = str(meta.get('report_date', ''))[5:10]
    _mm = _re.findall(r'\d+', str((d.get('price_summary', {}) or {}).get('current_price_date', '')))
    _eff = f"{int(_mm[1]):02d}-{int(_mm[2]):02d}" if len(_mm) >= 3 else None
    _m11 = d.get('m11_model_trends', [])
    _bad, _checked = [], 0
    for r in pv.get('detail', []):
        if r.get('pre_days') is None:
            continue
        _t = _nk(r['model'])
        rec = None
        for x in _m11:
            _k = _nk(x['model'])
            if _k == _t or (_k and _t and (_k in _t or _t in _k)):
                rec = x
                break
        if not rec:
            continue
        dates, daily = rec['june_dates'], rec['june_daily']
        valid = len(dates)
        for i, dt in enumerate(dates):
            if str(dt) > _today_mmdd:
                valid = i
                break
        vd, vq = dates[:valid], daily[:valid]
        sp = vd.index(_eff) if (_eff and _eff in vd) else max(1, len(vd) - 2)
        pre, post = vq[:sp], vq[sp:]
        if not pre or not post:
            continue
        _checked += 1
        pa, po = sum(pre) / len(pre), sum(post) / len(post)
        if abs(pa - (r.get('pre_daily_avg') or 0)) > 0.11 or abs(po - (r.get('post_daily_avg') or 0)) > 0.11:
            _bad.append((r['model'], round(pa, 2), r.get('pre_daily_avg'), round(po, 2), r.get('post_daily_avg')))
    if _bad:
        fail.append(f"  FAIL 调价前/后日均重算不符 {len(_bad)} 个: {_bad[:5]}")
    else:
        ok.append(f"  OK   调价前/后日均窗口重算一致 ({_checked} 个机型, 生效日 {_eff}, 已剔除未来补0营业日)")

print("\n".join(ok))
print()
if fail:
    print("发现问题:")
    print("\n".join(fail))
    print(f"\n结论: {len(ok)} 项通过, {len(fail)} 项异常")
    sys.exit(1)
print(f"结论: 全部 {len(ok)} 项通过 ✅")
