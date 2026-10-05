# Changelog

## v1.0 — Public stable release

首个面向公开使用整理的稳定版本，以已实际验证的 v0.4.6 工作流为基础。

### CNKI 采集

- KNS8 专业检索使用 `LY=文献来源`；
- 年份通过页面“发表时间”控件设置；
- 登录与采集分离；
- 支持 1–3 个低并发浏览器窗口和年份分片；
- 结果页“全选”增加真实已选数量校验、等待重试和刷新兜底；
- 检索按钮支持 normal / force / DOM 三层点击兜底；
- 继续保留原生 XLS、批次续接、合并和去重流程。

### Eligibility

- 自动处理明显非研究论文；
- `UNCERTAIN` 使用网页勾选复核，不要求手工输入 include / exclude。

### 可复现抽样

- 新增“确定性哈希 + 期号均衡”与“确定性哈希直接排序”两种方式；
- 固定 `SHA256(seed | stratum_id | candidate_key)` 作为确定性排序基础；
- 输出 sampling protocol、完整排序、逐样本凭证、输入 SHA256 与 run fingerprint。

### 交付与仓库整理

- README 重写为公开使用说明；
- 删除历史开发期说明文件和重复根目录文件；
- 增加 MIT License；
- 保留第三方许可证和版本说明；
- 运行数据、登录状态和真实 PDF 继续由 `.gitignore` 排除。
