# v0.4 界面与流程

```text
1 设计范围
  P1/P2/P3 + T1-T5 + 期刊 + 目标样本数
       ↓
2 CNKI自动采集插件
  自动 queries.json
  → 自动打开CNKI
  → 批量原生XLS导出
  → 命中量/导出量核验
  → 合并/去重
  → unique.json
       ↓
3 Candidate Pool
  自动匹配时期/Tier
  → Article Eligibility
  → 人只处理UNCERTAIN
       ↓
4 Freeze + Sample
  SHA256确定性排序
  → MAIN/HOLDOUT/RESERVE
  → P/H/R编号
  → Download Queue
  → Evidence Queue
```

## 关键边界

- CNKI采集插件只负责“把候选总体完整拿回来”，不决定最终选哪篇。
- Sampling Assistant 决定 Eligibility、候选池冻结和抽样。
- 用户只在登录/安全验证、UNCERTAIN复核、最终PDF下载和必要截图时介入。
- 当前CNKI外部标签和历史 `tier_at_publication` 分开保存。
