#!/usr/bin/env python3
"""把 generate_dashboard.py 的浅色主题补丁应用到已有的看板 HTML（如月度存档）。

用法:
    python scripts/apply_theme_to_html.py "月度看板存档/3CHUB_2026年8月销售看板.html" ...
    python scripts/apply_theme_to_html.py "月度看板存档/*.html"

说明:
- 浅色逻辑（LIGHT_THEME_CSS + apply_light_theme）直接从 generate_dashboard.py 源码提取执行，
  生成器里的主题规则改了，本脚本自动跟随，无需重复维护。
- 原文件会先备份到 --backup-dir（默认 .workbuddy/backups/）。
- 已经是浅色（含 "Light theme overrides"）的文件会跳过。
"""
import argparse
import ast
import glob
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, 'generate_dashboard.py')


def load_theme_patch():
    """从 generate_dashboard.py 提取 LIGHT_THEME_CSS 与 apply_light_theme。"""
    src = open(GEN, encoding='utf-8').read()
    tree = ast.parse(src)
    picked = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if 'LIGHT_THEME_CSS' in names:
                picked.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == 'apply_light_theme':
            picked.append(node)
    if len(picked) < 2:
        sys.exit('[ERROR] 未能在 generate_dashboard.py 中找到 LIGHT_THEME_CSS / apply_light_theme')
    ns = {}
    exec(compile(ast.Module(body=picked, type_ignores=[]), GEN, 'exec'), ns)
    return ns['apply_light_theme']


def main():
    ap = argparse.ArgumentParser(description='Apply light theme to existing dashboard HTML files')
    ap.add_argument('files', nargs='+', help='HTML 文件路径（支持 glob 通配）')
    ap.add_argument('--backup-dir', default=os.path.join(os.path.dirname(HERE), '.workbuddy', 'backups'),
                    help='原文件备份目录')
    args = ap.parse_args()

    apply_light_theme = load_theme_patch()
    os.makedirs(args.backup_dir, exist_ok=True)

    paths = []
    for pat in args.files:
        paths.extend(sorted(glob.glob(pat)))
    if not paths:
        sys.exit('[ERROR] 没有匹配到任何文件')

    for p in paths:
        if not os.path.isfile(p):
            print(f'[SKIP] 非文件: {p}')
            continue
        html = open(p, encoding='utf-8').read()
        if 'Light theme overrides' in html:
            print(f'[SKIP] 已是浅色版: {p}')
            continue
        if '</style>' not in html:
            print(f'[SKIP] 无 </style>, 结构异常: {p}')
            continue
        shutil.copy2(p, os.path.join(args.backup_dir, os.path.basename(p)))
        out = apply_light_theme(html)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(out)
        print(f'[OK] 已转浅色: {p} ({len(out)/1024:.0f}KB)')


if __name__ == '__main__':
    main()
