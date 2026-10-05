# 法学论文抽样与自动编号助手 v1.0

**Author: Synex1213**  
Repository: `https://github.com/Synex1213/sample-llm`

这是一个面向法学论文 T2 Benchmark / LLM 学术评价实验的数据采样工具。它把：

**抽样范围设计 → CNKI 候选题录采集 → Article Eligibility → 候选池冻结 → 可复现抽样 → 自动编号 → PDF / 链接交付**

串成一条可审计的工作流。

v1.0 以已经实测可用的 **v0.4.6** 为基线，只做必要补丁，没有改动整体研究框架。

## 1. v1.0 相对 v0.4.6 的三个核心更新

### 1.1 CNKI“当前页全选”稳定性补丁

CNKI 结果表有时已经显示 50 条论文，但“全选”控件的前端状态尚未初始化，可能出现：

```text
当前页第 1 次全选未生效（应新增 50，实际新增 0）
```

v1.0 不把第一次点击结果直接当成成功，而是：

```text
等待结果行稳定
→ 找真正可见的全选框
→ 点击
→ 检查 #selectCount 是否真实增加
→ 未增加则等待后重试
→ 两次失败后才刷新结果页
→ 再次验证
```

同时保留此前独立诊断器已经验证通过的两个小修复：

- KNS8 日期控件使用正确的 `Locator.evaluate((el, value) => ...)` 参数形式；
- “检索”按钮依次尝试 normal click → force click → DOM click，并确认结果页确实出现。

### 1.2 抽样方法显式化，并生成可复现凭证

冻结候选池后，用户现在要明确选择抽样方法：

1. **确定性哈希 + 期号均衡（推荐）**  
   对每个候选论文计算：

   `SHA256(seed | stratum_id | candidate_key)`

   先在各期号内部排序，再按期号轮转抽取，降低样本集中在同一期号的概率。

2. **确定性哈希直接排序**  
   直接按上述 SHA256 值从小到大排序抽取。

两种方法都满足：

> 同一候选池 + 同一抽样框 + 同一方法 + 同一 seed = 同一结果。

抽样完成后自动生成：

- `sampling_protocol.json`：方法、seed、规则、输入指纹；
- `sampling_certificate.csv`：每个 MAIN / HOLDOUT / RESERVE 的哈希值、顺位、候选池大小；
- `sampling_ranking_full.csv`：每个抽样格的完整候选排序；
- `SAMPLING_PROTOCOL.md`：人可以直接阅读的复现说明；
- `Run fingerprint`：把抽样方法、seed、sampling frame 和 candidate registry 指纹合成的运行指纹。

这些文件和 `sampling_frame.csv`、`candidate_registry.csv` 一起进入完整结果包，因此可以独立复核抽样结果，而不只是相信网页显示。

### 1.3 顶部流程卡片删除

网页顶部不再重复展示 4 个流程卡，只保留项目标题和一句说明，减少视觉占用。正式流程仍在页面的 1–4 个主体模块中完整呈现。

---

## 2. 推荐操作顺序

```text
1. 设计抽样范围
   ↓
2. 安装 / 修复 CNKI 采集包
   ↓
3. 打开 CNKI 登录
   ↓
4. 完成登录后点击“登录完成”
   ↓
5. 选择并发窗口数（建议 2）
   ↓
6. 开始信息采集
   ↓
7. 对 UNCERTAIN 论文做勾选复核
   ↓
8. 选择抽样方法 + seed
   ↓
9. 冻结候选池并抽样
   ↓
10. 保存抽样凭证与完整结果包
   ↓
11. 尝试自动下载 PDF；失败项使用 CNKI 链接手动下载
```

## 3. 抽样范围

默认时期：

```text
P1 = 2018–2020
P2 = 2021–2023
P3 = 2024–2025
```

期刊与 T1–T5 操作化分层位于：

`config/journal_registry.json`

T1–T5 是本研究使用的操作化编码，不是 CNKI 官方排名。

## 4. CNKI 候选题录采集

当前 KNS8 专业检索使用：

```text
LY='期刊名'
```

年份不再写成旧版 `YE` 字段，而是通过页面“发表时间”控件设置。

