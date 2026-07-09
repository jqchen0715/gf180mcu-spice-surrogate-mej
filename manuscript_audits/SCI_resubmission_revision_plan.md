# SCI 重投改稿路线

## 一句话主张

本文不再主张“提出新的机器学习算法”，而主张：在 GF180MCU 标准单元早期 sizing 与 PVT/load/slew 探索中，构建一个可复现、带 provenance、带少样本 corner calibration 的 SPICE-efficient 候选筛选流程，并用 primary/validation 两批 SPICE 数据证明它可用于排序、校准和仿真预算分配。

## 论文定位调整

| 旧定位 | 新定位 |
|---|---|
| ML surrogate workflow / benchmark | SPICE-efficient standard-cell candidate screening and calibration workflow |
| 强调模型比较 | 强调减少 SPICE 筛选成本、候选排序、corner 支持点校准 |
| active learning 作为核心贡献 | active learning 降为 retrospective pool-acquisition study |
| provenance 是口号 | provenance 用 legacy source negative-control ablation 支撑 |
| “standard-cell exploration” 泛化较宽 | 限定为 GF180MCU controlled transistor-level arcs, not full Liberty/sign-off |

## 已补强的实验证据

| 审稿问题 | 当前处理 |
|---|---|
| 现代强基线不足 | 新增 GPR、XGBoost、LightGBM、CatBoost，并保留 SVR/RF/ExtraTrees/GB/MLP/Ridge |
| 缺统计显著性 | 新增 Friedman test 和 paired Wilcoxon signed-rank test with Holm correction |
| 缺排序指标 | 新增 Spearman、Kendall Tau、Precision@K、Recall@K、NDCG@K |
| 缺不确定性/区间 | 新增 split conformal prediction intervals，报告 coverage 和 interval width |
| 缺工程耗时 | 解析 ngspice log 中 total elapsed time，并测训练/推理耗时 |
| 缺物理解释 | 新增 permutation importance，突出 Wn、Cload、corner、Vdd、topology/arc 的作用 |
| validation 不够强 | 新增所有 11 个模型的 V2->V3 validation 表，而不只报告 GB/SVR/MLP |

## 仍不能硬声称的内容

| 不能声称 | 应该写成 |
|---|---|
| 可替代 SPICE | 可用于 early screening; selected points require SPICE re-validation |
| 完整 standard-cell characterization | controlled transistor-level arcs, not complete Liberty tables |
| 跨 PDK 泛化 | same-flow GF180MCU validation only; cross-PDK remains future work |
| 真正 online active learning | retrospective oracle-backed pool acquisition |
| provenance 直接提升所有模型精度 | provenance prevents unsafe source fusion; legacy data caused negative transfer |
| GNN/PINN/Transformer 被全面击败 | not directly comparable without graph/layout/physics representations |

## 新稿结构

1. Introduction：从 characterization/simulation-cost bottleneck 切入，不从 ML 热点切入。
2. Related work：分成 ML-assisted characterization、multi-fidelity/provenance、uncertainty/ranking。
3. Dataset and SPICE flow：强调 GF180MCU/ngspice、controlled arcs、两批 SPICE 数据、日志 provenance。
4. Method：feature encoding、candidate score、conformal interval、few-shot corner support。
5. Results：
   - primary + validation prediction using stronger baselines;
   - statistical tests and cost;
   - feature importance and physical interpretation;
   - candidate ranking metrics;
   - conformal intervals;
   - cross-cell transfer and corner support;
   - source-fusion negative control.
6. Discussion：正面解释边界和失败模式。
7. Conclusion：收窄但有力。

## 最适合下一轮投稿的期刊判断

优先建议投 `Integration, the VLSI Journal` 或类似 EDA/VLSI 应用型 SCI 期刊；若继续投 `Microelectronics Journal`，必须避免像第一次那样呈现为 ML benchmark。新稿可以作为 Microelectronics-style manuscript，但论证要更像 microelectronics design automation / characterization-effort reduction。

