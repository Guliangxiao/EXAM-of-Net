# 实验记录（网络鲁棒性度量）

服务器：`115.156.159.91:1205`（host: amax，40 核，251 GB，4×RTX 3090）
解释器：`/opt/anaconda31/bin/python`（3.10.9，networkx 2.8.4，numpy 1.23.5，scipy 1.10.0，pandas 1.5.3，matplotlib 3.7.0）
远端目录：`~/netw_sci/`（code / out / logs）

## 实验规模

- 7 个网络族 × 3 个规模（500/1000/2000）× 5 个种子 = **105 个网络**
- 每个网络 3 种攻击顺序（random / degree / betweenness）
- 基准攻击者（不接触任何度量）：自适应度攻击、自适应介数攻击
- 攻击预算：代价预算 10%、20%，节点预算 20%（经典设定）

## 运行命令

```bash
python code/run_exp.py --out out/full.csv --workers 32 --sizes 500,1000,2000 --seeds 5   # 20 s
python code/exp_gt2.py --out out/gt_betweenness.csv --workers 32                          # 210 s
python code/exp_alpha.py --csv out/full.csv --gt2 out/gt_betweenness.csv \
       --out out/alpha_scan.csv                                                          # 20 s
python code/analyze.py --csv out/full.csv --gt2 out/gt_betweenness.csv --outdir out/analysis
python code/figs.py --csv out/full.csv --analysis out/analysis \
       --alpha-csv out/alpha_scan_rho.csv --outdir out/figs
```

## 关键结果（degree 攻击序，105 网络）

Spearman ρ（负值 = 度量正确反映损伤）：

| α | 自适应度 D20 | 自适应介数 B20 | 等代价 D_unif |
|---|---|---|---|
| 0（经典 R） | −0.259 | −0.011 | **−0.953** |
| 0.5 | −0.300 | −0.069 | −0.926 |
| 1.0 | −0.618 | −0.415 | −0.749 |
| **1.5** | **−0.769** | **−0.873** | +0.249 |
| 2.0 | −0.455 | −0.667 | +0.640 |
| 3.0 | −0.179 | −0.406 | +0.827 |

- 排序变化：Kendall τ(R0, R1) = 0.659；τ(R0, R2) = −0.356（排序被实质改写甚至反转）
- 间隙随异质性：ρ(R1−R0, CV_k) = 0.716（degree）/ 0.746（betweenness）
- 留一网络族：R1 的 ρ 始终在 [−0.813, −0.394]，符号稳定

## 必须写进论文的负面结果

- 族内（同族同规模，5 个种子）细粒度排序一致性很弱：R1 在 10/21 组中优于 R0（符号检验 p=1），
  组内 τ 中位数 R0=0.00、R1=−0.20。
- 控制网络族后的偏相关显著衰减：R0 +0.287、R1 −0.227、R2 −0.362。
- 结论表述应为：**度量适用于"跨设计/跨网络族的比较"**，对同族内细微结构差异判别力有限；
  R1 的优势有相当一部分来自族间差异（言明即可，不可包装成完全族内有效）。

## 论文落点

1. 经典 R 隐含"等代价"假设；在代价受限威胁下相关性接近 0（低预算下甚至反号）。
2. 代价加权族 R_α，α=0 严格退化为 R；α≈1.5 时代价受限场景相关性最强。
3. α 过大（≥2）在等代价场景反向失效（ρ→+0.83），说明**度量必须与威胁模型匹配**。
4. α 的选取可以测量，不必凭经验。

## 补充分析（第 4 天）

`code/exp_extra.py` 产出三张表，供正文表 2、表 3 与 6.5 节使用：

- `by_family_rho.csv`：分族 Spearman ρ（每族 15 个网络）
- `by_size.csv`：分规模 Spearman ρ（N=500/1000/2000）
- `cascade_calibration.csv`：Motter–Lai 级联标定（β × 初始失效比例）

分族结果修正了此前的结论：R₁ 的增益集中在幂律族（PL-2.5 由 +0.357 到 −0.746，PL-3.0 由 +0.204 到 −0.839），
在 ER/WS 等同质族内三种度量都接近噪声。BA-m3 的改善来自 R₂（−0.355）而非 R₁（+0.246）。

反例对（6.7 节）：PL-3.0、N=1000、种子 0 与 1，明细见 `counterexamples.csv`
（种子 0：kmax=115、CV=1.78、R₀=0.033、R₁=0.183、D₂₀=0.678、代价预算下可拆 32 个节点；
种子 1：kmax=39、CV=0.91、R₀=0.046、R₁=0.150、D₂₀=0.947、可拆 70 个）。
经典 R 判种子 1 更稳，实测与 R₁ 都判种子 0 更稳。

`verify3.log` 为数字核对输出：66 项全部 ALL MATCH。
