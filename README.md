# Law Paper Sampling Assistant

**法学论文抽样与自动编号助手 · v1.0**  
Author: **Synex1213**

[![CI](https://github.com/Synex1213/sample-llm/actions/workflows/ci.yml/badge.svg)](https://github.com/Synex1213/sample-llm/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个面向法学论文 Benchmark / LLM 学术评价研究的数据采样工具。它把“研究范围设计、CNKI 候选题录采集、论文类型筛选、候选池冻结、可复现抽样、自动编号、PDF/链接交付”连接成一条可审计、可复现的工作流。

> 本项目用于科研数据构建与抽样管理。它不会绕过登录、验证码、机构访问权限、付费或其他访问控制，也不隶属于 CNKI。

## 主要能力

- **网页化抽样设计**：直接选择时期、Tier、期刊和 MAIN / HOLDOUT / RESERVE 数量。
- **CNKI 候选题录采集**：使用 KNS8 专业检索，支持登录状态保存、年份分片和低并发多窗口采集。
- **Article Eligibility**：自动排除明显非研究论文，仅把边界条目交给人工复核。
- **确定性抽样**：基于 SHA256 排序，支持“期号均衡”和“直接排序”两种可复现方法。
- **自动编号**：生成 Pxxx / Hxxx / Rxxx 编号，并冻结 MAIN / HOLDOUT / RESERVE 关系。
- **抽样凭证**：自动保存抽样协议、完整排序、逐样本凭证和输入数据指纹。
- **PDF / 链接交付**：自动下载为 best-effort；失败时保留 CNKI 详情页链接，不改变既定样本。

## 工作流

```text
研究范围设计
    ↓
CNKI 登录
    ↓
候选题录采集（LY + 页面发表时间）
    ↓
合并、去重、匹配时期/Tier
    ↓
Article Eligibility
    ↓
人工复核 UNCERTAIN
    ↓
冻结候选池
    ↓
选择抽样方法 + seed
    ↓
确定性抽样
    ↓
MAIN / HOLDOUT / RESERVE
    ↓
P/H/R 自动编号
    ↓
抽样凭证 + 下载任务 + Evidence Queue
    ↓
PDF 自动获取 / CNKI 链接兜底
```

## 环境要求

推荐环境：

- Windows 10 / 11（当前主要测试平台）
- Python 3.11+
- Microsoft Edge 或 Google Chrome
- 能正常访问 CNKI 的网络环境
- 如需导出/下载受权限控制的内容，请使用你本人有权使用的机构或个人账号

macOS / Linux 提供启动脚本，但 CNKI 浏览器自动化的实际兼容性可能因浏览器和登录环境不同而变化。

## 快速开始

### Windows

1. 下载仓库 ZIP 或 clone 仓库。
2. **完整解压**到普通文件夹，不要直接在 WinRAR 临时目录中运行。
3. 双击：

```text
run_windows.bat
```

脚本会：

1. 创建 `.venv`；
2. 安装 `requirements.txt`；
3. 启动本地网页应用。

程序默认尝试端口 7860，如被占用会在 7860–7870 之间寻找可用端口。

### macOS / Linux

```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

## 第一次使用

### 1. 设计抽样范围

界面中选择：

- 参与时期 P1 / P2 / P3；
- T1–T5；
- 每个 Tier 中参与的期刊；
- MAIN / HOLDOUT / RESERVE 数量。

当前默认时期：

```text
P1 = 2018–2020
P2 = 2021–2023
P3 = 2024–2025
```

期刊分层配置位于：

```text
config/journal_registry.json
```

> T1–T5 是本研究使用的操作化编码，不代表 CNKI 官方排名。

### 2. 安装 / 修复 CNKI 采集组件

在网页中点击：

```text
安装 / 修复采集包
```

项目内固定保存 `cnki-metadata-exporter 0.2.0` 的安装包与许可证，用于减少上游版本变化带来的不确定性。

### 3. 登录 CNKI

按顺序操作：

```text
打开 CNKI 登录
→ 完成机构/个人登录及必要安全验证
→ 回到工具点击“登录完成”
→ 开始信息采集
```

登录资料仅保存在本机：

```text
runtime_outputs/cnki_master_profile/
```

该目录已被 `.gitignore` 排除，不应提交到 GitHub。

### 4. 采集候选题录

当前 KNS8 专业检索使用：

```text
LY='期刊名'
```

年份通过页面“发表时间”控件设置，不使用旧版 `YE` 字段。

采集支持：

- 1–3 个低并发窗口；
- 按年份分片；
- 已完成批次续接；
- 原生 XLS 导出；
- 最终合并和去重。

**建议并发数保持 2。** 更高并发不一定更快，并可能增加安全验证概率。

v1.0 对结果页“全选”增加了验证机制：程序只有在“已选文献数”真实增加后才认为当前页勾选成功，避免页面尚未初始化时出现假成功。

### 5. Article Eligibility

程序会自动识别明显不适合作为研究论文样本的条目，例如：

- 书评；
- 访谈；
- 会议纪要；
- 征稿启事；
- 卷首语；
- 新闻 / 资讯；
- 目录；
- 译文等。

边界条目标记为 `UNCERTAIN`。用户只需在网页中勾选要纳入的条目，不需要逐行输入 `include / exclude`。

规则配置位于：

```text
config/eligibility_rules.json
```

## 可复现抽样

冻结候选池后，v1.0 提供两种抽样方式。

### 方法 A：确定性哈希 + 期号均衡（推荐）

每个候选论文的优先级基于：

```text
SHA256(seed | stratum_id | candidate_key)
```

程序先在各期号内部按哈希值排序，再按期号轮转抽取，以降低样本集中在同一期号的概率。

### 方法 B：确定性哈希直接排序

使用同样的 SHA256 值，在同一抽样格中直接从小到大排序后抽取。

### 复现条件

以下四项保持一致时，应得到一致结果：

```text
sampling frame
+ candidate registry
+ sampling method
+ seed
```

抽样完成后会自动保存：

```text
sampling_protocol.json
SAMPLING_PROTOCOL.md
sampling_certificate.csv
sampling_ranking_full.csv
```

其中：

- `sampling_protocol.json`：方法、seed、规则、输入 SHA256 和运行指纹；
- `sampling_certificate.csv`：每个最终样本的 candidate_key、draw_hash、draw_rank、候选池大小等；
- `sampling_ranking_full.csv`：每个抽样格中所有候选论文的完整排序；
- `SAMPLING_PROTOCOL.md`：便于人工阅读和论文方法部分引用的协议说明。

## MAIN / HOLDOUT / RESERVE

- `MAIN`：正式实验样本；
- `HOLDOUT`：独立保留样本；
- `RESERVE`：预先冻结的替补顺序。

默认编号：

```text
P001...  MAIN
H001...  HOLDOUT
R001...  RESERVE
```

如果正式样本 PDF 无法取得，不应人工任意换样本。应按照同一抽样格的 RESERVE 顺序替补，并记录 replacement reason。

## 输出文件

完整结果包 `sampling_result_bundle.zip` 主要包含：

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

其中与抽样复现最直接相关的是：

```text
sampling_frame.csv
candidate_registry.csv
sampling_protocol.json
sampling_ranking_full.csv
sampling_certificate.csv
```

## PDF 获取

PDF 自动下载属于 **best-effort**：

- 能直接下载则保存；
- 遇到机构权限、二次下载页或页面结构变化时记录失败；
- 自动下载失败不会改变已经冻结的样本；
- 每篇入选样本尽量保留 CNKI 详情页 URL，方便人工补下载。

PDF 不要求重命名为 `P001.pdf`。后续流程通过 manifest 将原始 PDF 与 `paper_id` 绑定。

## 项目结构

```text
sample-llm/
├─ app.py                     # Gradio 前端和工作流入口
├─ config/                    # 期刊分层与 Eligibility 规则
├─ integrations/              # CNKI 登录、采集和 PDF 获取
├─ sampling_core/             # 抽样框、元数据、筛选、抽样、结果导出
├─ third_party/               # 固定第三方采集组件与许可证
├─ demo/                      # 合成演示数据
├─ runtime_outputs/           # 本地运行输出（不提交真实数据）
├─ requirements.txt
├─ run_windows.bat
├─ run_mac_linux.sh
├─ CHANGELOG.md
├─ THIRD_PARTY_NOTICES.md
├─ LICENSE
└─ VERSION
```

## 合成示例数据

`demo/demo_candidates_SYNTHETIC.csv` 仅用于测试流程和界面，不是真实研究样本，也不应被用于正式结果分析。

## 隐私与数据管理

不要提交到公开仓库：

- `.venv/`；
- CNKI 登录 profile、Cookie、session；
- 下载的真实论文 PDF；
- 私有标签表；
- 未公开的研究数据；
- `labels_vault_seed_DO_NOT_COMMIT.csv` 等真实标签文件。

仓库中的 `.gitignore` 已覆盖主要运行数据目录，但正式发布前仍应人工检查 `git status`。

## 已知限制

- CNKI 页面结构、按钮选择器和验证流程可能变化，因此采集模块未来可能需要兼容性补丁；
- 自动 PDF 下载受机构权限和页面流程影响，不能保证所有论文都能自动下载；
- 自动 Eligibility 只用于减少明显无效条目，边界条目仍需要研究人员判断；
- 当前程序主要面向本项目的法学期刊抽样设计，不是通用网页爬虫。

## 第三方依赖

项目使用或参考：

- [JYao-Chen/cnki-metadata-exporter](https://github.com/JYao-Chen/cnki-metadata-exporter)：CNKI 原生 XLS 导出、断点续跑、合并和去重；
- [ZhuoerYu/CNKI-Paper-Crawler](https://github.com/ZhuoerYu/CNKI-Paper-Crawler)：PDF 下载控件识别思路参考其公开实现。

第三方许可和固定版本信息见 `THIRD_PARTY_NOTICES.md` 与 `third_party/`。

## License

本项目以 **MIT License** 公开发布。第三方组件继续遵循其各自许可证。

## 版本

当前公开稳定版本：**v1.0**。

版本变化见 `CHANGELOG.md`。
