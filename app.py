from __future__ import annotations

import hashlib
import html
import os
import socket
from pathlib import Path

import gradio as gr
import pandas as pd

for key in ("NO_PROXY", "no_proxy"):
    cur = [x.strip() for x in os.environ.get(key, "").split(",") if x.strip()]
    for h in ("localhost", "127.0.0.1"):
        if h not in cur:
            cur.append(h)
    os.environ[key] = ",".join(cur)

from sampling_core import (
    load_registry, build_frame, attach_frame, read_candidates,
    load_rules, classify, sample, make_bundle,
    METHOD_HASH_ISSUE_BALANCED, METHOD_HASH_SIMPLE,
    METHOD_LABELS, METHOD_DESCRIPTIONS, PROTOCOL_VERSION,
)
from integrations.cnki_external import (
    package_status, install_package, collect, request_stop,
    start_login, finish_login, PACKAGE_VERSION, PINNED_COMMIT,
)
from integrations.pdf_downloader import download_selected, request_stop_pdf

ROOT = Path(__file__).resolve().parent
REGISTRY = load_registry(ROOT / "config" / "journal_registry.json")
RULES = load_rules(ROOT / "config" / "eligibility_rules.json")
OUT = ROOT / "runtime_outputs"
OUT.mkdir(exist_ok=True)
TIERS = ["T1", "T2", "T3", "T4", "T5"]


METHOD_CHOICE_TO_ID = {
    METHOD_LABELS[METHOD_HASH_ISSUE_BALANCED]: METHOD_HASH_ISSUE_BALANCED,
    METHOD_LABELS[METHOD_HASH_SIMPLE]: METHOD_HASH_SIMPLE,
}


def sampling_method_help(choice):
    method = METHOD_CHOICE_TO_ID.get(choice, METHOD_HASH_ISSUE_BALANCED)
    desc = METHOD_DESCRIPTIONS[method]
    return (
        "<div class='note'><b>抽样依据：</b>" + html.escape(desc) +
        "<br><b>复现要求：</b>候选池、抽样框、方法和 seed 均不变。抽样完成后会生成 "
        "<code>sampling_protocol.json</code>、<code>sampling_certificate.csv</code> 和完整排序表。</div>"
    )


def sampling_protocol_html(protocol):
    if not protocol:
        return "<div class='note'>完成抽样后，这里会显示本次抽样方法、seed、输入指纹和运行指纹。</div>"
    return (
        "<div class='pluginbox'><b>本次抽样凭证</b><br>"
        f"方法：{html.escape(str(protocol.get('method_label','')))}<br>"
        f"seed：<code>{html.escape(str(protocol.get('seed','')))}</code><br>"
        f"协议版本：<code>{html.escape(str(protocol.get('protocol_version','')))}</code><br>"
        f"Sampling frame SHA256：<code>{html.escape(str(protocol.get('sampling_frame_sha256','')))}</code><br>"
        f"Candidate registry SHA256：<code>{html.escape(str(protocol.get('candidate_registry_sha256','')))}</code><br>"
        f"Run fingerprint：<code>{html.escape(str(protocol.get('run_fingerprint','')))}</code></div>"
    )

