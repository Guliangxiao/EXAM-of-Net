#!/usr/bin/env bash
# 一键复现论文全部实验与图表。
#
# 在服务器 ~/netw_sci/ 下执行：
#     bash code/reproduce.sh
#
# 预计耗时：主实验 20 s + 第二判据 210 s + α 扫描 20 s + 统计/出图 < 5 s。
set -euo pipefail

PY=${PY:-/opt/anaconda31/bin/python}
cd "$(dirname "$0")/.."

echo "[1/6] 主实验（105 网络 × 3 攻击序）"
"$PY" code/run_exp.py --out out/full.csv --workers 32 --sizes 500,1000,2000 --seeds 5

echo "[2/6] 第二独立判据（自适应介数攻击）"
"$PY" code/exp_gt2.py --out out/gt_betweenness.csv --workers 32 --sizes 500,1000,2000 --seeds 5

echo "[3/6] α 扫描"
"$PY" code/exp_alpha.py --csv out/full.csv --gt2 out/gt_betweenness.csv --out out/alpha_scan.csv

echo "[4/6] 统计与稳健性检查"
"$PY" code/analyze.py --csv out/full.csv --gt2 out/gt_betweenness.csv --outdir out/analysis

echo "[5/6] 出图"
"$PY" code/figs.py --csv out/full.csv --analysis out/analysis \
      --alpha-csv out/alpha_scan_rho.csv --outdir out/figs

echo "[6/6] 核对论文中引用的数字"
"$PY" code/verify_numbers.py

echo "全部完成：out/full.csv, out/analysis/, out/figs/ 已生成。"