### 登录与采集分离

```text
打开 CNKI 登录
→ 完成机构 / 个人登录及必要验证
→ 点击“登录完成”
→ 开始信息采集
```

登录资料只保存在本机：

`runtime_outputs/cnki_master_profile/`

不要提交到 GitHub。

### 并发采集

CNKI 原生 XLS 导出使用“已选文献”状态。为了避免并发窗口互相覆盖，程序使用独立 profile 副本。

- 默认并发：2；
- 上限：3；
- 支持按年份分片；
- 单期刊、单时期也可以拆成年份任务并行。

高并发不一定更快，并可能增加安全验证概率。

## 5. Article Eligibility

程序自动处理明显类型，例如：

- 书评；
- 访谈；
- 会议纪要；
- 征稿启事；
- 卷首语；
- 新闻 / 资讯；
- 目录；
- 译文等。

边界论文标记为 `UNCERTAIN`。用户只需要在网页里勾选要纳入的论文，不再逐行输入 `include / exclude`。

Eligibility 规则位于：

`config/eligibility_rules.json`

## 6. MAIN / HOLDOUT / RESERVE

- `MAIN`：正式实验样本；
- `HOLDOUT`：独立保留样本；
- `RESERVE`：预先冻结的替补顺序。

默认编号：

```text
P001...  MAIN
H001...  HOLDOUT
R001...  RESERVE
```

如果正式样本 PDF 无法获得，不应人工任意换一篇，而应按同一抽样格的 RESERVE 顺序替补，并记录 replacement reason。

## 7. 完整结果包

抽样完成后 `sampling_result_bundle.zip` 包含主要文件：

```text
sampling_frame.csv
candidate_registry.csv
selected_samples.csv
reserve_samples.csv
sampling_issues.csv
sampling_protocol.json
SAMPLING_PROTOCOL.md
sampling_certificate.csv
sampling_ranking_full.csv
download_queue.csv
evidence_queue.csv
safe_sample_manifest.csv
labels_vault_seed_DO_NOT_COMMIT.csv
```

其中最重要的复现材料是：

```text
sampling_frame.csv
candidate_registry.csv
sampling_protocol.json
sampling_ranking_full.csv
sampling_certificate.csv
```

## 8. PDF 获取

PDF 自动下载属于 best-effort：

- 能直接下载则保存；
- 遇到机构权限、订单页或页面结构变化时记录失败；
- 自动下载失败不会改变抽样结果；
- 每篇入选样本保留 CNKI 详情页 URL，采集同学可以直接打开。

PDF 不强制重命名为 `P001.pdf`，后续通过 manifest 绑定 `paper_id`。

## 9. Windows 快速启动

完整解压后双击：

```text
run_windows.bat
```

不要直接从 WinRAR 临时目录运行。

首次运行会创建 `.venv` 并安装依赖。程序会在 7860–7870 中自动寻找空闲端口。

## 10. 目录结构

```text
app.py
config/
  journal_registry.json
  eligibility_rules.json
integrations/
  cnki_external.py
  collector_runner.py
  login_runner.py
  pdf_downloader.py
sampling_core/
  planning.py
  metadata.py
  eligibility.py
  sampler.py
  exporter.py
  utils.py
third_party/
demo/
runtime_outputs/
README.md
CHANGELOG_v1.0.md
DESIGN_AND_FLOW.md
TEST_v1.0.md
```

## 11. 第三方项目

本项目使用 / 参考：

- `JYao-Chen/cnki-metadata-exporter`：CNKI 原生 XLS 导出、断点续跑、合并与去重主干，MIT License；
- `ZhuoerYu/CNKI-Paper-Crawler`：PDF 下载控件识别思路参考其公开实现，MIT License。

相关说明见 `THIRD_PARTY_NOTICES.md` 与 `third_party/`。

本工具不会绕过登录、验证码、付费或机构访问控制。

## 12. 仓库卫生

不要提交：

- `.venv/`；
- `runtime_outputs/` 中的登录 profile；
- 下载的真实 PDF；
- 私有标签表；
- Cookie / session；
- `labels_vault_seed_DO_NOT_COMMIT.csv` 等真实标签文件。
