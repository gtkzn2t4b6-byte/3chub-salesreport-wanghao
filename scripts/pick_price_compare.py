#!/usr/bin/env python3
"""按「对比约10天前价格表」规则, 从 Downloads 中挑选价格对比文件。

用法:
    python scripts/pick_price_compare.py "Retail price list 07.09.2026.xlsx"
    python scripts/pick_price_compare.py 2026-09-07            # 直接给当前日期
    python scripts/pick_price_compare.py 07.09.2026 --days 10  # 可改间隔天数

规则: 在 ~/Downloads 找 "Retail price list DD.MM.YYYY.xlsx",
      目标日期 = 当前价格表日期 - N 天(默认10),
      取与目标日期绝对差最小的一份(必须早于当前价格表)。
"""
import sys, re, glob, os
from datetime import datetime, timedelta


def parse_date(text):
    """从文件名或字符串中解析日期, 支持 DD.MM.YYYY / YYYY-MM-DD"""
    m = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def pick(current, days=10, search_dir=None):
    search_dir = search_dir or os.path.expanduser('~/Downloads')
    cur = parse_date(str(current))
    if not cur:
        raise SystemExit(f'无法从 {current!r} 解析日期')
    target = cur - timedelta(days=days)

    cands = []
    for p in glob.glob(os.path.join(search_dir, 'Retail price list *.xlsx')):
        d = parse_date(os.path.basename(p))
        if d and d < cur:
            cands.append((abs((d - target).days), d, p))
    if not cands:
        raise SystemExit('未找到更早的价格表文件')

    cands.sort(key=lambda x: (x[0], -x[1].timestamp()))
    return cands[0][2], cands[0][1], cur, target, days


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    days = 10
    if '--days' in sys.argv:
        days = int(sys.argv[sys.argv.index('--days') + 1])
    if not args:
        raise SystemExit(__doc__)
    path, d, cur, target, n = pick(args[0], days)
    print(path)
    sys.stderr.write(
        f'当前价格表 {cur:%Y-%m-%d} | 目标(前{n}天) {target:%Y-%m-%d} '
        f'| 选中 {d:%Y-%m-%d}\n'
    )
