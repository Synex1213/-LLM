# v1.0

v1.0 以 v0.4.6 为稳定基线，不重写整体架构，只合并经实际测试确认需要的补丁。

## 1. 结果页全选稳定性

- 等待结果行数量稳定后再点击；
- 只操作真实可见的“全选”控件；
- 以 `#selectCount` 是否增加作为成功判据；
- 第一次失败先等待重试，不立即刷新；
- 连续失败后才刷新结果页并再次验证。

## 2. KNS8 检索小修复

- 修复日期控件 `Locator.evaluate()` 参数形式；
- 检索按钮增加 normal / force / DOM 三层点击；
- 点击后必须检测结果页或无结果提示真实出现。

这些逻辑来自已经单独跑通的 CNKI 勾选→XLS 诊断流程。

## 3. 抽样协议与复现凭证

新增两种显式抽样方式：

- `hash_issue_balanced`：确定性哈希 + 期号均衡（默认）；
- `hash_simple`：确定性哈希直接排序。

均以：

`SHA256(seed | stratum_id | candidate_key)`

为确定性优先级基础。

抽样结果包新增：

- `sampling_protocol.json`；
- `SAMPLING_PROTOCOL.md`；
- `sampling_certificate.csv`；
- `sampling_ranking_full.csv`；
- sampling frame / candidate registry SHA256；
- run fingerprint。

## 4. UI 精简

删除页面顶部重复的四张步骤卡片，只保留标题和简短说明。

## 5. 项目整理

- 删除旧版 changelog / README_FIX 等历史文件；
- 删除运行缓存与测试产物；
- 合并重复补丁文件；
- README、测试说明、流程说明统一更新为 v1.0；
- 项目作者统一为 `Synex1213`。
