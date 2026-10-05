# v1.0 流程与模块边界

```text
1 设计抽样范围
  时期 + Tier + 期刊 + MAIN/HOLDOUT/RESERVE
       ↓
2 CNKI候选题录采集
  登录
  → LY='期刊名'
  → 页面发表时间
  → 年份分片/低并发
  → 结果页勾选
  → 原生XLS
  → 合并去重
  → unique.json
       ↓
3 Candidate Pool
  自动匹配 journal × year × period × tier
  → Article Eligibility
  → 人工只处理 UNCERTAIN
       ↓
4 Freeze + Reproducible Sampling
  选择抽样方法
  → 固定 seed
  → SHA256确定性排序
  → MAIN/HOLDOUT/RESERVE
  → P/H/R编号
  → sampling_protocol
  → sampling_certificate
  → full ranking
       ↓
5 PDF / Evidence
  自动下载（best-effort）
  → CNKI链接兜底
  → Evidence Queue
```

## 核心边界

- CNKI 采集模块负责尽量完整取得候选总体，不决定最终抽哪篇；
- Eligibility 决定哪些记录进入可抽候选池；
- Sampling Core 只对冻结后的候选池排序和抽选；
- PDF 下载失败不能静默改变样本；
- `sampling_protocol.json + sampling_ranking_full.csv + candidate_registry.csv + sampling_frame.csv` 构成抽样复现的核心证据链。