CSS = """
:root{--ink:#181d26;--muted:#6b7280;--soft:#f7f8fa;--line:#e6e8ec;--accent:#5e6ad2;}
body{background:#f3f4f6!important}.gradio-container{max-width:1240px!important;margin:0 auto!important;padding:26px!important;background:white!important;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif!important;color:var(--ink)!important}
footer{display:none!important}.hero{padding:4px 0 20px;border-bottom:1px solid var(--line);margin-bottom:20px}.hero h1{font-size:32px!important;margin:0 0 6px!important}.hero p{margin:0!important;color:var(--muted)!important;font-size:15px!important}.sec{margin:26px 0 12px}.sec h2{font-size:23px!important;margin:0 0 4px!important}.sec p{margin:0!important;color:var(--muted)!important;font-size:14px!important}.card{border:1px solid var(--line)!important;border-radius:12px!important;padding:17px!important;background:white!important}.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:10px 0}.kpi{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:white}.kpi .v{font-size:24px;font-weight:650}.kpi .l{font-size:12px;color:var(--muted);margin-top:4px}.note{font-size:12px;color:var(--muted);padding:9px 11px;border:1px solid var(--line);background:var(--soft);border-radius:8px;margin:8px 0}.status-good{color:#157347;font-weight:650}.status-bad{color:#b42318;font-weight:650}.status-warn{color:#9a5b00;font-weight:650}.pluginbox{padding:13px 14px;border:1px solid var(--line);background:#fbfbfc;border-radius:10px}.gradio-container table{font-size:13px!important}.gradio-container th{background:#f8f9fb!important;font-weight:650!important}button.primary{background:#181d26!important;color:white!important;border-color:#181d26!important;min-height:44px!important;border-radius:9px!important;font-weight:650!important}button.secondary{background:white!important;color:#181d26!important;border:1px solid #d7dbe2!important;border-radius:9px!important;min-height:42px!important}button.stop{background:#fff5f4!important;color:#b42318!important;border:1px solid #f3c2bd!important;border-radius:9px!important;min-height:42px!important;font-weight:650!important}button.stop:hover{background:#feeceb!important}.logbox textarea{font-family:ui-monospace,SFMono-Regular,Consolas,monospace!important;font-size:12px!important}.statusbar{border-top:1px solid var(--line);margin-top:30px;padding-top:14px;color:var(--muted);font-size:12px}.linklist{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:10px;padding:8px 14px;background:#fff}.linkrow{padding:9px 2px;border-bottom:1px solid #f0f1f3;font-size:13px}.linkrow:last-child{border-bottom:0}.linkrow a{color:#4f5ac7;text-decoration:none;font-weight:600}.linkrow a:hover{text-decoration:underline}@media(max-width:900px){.kpis{grid-template-columns:1fr 1fr}.gradio-container{padding:14px!important}}
"""


def header():
    return """<div class='hero'><h1>法学论文抽样与自动编号助手</h1><p>从 CNKI 候选题录采集、Eligibility 复核到可复现抽样、编号和下载交付。</p></div>"""


def _all_periods(p1s, p1e, p2s, p2e, p3s, p3e):
    ps = [
        {"id":"P1","start_year":int(p1s),"end_year":int(p1e)},
        {"id":"P2","start_year":int(p2s),"end_year":int(p2e)},
        {"id":"P3","start_year":int(p3s),"end_year":int(p3e)},
    ]
    for p in ps:
        if p["start_year"] > p["end_year"]:
            raise gr.Error(f"{p['id']} 起始年晚于结束年")
    if ps[0]["end_year"] >= ps[1]["start_year"] or ps[1]["end_year"] >= ps[2]["start_year"]:
        raise gr.Error("P1/P2/P3 年份不能重叠")
    return ps


def build_plan(p1s,p1e,p2s,p2e,p3s,p3e,period_choices,tier_choices,t1,t2,t3,t4,t5,main_n,reserve_n,holdout_enabled,holdout_start,holdout_end,holdout_n):
    all_ps = _all_periods(p1s,p1e,p2s,p2e,p3s,p3e)
    chosen_periods = set(period_choices or [])
    ps = [p for p in all_ps if p["id"] in chosen_periods]
    if not ps:
        raise gr.Error("至少选择一个研究时期")
    selected_tiers = list(tier_choices or [])
    if not selected_tiers:
        raise gr.Error("至少选择一个 Tier")
    by = {"T1":t1 or [],"T2":t2 or [],"T3":t3 or [],"T4":t4 or [],"T5":t5 or []}
    selected = []
    for t in selected_tiers:
        selected.extend(by[t])
    selected = list(dict.fromkeys(selected))
    if not selected:
        raise gr.Error("至少选择一本期刊")
    frame = build_frame(REGISTRY,ps,selected_tiers,selected,int(main_n),int(reserve_n),bool(holdout_enabled),int(holdout_start),int(holdout_end),int(holdout_n))
    agg = frame.groupby(["role","tier","period"],as_index=False).agg(期刊数=("journal_family_name","nunique"),目标论文数=("target_n","sum"),备用数=("reserve_n","sum")).rename(columns={"role":"角色","tier":"Tier","period":"时期"})
    html_txt = "<div class='kpis'>" + "".join([
        f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div></div>"
        for v,l in [(len(selected),"已选期刊"),(len(ps),"研究时期"),(int(frame[frame.role=='MAIN'].target_n.sum()),"MAIN目标"),(int(frame[frame.role=='HOLDOUT'].target_n.sum()) if (frame.role=='HOLDOUT').any() else 0,"HOLDOUT目标"),(int(frame.reserve_n.sum()),"备用位")]
    ]) + "</div><div class='note'>抽样框已在后台生成。选择单个三年时期时，采集器也会按年份分片并发，不再强制串行跑完整三年。</div>"
    return frame, html_txt, agg


