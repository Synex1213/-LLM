# v1.0 最小测试清单

建议先用一个小范围验证，不要直接跑 50 刊。

## A. CNKI 登录

1. 打开软件；
2. 点击“打开 CNKI 登录”；
3. 完成机构/个人登录；
4. 点击“登录完成”；
5. 页面应显示登录资料已保存。

## B. 小规模采集

建议：

```text
P1
法学研究
MAIN=1
RESERVE=1
并发=2
年份分片=2
```

预期：

- 能提交 `LY='法学研究'`；
- 页面发表时间正确写入；
- 检索按钮真实执行；
- 当前页全选若第一次未生效，会自动重试；
- XLS 正常落盘；
- 最终生成 `unique.json`。

## C. Eligibility

确认 UNCERTAIN 论文通过勾选完成纳入/排除，不需要手输 include/exclude。

## D. 抽样复现

先选：

```text
确定性哈希 + 期号均衡（推荐）
seed = law_sampling_v1
```

抽样一次，保存：

- `sampling_protocol.json`；
- `sampling_certificate.csv`；
- `sampling_ranking_full.csv`；
- `sampling_result_bundle.zip`。

然后在候选池不变的情况下再次使用同一方法和 seed，确认最终 `paper_id + candidate_key + draw_hash + draw_rank` 一致。

再更换 seed，确认排序/样本发生变化。

## E. 第二种抽样方法

改为“确定性哈希直接排序”，确认：

- 方法字段改变；
- run fingerprint 改变；
- 同一方法+同一seed重复执行仍可复现。

## F. PDF

最后再测自动 PDF 下载。自动失败不应修改已经冻结的样本。
