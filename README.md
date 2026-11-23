# EXAM-of-Net

《网络科学》课程论文《考虑攻击代价的复杂网络鲁棒性度量研究——度量改进与攻击仿真检验》的
实验代码与结果数据。论文提出代价加权鲁棒性度量族 $R_\alpha$，并在 105 个网络上与
"不接触度量的自适应攻击者"作对照检验。

## 目录结构

```
code/        实验代码
  netlib.py         网络生成 / 攻击序列 / R_α 计算 / Motter–Lai 级联
  run_exp.py        主实验：105 网络 × 3 攻击序列
  exp_gt2.py        第二独立判据（自适应介数攻击）
  exp_alpha.py      代价指数 α 扫描
  exp_extra.py      分族 / 分规模 / 级联标定
  analyze.py        Spearman、bootstrap、留一网络族、偏相关、组内一致性
  figs.py           论文 4 张图
  verify_numbers.py 论文正文数字与实验产出的逐条核对
  reproduce.sh      一键复现全流程
results/     实验输出（CSV）与核对日志
figs/        论文插图（PNG 300 dpi + 矢量 PDF）
```

## 环境

- Python ≥ 3.8（开发环境 3.10.9）
- NetworkX ≥ 2.8、NumPy、SciPy、pandas、matplotlib

```bash
pip install -r requirements.txt
```

## 复现

```bash
bash code/reproduce.sh
```

依次执行：主实验（约 20 s）→ 第二判据（约 210 s）→ α 扫描（约 20 s）→
统计与稳健性检查 → 出图 → 数字核对。全部结果写入 `results/` 与 `figs/`。

单步运行示例：

```bash
python code/run_exp.py --out results/full.csv --workers 32 --sizes 500,1000,2000 --seeds 5
python code/analyze.py --csv results/full.csv --gt2 results/gt_betweenness.csv --outdir results
python code/figs.py --csv results/full.csv --analysis results --alpha-csv results/alpha_scan_rho.csv --outdir figs
```

## 数据说明

| 文件 | 内容 |
|---|---|
| `results/full.csv` | 主实验：105 个网络 × 3 种攻击序列 = 315 行，含 R₀/R₀.₅/R₁/R₂ 与三种攻击预算下的损伤 |
| `results/gt_betweenness.csv` | 自适应介数攻击者的损伤（第二独立判据） |
| `results/metrics_vs_truth.csv` | 各度量与各判据的 Spearman ρ、p 值与 bootstrap 95% 置信区间 |
| `results/robustness.csv` | 留一网络族区间、控制族偏相关 |
| `results/by_family_rho.csv` / `by_size.csv` | 分族、分规模的相关系数 |
| `results/cascade_calibration.csv` | Motter–Lai 级联标定（表 3 来源） |
| `results/counterexamples.csv` | 6.7 节反例对的明细 |
| `results/verify3.log` | 论文数字自检输出（66 项 ALL MATCH） |

注：`full.csv` 含单次耗时列 `secs`，重跑时字节会变，但统计量不变。

## 结果摘要

在代价受限威胁下，经典 R 与实际损伤几乎不相关（ρ = −0.26，低预算下 ρ = +0.05）；
代价加权度量在 α ≈ 1.5 时相关性最强（ρ 达 −0.77 ~ −0.87）；
而 α ≥ 2 会在等代价场景中反向失效（ρ = +0.64 ~ +0.83）。
详见论文。

## 许可

课程作业代码，仅供学习与复现参考。