def status_html():
    st = package_status()
    pkg = "<span class='status-good'>● 采集包已安装</span>" if st["installed"] else "<span class='status-warn'>● 采集包未安装</span>"
    browser = st.get("browser_channel") or "未检测到"
    login = "<span class='status-good'>● 登录资料已保存</span>" if st.get("login_profile_ready") else "<span class='status-warn'>● 尚未保存登录资料</span>"
    if st.get("login_running"):
        login = "<span class='status-warn'>● 登录窗口已打开</span>"
    return f"<div class='pluginbox'>{pkg}　{login}<br><span style='color:#6b7280'>cnki-metadata-exporter {st.get('version') or PACKAGE_VERSION} · commit {PINNED_COMMIT[:8]}… · 浏览器：{browser}</span></div>"


def install_package_ui():
    yield status_html(), "正在检查 CNKI 采集包…"
    try:
        for state in install_package():
            yield status_html(), state.get("log","") + ("\n" if state.get("log") else "") + state.get("message","")
        yield status_html(), "采集包已安装。下一步请先打开 CNKI 登录。"
    except Exception as e:
        yield status_html(), f"安装/修复失败：{e}"


def open_login_ui():
    try:
        msg = start_login()
        return status_html(), msg
    except Exception as e:
        return status_html(), f"打开登录窗口失败：{e}"


def finish_login_ui():
    try:
        msg = finish_login()
        return status_html(), msg
    except Exception as e:
        return status_html(), f"保存登录状态失败：{e}"


def stop_collect_ui():
    msg = request_stop()
    return f"<div class='note'><span class='status-warn'>采集控制：</span>{html.escape(msg)}</div>", msg


def _review_payload(reg):
    u = reg[reg["eligibility_status"] == "UNCERTAIN"][["review_id","title","journal","year","issue","eligibility_reason"]].copy()
    table = u.rename(columns={"review_id":"ID","title":"题名","journal":"期刊","year":"年份","issue":"期号","eligibility_reason":"为什么需要你看"})
    labels = [f"{r.review_id}｜{str(r.title)[:70]}｜{r.journal}｜{r.year}" for r in u.itertuples()]
    return table, labels


def process_path(frame, path):
    cand = read_candidates([str(path)])
    if "year" in cand.columns and len(frame):
        y = pd.to_numeric(cand["year"],errors="coerce")
        lo = int(frame["start_year"].min()); hi = int(frame["end_year"].max())
        cand = cand[y.isna() | ((y >= lo) & (y <= hi))].reset_index(drop=True)
    attached = attach_frame(cand,frame)
    reg = classify(attached,RULES).reset_index(drop=True)
    reg["review_id"] = [f"U{i+1:04d}" for i in range(len(reg))]
    counts = reg["eligibility_status"].value_counts().to_dict()
    summary = "<div class='kpis'>" + "".join(
        f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div></div>"
        for v,l in [(len(cand),"候选论文"),(counts.get("ELIGIBLE_AUTO",0),"自动纳入"),(counts.get("EXCLUDED_AUTO",0),"自动排除"),(counts.get("UNCERTAIN",0),"待复核"),(counts.get("HOLD_METADATA",0),"元数据异常")]
    ) + "</div><div class='note'>人工只需要处理下方边界论文。自动纳入/排除不需要逐篇确认。</div>"
    compact = reg[["title","journal","year","issue","tier","period","eligibility_status","eligibility_reason"]].rename(columns={"title":"题名","journal":"期刊","year":"年份","issue":"期号","tier":"Tier","period":"时期","eligibility_status":"状态","eligibility_reason":"原因"})
    table, labels = _review_payload(reg)
    return reg, summary, compact.head(300), table, labels


