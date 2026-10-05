# Law Paper Sampling Assistant

**法学论文抽样与自动编号助手 · v0.4.6**  
Author: **Synex1213**
Repository: **https://github.com/Synex1213/law-paper-sampling-assistant**

这是一个面向法学论文 T2 Benchmark / LLM 学术评价实验的数据采样工具。它把“研究范围设计 → CNKI 候选题录采集 → Article Eligibility → 可复现抽样 → 自动编号 → PDF 获取/人工链接兜底”串成一条可审计工作流。

> 本仓库是独立项目，不属于团队主仓库。

## 目标

工具主要解决四个问题：

- 不让采样人员逐篇手工翻 CNKI 决定“哪篇合适”；
- 把候选池、排除规则、抽样顺序和替补顺序固定下来；
- 降低 CNKI 批量采集、登录、分期和编号的人工成本；
- 为后续 PDF → Markdown → 匿名化 → LLM Benchmark 提供稳定上游输入。

## 工作流

```text
选择时期 / Tier / 期刊 / 样本量
        ↓
CNKI 登录
        ↓
并发批量采集候选题录
        ↓
自动匹配 journal × period × tier
        ↓
Article Eligibility 自动初筛
        ↓
人工只处理 UNCERTAIN
        ↓
冻结候选池
        ↓
SHA256 确定性抽样
        ↓
MAIN / HOLDOUT / RESERVE
        ↓
P001 / H001 / R001 自动编号
        ↓
CNKI 链接 + Evidence Queue
        ↓
尝试自动下载 PDF / 人工链接兜底
```

## v0.4.6 主要能力

### 1. 网页化抽样设计

不要求用户先制作复杂的 sampling frame。界面直接设置：

- P1 / P2 / P3 时期；
- T1–T5；
- 每层具体期刊；
- MAIN / RESERVE / HOLDOUT 数量。

当前默认时期为：

```text
P1 = 2018–2020
P2 = 2021–2023
P3 = 2024–2025
```

期刊分层定义保存在 `config/journal_registry.json`，可以独立替换，不需要改抽样引擎。

### 2. CNKI KNS8 候选题录采集

当前专业检索使用：

```text
LY='期刊名'
```

年份不使用旧版 `YE` 字段，而通过 CNKI 页面“发表时间”控件限制。

为提高速度，v0.4.6 支持：

- 1–3 个独立浏览器 profile 并发；
- 按年份切分任务；
- 单期刊也可以拆成多个时间分片并行；
- 已完成批次可续接。

### 3. 登录与采集分离

推荐顺序：

```text
安装 / 修复 CNKI 采集包
→ 打开 CNKI 登录
→ 完成机构/个人登录和必要验证
→ 登录完成
→ 开始信息采集
```

登录资料只保存在本机 `runtime_outputs/cnki_master_profile/`，该目录被 `.gitignore` 排除。

### 4. Article Eligibility

程序自动排除明显非研究论文，例如：

- 书评；
- 访谈；
- 会议纪要；
- 征稿启事；
- 卷首语；
- 新闻；
- 目录；
- 译文等。

边界条目标记为 `UNCERTAIN`，用户只需勾选需要纳入的论文，不需要逐行输入 `include / exclude`。

### 5. 可复现抽样

正式抽样不是临时 `random.choice()`，而是根据固定协议与候选键做确定性 SHA256 排序。

同样的：

```text
sampling frame + candidate pool + seed
```

应得到相同抽样结果。

样本角色分为：

- `MAIN`：正式实验样本；
- `HOLDOUT`：独立保留样本；
- `RESERVE`：预先冻结的替补顺序。

获取失败不能静默换样本，只能按同一 stratum 的 RESERVE 顺序替补。

### 6. 自动编号与下载清单

默认编号：

```text
P001...   MAIN
H001...   HOLDOUT
R001...   RESERVE
```

抽样后自动生成：

- 已选样本表；
- CNKI 页面链接；
- 下载任务；
- Evidence Queue；
- 抽样缺口；
- 可交给后续实验模块的 manifest / labels seed。

### 7. PDF 获取

PDF 自动下载是 best-effort：

- 能直接下载则保存；
- 遇到权限、下载页、页面结构变化等问题时记录失败；
- 不改变抽样结果；
- 始终保留 CNKI 详情页链接，便于采样同学手动下载。

## Windows 快速开始

1. 下载或 clone 本仓库；
2. **完整解压**，不要在 WinRAR 临时目录内运行；
3. 双击：

```text
run_windows.bat
```

首次运行会创建 `.venv` 并安装依赖。程序会自动寻找 7860–7870 之间的空闲本地端口。

## 目录结构

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
third_party/
runtime_outputs/
demo/
```

其中：

- `integrations/`：负责 CNKI 浏览器、登录、原生 XLS 和 PDF；
- `sampling_core/`：负责与 CNKI 无关的采样规则，后续可以直接嵌入 Django/工作台；
- `runtime_outputs/`：本机运行数据，不应提交真实登录资料或样本文件。

## 第三方项目

本项目使用/参考：

- [`JYao-Chen/cnki-metadata-exporter`](https://github.com/JYao-Chen/cnki-metadata-exporter)
  - CNKI 原生 XLS 批量导出、断点续跑、数量核验与合并去重；
  - MIT License；
  - 本仓库保留固定源码快照与许可证说明。
- [`ZhuoerYu/CNKI-Paper-Crawler`](https://github.com/ZhuoerYu/CNKI-Paper-Crawler)
  - PDF 下载控件识别思路参考其公开实现；
  - MIT License。

相关第三方许可见 `third_party/`。

## 科研使用注意

- 工具不会绕过登录、验证码、付费或机构访问控制；
- CNKI 当前标签与论文发表当年的 Tier 是不同变量，不应混用；
- 自动 Eligibility 只负责明显类型，边界论文仍保留人工复核；
- 自动 PDF 获取失败不能成为人工随意换样本的理由；
- 正式研究应保存 sampling seed、candidate pool、抽样结果和 replacement reason。

## 隐私与仓库卫生

不要提交：

- `.venv/`；
- `runtime_outputs/` 中的登录 profile；
- 下载的真实 PDF；
- 私有标签表；
- 机构认证 cookie / session；
- 其他受版权或访问权限限制的数据文件。

## 当前状态

`v0.4.6` 是当前稳定基线。后续对 CNKI 导出稳定性、并发和 PDF 获取的改动建议先在独立测试版本验证，再合并到稳定分支。