def auto_collect_ui(frame, concurrency, year_chunk):
    if frame is None or len(frame) == 0:
        raise gr.Error("请先完成第1步并生成抽样方案")
    st = package_status()
    if not st.get("login_profile_ready"):
        raise gr.Error("请先点击“打开 CNKI 登录”，完成登录后点击“登录完成”，再开始采集。")
    latest_log = []
    try:
        for ev in collect(frame,max_workers=int(concurrency),year_chunk=int(year_chunk)):
            latest_log.append(ev.get("message", ""))
            latest_log = latest_log[-80:]
            if ev.get("done"):
                unique = ev["unique_json"]
                reg, summary, preview, review_table, labels = process_path(frame,unique)
                yield summary, "\n".join(latest_log), preview, review_table, gr.update(choices=labels,value=[]), reg, unique
                return
            yield "<div class='note'>正在并发采集候选题录。已完成批次会保留；如果需要可点击“停止采集”。</div>", "\n".join(latest_log), pd.DataFrame(), pd.DataFrame(), gr.update(choices=[],value=[]), pd.DataFrame(), None
    except Exception as e:
        latest_log.append(f"采集失败/停止：{e}")
        yield "<div class='note'><span class='status-bad'>本次采集没有完成。</span> 已完成的原生XLS批次会保留，可以修复后继续。</div>", "\n".join(latest_log), pd.DataFrame(), pd.DataFrame(), gr.update(), pd.DataFrame(), None


def manual_import_ui(frame, files):
    if frame is None or len(frame)==0: raise gr.Error("请先完成第1步")
    if not files: raise gr.Error("请选择 XLS/JSON/CSV")
    paths=[f if isinstance(f,str) else f.name for f in files]
    cand=read_candidates(paths); attached=attach_frame(cand,frame); reg=classify(attached,RULES).reset_index(drop=True)
    reg["review_id"]=[f"U{i+1:04d}" for i in range(len(reg))]
    counts=reg["eligibility_status"].value_counts().to_dict()
    summary="<div class='kpis'>"+"".join(f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div></div>" for v,l in [(len(cand),"候选论文"),(counts.get("ELIGIBLE_AUTO",0),"自动纳入"),(counts.get("EXCLUDED_AUTO",0),"自动排除"),(counts.get("UNCERTAIN",0),"待复核"),(counts.get("HOLD_METADATA",0),"元数据异常")])+"</div>"
    compact=reg[["title","journal","year","issue","tier","period","eligibility_status","eligibility_reason"]].rename(columns={"title":"题名","journal":"期刊","year":"年份","issue":"期号","tier":"Tier","period":"时期","eligibility_status":"状态","eligibility_reason":"原因"})
    table,labels=_review_payload(reg)
    return reg,summary,compact.head(300),table,gr.update(choices=labels,value=[])


def apply_review_selection(registry, selected_labels, unchecked_policy):
    if registry is None or len(registry)==0:
        raise gr.Error("没有候选库")
    reg=registry.copy()
    selected_ids={str(x).split("｜",1)[0].strip() for x in (selected_labels or [])}
    include_unchecked = (unchecked_policy == "未勾选 = 纳入")
    for i,row in reg.iterrows():
        if row["eligibility_status"] != "UNCERTAIN": continue
        selected = str(row["review_id"]) in selected_ids
        reg.at[i,"decision"] = "include" if (selected or (include_unchecked and not selected)) else "exclude"
    n_inc=int(((reg["eligibility_status"]=="UNCERTAIN") & (reg["decision"]=="include")).sum())
    n_exc=int(((reg["eligibility_status"]=="UNCERTAIN") & (reg["decision"]=="exclude")).sum())
    return reg, f"<div class='note'>边界论文已确认：纳入 <b>{n_inc}</b> 篇，排除 <b>{n_exc}</b> 篇。</div>"


def set_all_review(registry, decision):
    if registry is None or len(registry)==0: raise gr.Error("没有候选库")
    reg=registry.copy(); mask=reg["eligibility_status"]=="UNCERTAIN"; reg.loc[mask,"decision"]=decision
    return reg, f"<div class='note'>全部 UNCERTAIN 已设为 <b>{decision}</b>。</div>"


def link_html(primary):
    if primary is None or primary.empty:
        return "<div class='note'>没有可用链接。</div>"
    rows=[]
    for r in primary.to_dict("records"):
        url=str(r.get("url","")).strip(); pid=str(r.get("paper_id","")); title=html.escape(str(r.get("title",""))); meta=html.escape(f"{r.get('journal','')} · {r.get('year','')} · {r.get('tier','')}")
        if url.startswith("http"):
            rows.append(f"<div class='linkrow'><b>{html.escape(pid)}</b>　{title}<br><span style='color:#6b7280'>{meta}</span>　<a href='{html.escape(url,quote=True)}' target='_blank'>打开 CNKI 页面 ↗</a></div>")
        else:
            rows.append(f"<div class='linkrow'><b>{html.escape(pid)}</b>　{title}<br><span style='color:#b42318'>候选元数据中没有详情页URL；请按题名检索。</span></div>")
    return "<div class='linklist'>"+"".join(rows)+"</div>"


def run_sample(frame, registry, method_choice, seed, width):
    if registry is None or len(registry) == 0:
        raise gr.Error("请先完成第2步")
    reg = registry.copy()
    unresolved = reg[(reg["eligibility_status"] == "UNCERTAIN") & (~reg["decision"].isin(["include","exclude"]))]
    if len(unresolved):
        raise gr.Error(f"还有 {len(unresolved)} 条边界论文未确认。请在第2步用勾选方式处理。")

    method = METHOD_CHOICE_TO_ID.get(method_choice, METHOD_HASH_ISSUE_BALANCED)
    seed_value = str(seed or "law_sampling_v1").strip() or "law_sampling_v1"
    primary, reserve, issues, audit = sample(
        reg, frame, seed=seed_value, method=method, width=int(width)
    )
    protocol = {
        "protocol_version": PROTOCOL_VERSION,
        "method": method,
        "method_label": METHOD_LABELS[method],
        "description": METHOD_DESCRIPTIONS[method],
        "seed": seed_value,
        "reserve_seed": seed_value + "|reserve",
        "hash_formula": "SHA256(seed | stratum_id | candidate_key)",
    }
    zpath = OUT / "sampling_result_bundle.zip"
    (
        download, evidence, z, protocol_file, certificate_file, ranking_file,
        protocol_final, certificate
    ) = make_bundle(
        frame, reg, primary, reserve, issues, zpath, audit=audit, protocol=protocol
    )

    main = primary[primary["sample_role"] == "MAIN"] if not primary.empty else pd.DataFrame()
    hold = primary[primary["sample_role"] == "HOLDOUT"] if not primary.empty else pd.DataFrame()
    short_fp = str(protocol_final.get("run_fingerprint", ""))[:16]
    summary = "<div class='kpis'>" + "".join([
        f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div></div>"
        for v,l in [
            (len(main),"MAIN"),(len(hold),"HOLDOUT"),(len(reserve),"RESERVE"),
            (len(download),"待获取PDF"),(len(evidence[evidence.required==1]) if not evidence.empty else 0,"需人工留证")
        ]
    ]) + (
        "</div><div class='note'><b>抽样方法：</b>" + html.escape(METHOD_LABELS[method]) +
        "　<b>seed：</b><code>" + html.escape(seed_value) + "</code>" +
        "　<b>运行指纹：</b><code>" + html.escape(short_fp) + "…</code><br>" +
        "结果包中已保存抽样协议、逐样本凭证和完整排序，可据此复算。" +
        " PDF自动下载失败不会改变样本，CNKI网页链接始终保留。</div>"
    )

    selected = primary[["paper_id","sample_role","tier","period","journal","year","issue","title"]].rename(
        columns={"paper_id":"编号","sample_role":"角色","tier":"Tier","period":"时期","journal":"期刊","year":"年份","issue":"期号","title":"题名"}
    ) if not primary.empty else pd.DataFrame()
    if not download.empty:
        d = download[["paper_id","role","tier","period","journal","year","issue","title","cnki_url","download_status"]].rename(
            columns={"paper_id":"编号","role":"角色","tier":"Tier","period":"时期","journal":"期刊","year":"年份","issue":"期号","title":"题名","cnki_url":"CNKI链接","download_status":"状态"}
        )
    else:
        d = download
    e = evidence[["task_id","type","required","status","page","screenshot_name","what_to_capture"]].rename(
        columns={"task_id":"任务","type":"证据类型","required":"必须人工","status":"状态","page":"打开页面","screenshot_name":"截图文件名","what_to_capture":"截图要求"}
    ) if not evidence.empty else evidence
    cert_view = certificate.rename(columns={
        "paper_id":"编号","sample_role":"角色","stratum_id":"抽样格","journal":"期刊",
        "year":"年份","issue":"期号","title":"题名","draw_hash":"抽样哈希",
        "draw_rank":"格内顺位","stratum_pool_size":"候选池大小","sampling_method":"方法",
        "sampling_seed":"seed","run_fingerprint":"运行指纹"
    }) if not certificate.empty else certificate

    return (
        primary, summary, selected, d, _links_html(primary), e, issues, z,
        sampling_protocol_html(protocol_final), cert_view, protocol_file, certificate_file, ranking_file
    )


def auto_download_pdfs_ui(primary):
    if primary is None or len(primary)==0:
        raise gr.Error("请先完成抽样")
    try:
        rows, zip_path = download_selected(primary,OUT/"selected_pdfs")
    except Exception as e:
        return f"<div class='note'><span class='status-bad'>PDF自动下载未启动：</span>{html.escape(str(e))}<br>可直接使用上方 CNKI 页面链接手动下载。</div>", pd.DataFrame(), None
    df = pd.DataFrame(rows)
    status_path = OUT / "pdf_download_status.csv"
    df.to_csv(status_path,index=False,encoding="utf-8-sig")
    ok = int((df["pdf_file"].fillna("") != "").sum()) if not df.empty else 0
    fail = len(df) - ok
    summary = f"<div class='note'><span class='status-good'>PDF自动下载完成：</span>成功 {ok} 篇，未自动获取 {fail} 篇。未成功的样本请使用 CNKI 链接手动打开，不会改变抽样结果。</div>"
    view = df.rename(columns={"paper_id":"编号","title":"题名","cnki_url":"CNKI链接","pdf_file":"PDF文件","status":"状态"})
    return summary, view, str(status_path)


def stop_pdf_ui():
    return request_stop_pdf()


def make_app():
    with gr.Blocks(title="法学论文抽样与自动编号助手 v1.0") as demo:
        gr.HTML(header())
        frame_state = gr.State(pd.DataFrame())
        registry_state = gr.State(pd.DataFrame())
        primary_state = gr.State(pd.DataFrame())

        gr.HTML("<div class='sec'><h2>1. 设计抽样范围</h2><p>直接选择参与时期、Tier 和期刊；程序在后台生成抽样框。</p></div>")
        with gr.Group(elem_classes="card"):
            period_choices = gr.CheckboxGroup(["P1","P2","P3"],value=["P1","P2","P3"],label="参与时期")
            with gr.Row():
                with gr.Column(): gr.Markdown("**P1**"); p1s=gr.Number(2018,label="起始年",precision=0); p1e=gr.Number(2020,label="结束年",precision=0)
                with gr.Column(): gr.Markdown("**P2**"); p2s=gr.Number(2021,label="起始年",precision=0); p2e=gr.Number(2023,label="结束年",precision=0)
                with gr.Column(): gr.Markdown("**P3**"); p3s=gr.Number(2024,label="起始年",precision=0); p3e=gr.Number(2025,label="结束年",precision=0)
            tier_choices=gr.CheckboxGroup(TIERS,value=TIERS,label="参与Tier")
            with gr.Accordion("T1 · 3刊",open=True): t1=gr.CheckboxGroup(REGISTRY["tiers"]["T1"],value=REGISTRY["tiers"]["T1"],label="T1期刊")
            with gr.Accordion("T2 · 13刊",open=True): t2=gr.CheckboxGroup(REGISTRY["tiers"]["T2"],value=REGISTRY["tiers"]["T2"],label="T2期刊")
            with gr.Accordion("T3 · 4刊",open=False): t3=gr.CheckboxGroup(REGISTRY["tiers"]["T3"],value=REGISTRY["tiers"]["T3"],label="T3期刊")
            with gr.Accordion("T4 · 22刊",open=False): t4=gr.CheckboxGroup(REGISTRY["tiers"]["T4"],value=REGISTRY["tiers"]["T4"],label="T4期刊")
            with gr.Accordion("T5 · 8刊",open=False): t5=gr.CheckboxGroup(REGISTRY["tiers"]["T5"],value=REGISTRY["tiers"]["T5"],label="T5期刊")
            with gr.Row(): main_n=gr.Number(1,label="MAIN/期刊×时期",precision=0); reserve_n=gr.Number(1,label="RESERVE/格",precision=0); holdout_enabled=gr.Checkbox(True,label="启用HOLDOUT"); holdout_n=gr.Number(1,label="HOLDOUT/刊",precision=0)
            with gr.Row(): holdout_start=gr.Number(2024,label="HOLDOUT起始年",precision=0); holdout_end=gr.Number(2025,label="HOLDOUT结束年",precision=0)
            build_btn=gr.Button("生成抽样方案",variant="primary",elem_classes="primary")
        plan_summary=gr.HTML(); plan_preview=gr.Dataframe(label="方案摘要",interactive=False,wrap=True)
        build_btn.click(build_plan,inputs=[p1s,p1e,p2s,p2e,p3s,p3e,period_choices,tier_choices,t1,t2,t3,t4,t5,main_n,reserve_n,holdout_enabled,holdout_start,holdout_end,holdout_n],outputs=[frame_state,plan_summary,plan_preview])

        gr.HTML("<div class='sec'><h2>2. 登录并采集 CNKI 候选题录</h2><p>先登录一次，再并发采集。并发采用独立浏览器资料副本，避免多个窗口共用同一个“已选文献”状态。</p></div>")
        with gr.Group(elem_classes="card"):
            plugin_state=gr.HTML(status_html())
            with gr.Row():
                install_btn=gr.Button("1｜安装 / 修复采集包",elem_classes="secondary")
                login_btn=gr.Button("2｜打开 CNKI 登录",elem_classes="secondary")
                login_done_btn=gr.Button("登录完成",elem_classes="secondary")
            login_message=gr.Textbox(label="登录状态",lines=2,interactive=False)
            with gr.Row():
                concurrency=gr.Slider(1,3,value=2,step=1,label="并发采集窗口数（建议2）")
                year_chunk=gr.Radio([1,2,3],value=2,label="年份分片（每个采集任务包含几年）")
            gr.HTML("<div class='note'>例：只选 P1=2018–2020 + 一本期刊，分片=2 会拆成 2018–2019 和 2020 两个任务，可由 2 个窗口同时采。并发超过 3 不建议，容易触发额外验证。</div>")
            with gr.Row():
                collect_btn=gr.Button("3｜开始信息采集",variant="primary",elem_classes="primary")
                stop_btn=gr.Button("停止采集",elem_classes="stop")
            plugin_log=gr.Textbox(label="采集/安装日志",lines=9,interactive=False,elem_classes="logbox")
            unique_file=gr.File(label="本次自动生成的 unique.json（留档）")
        install_btn.click(install_package_ui,outputs=[plugin_state,plugin_log])
        login_btn.click(open_login_ui,outputs=[plugin_state,login_message],queue=False)
        login_done_btn.click(finish_login_ui,outputs=[plugin_state,login_message],queue=False)

        candidate_summary=gr.HTML(); candidate_preview=gr.Dataframe(label="候选库概览",interactive=False,wrap=True)
        uncertain_table=gr.Dataframe(label="边界论文（只读）",interactive=False,wrap=True)
        uncertain_choices=gr.CheckboxGroup([],label="勾选要纳入的边界论文",info="不用输入 include/exclude。只勾你认为应该纳入的论文。")
        with gr.Row():
            unchecked_policy=gr.Radio(["未勾选 = 排除","未勾选 = 纳入"],value="未勾选 = 排除",label="未勾选项如何处理")
            apply_review_btn=gr.Button("应用勾选结果",elem_classes="secondary")
            all_include_btn=gr.Button("全部纳入",elem_classes="secondary")
            all_exclude_btn=gr.Button("全部排除",elem_classes="secondary")
        review_status=gr.HTML()

        collect_btn.click(auto_collect_ui,inputs=[frame_state,concurrency,year_chunk],outputs=[candidate_summary,plugin_log,candidate_preview,uncertain_table,uncertain_choices,registry_state,unique_file],concurrency_limit=1)
        stop_btn.click(stop_collect_ui,outputs=[candidate_summary,plugin_log],queue=False)
        apply_review_btn.click(apply_review_selection,inputs=[registry_state,uncertain_choices,unchecked_policy],outputs=[registry_state,review_status])
        all_include_btn.click(lambda r:set_all_review(r,"include"),inputs=[registry_state],outputs=[registry_state,review_status])
        all_exclude_btn.click(lambda r:set_all_review(r,"exclude"),inputs=[registry_state],outputs=[registry_state,review_status])

        with gr.Accordion("高级 / 备用：已有 CNKI XLS、JSON、CSV 时手动导入",open=False):
            manual_files=gr.File(label="候选元数据",file_count="multiple",file_types=[".json",".csv",".xls",".xlsx"],type="filepath")
            manual_btn=gr.Button("导入已有元数据",elem_classes="secondary")
            manual_btn.click(manual_import_ui,inputs=[frame_state,manual_files],outputs=[registry_state,candidate_summary,candidate_preview,uncertain_table,uncertain_choices])

        gr.HTML("<div class='sec'><h2>3. 冻结候选池并自动编号</h2><p>先明确抽样方法和 seed，再冻结候选池。系统会同时生成可复现的抽样协议、排序记录和逐样本凭证。</p></div>")
        with gr.Group(elem_classes="card"):
            method_choice=gr.Radio(
                [METHOD_LABELS[METHOD_HASH_ISSUE_BALANCED], METHOD_LABELS[METHOD_HASH_SIMPLE]],
                value=METHOD_LABELS[METHOD_HASH_ISSUE_BALANCED],
                label="抽样方法"
            )
            method_help=gr.HTML(sampling_method_help(METHOD_LABELS[METHOD_HASH_ISSUE_BALANCED]))
            with gr.Row():
                seed=gr.Textbox("law_sampling_v1",label="抽样 seed",info="相同候选池 + 相同方法 + 相同 seed，应得到相同抽样结果")
                width=gr.Number(3,label="编号位数",precision=0)
            sample_btn=gr.Button("冻结并抽样",variant="primary",elem_classes="primary")
        method_choice.change(sampling_method_help,inputs=[method_choice],outputs=[method_help],queue=False)
        sample_summary=gr.HTML()
        with gr.Tabs():
            with gr.Tab("已选样本"): selected=gr.Dataframe(interactive=False,wrap=True)
            with gr.Tab("抽样凭证"):
                protocol_view=gr.HTML("<div class='note'>完成抽样后，这里会显示复现凭证。</div>")
                certificate_view=gr.Dataframe(label="逐样本抽样凭证",interactive=False,wrap=True)
                with gr.Row():
                    protocol_file=gr.File(label="sampling_protocol.json")
                    certificate_file=gr.File(label="sampling_certificate.csv")
                    ranking_file=gr.File(label="sampling_ranking_full.csv")
            with gr.Tab("下载任务"):
                downloads=gr.Dataframe(interactive=False,wrap=True)
                link_list=gr.HTML("<div class='note'>抽样后这里会生成 CNKI 页面链接。</div>")
            with gr.Tab("证据任务"): evidence=gr.Dataframe(interactive=False,wrap=True)
            with gr.Tab("抽样缺口"): issues=gr.Dataframe(interactive=False,wrap=True)
        result_zip=gr.File(label="完整结果包")
        sample_btn.click(
            run_sample,
            inputs=[frame_state,registry_state,method_choice,seed,width],
            outputs=[
                primary_state,sample_summary,selected,downloads,link_list,evidence,issues,result_zip,
                protocol_view,certificate_view,protocol_file,certificate_file,ranking_file
            ]
        )

        gr.HTML("<div class='sec'><h2>4. 获取入选样本 PDF</h2><p>先尝试使用已登录的 CNKI 浏览器自动下载；无法自动取得的样本继续保留网页链接，由采集同学手动下载。</p></div>")
        with gr.Group(elem_classes="card"):
            with gr.Row():
                pdf_btn=gr.Button("尝试自动下载入选 PDF（实验性）",variant="primary",elem_classes="primary")
                pdf_stop_btn=gr.Button("停止 PDF 下载",elem_classes="stop")
            pdf_summary=gr.HTML()
            pdf_status=gr.Dataframe(label="PDF下载结果",interactive=False,wrap=True)
            pdf_status_file=gr.File(label="PDF下载状态 CSV")
        pdf_btn.click(auto_download_pdfs_ui,inputs=[primary_state],outputs=[pdf_summary,pdf_status,pdf_status_file],concurrency_limit=1)
        pdf_stop_btn.click(stop_pdf_ui,outputs=[login_message],queue=False)

        gr.HTML(f"<div class='statusbar'>采集包：cnki-metadata-exporter {PACKAGE_VERSION} · commit {PINNED_COMMIT[:8]}…｜KNS8：LY + 页面发表时间｜并发上限3｜登录/验证码由用户完成，不绕过访问控制｜Author: Synex1213。</div>")
        demo.load(status_html,outputs=[plugin_state])
    return demo


def find_free_port(start=7860,end=7870):
    for port in range(start,end+1):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            try:
                s.bind(("127.0.0.1",port)); return port
            except OSError:
                continue
    raise OSError("7860–7870 都被占用，请关闭旧版 Sampling Assistant 后重试。")


if __name__ == "__main__":
    port=find_free_port()
    print(f"\n[Sampling Assistant] 启动端口：{port}")
    if port!=7860:
        print(f"[Sampling Assistant] 7860 已被占用，已自动切换到 {port}。")
    print(f"[Sampling Assistant] 本地地址：http://127.0.0.1:{port}\n")
    make_app().launch(server_name="127.0.0.1",server_port=port,inbrowser=True,show_error=True,theme=gr.themes.Base(),css=CSS)
