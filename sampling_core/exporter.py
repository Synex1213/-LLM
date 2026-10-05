from __future__ import annotations
import tempfile, zipfile
from pathlib import Path
import pandas as pd
from .utils import parse_cnki

def _write(df,path): df.to_csv(path,index=False,encoding="utf-8-sig")
def result_tables(primary,reserve):
    download=[]; evidence=[]
    for rec in primary.to_dict("records"):
        ids=parse_cnki(rec.get("url",""),rec.get("cnki_filename",""),rec.get("cnki_dbcode",""))
        download.append({"paper_id":rec.get("paper_id",""),"role":rec.get("sample_role",""),"tier":rec.get("tier",""),"period":rec.get("period",""),"journal":rec.get("journal",""),"year":rec.get("year",""),"issue":rec.get("issue",""),"title":rec.get("title",""),"cnki_url":rec.get("url",""),"doi":rec.get("doi",""),"cnki_record_key":ids["cnki_record_key"],"download_status":"待下载"})
        need=1 if ids["record_key_method"] in {"missing","url_hash"} else 0
        evidence.append({"task_id":f"{rec.get('paper_id','')}-A","paper_id":rec.get("paper_id",""),"type":"论文题录","required":need,"status":"待处理" if need else "自动信息已足够","page":rec.get("url","") or f"精确检索：{rec.get('title','')}","screenshot_name":f"{rec.get('paper_id','')}_A_article_record.png" if need else "—","what_to_capture":"题名 + 作者 + 期刊/来源 + 年份/期号；尽量保留地址栏" if need else "无需截图"})
    if not primary.empty:
        for i,rec in primary[["journal_family_name","journal"]].drop_duplicates().reset_index(drop=True).iterrows():
            evidence.append({"task_id":f"J{i+1:03d}-B","paper_id":"—","type":"期刊当前标签","required":1,"status":"待处理","page":f"打开《{rec['journal']}》CNKI期刊/来源页","screenshot_name":f"J{i+1:03d}_B_journal_tags.png","what_to_capture":"期刊名称 + CNKI当前展示标签；同一期刊只截一次"})
    return pd.DataFrame(download),pd.DataFrame(evidence)
def make_bundle(frame,registry,primary,reserve,issues,out_path):
    out_path=Path(out_path); download,evidence=result_tables(primary,reserve)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _write(frame,root/"sampling_frame.csv"); _write(registry,root/"candidate_registry.csv"); _write(primary,root/"selected_samples.csv"); _write(reserve,root/"reserve_samples.csv"); _write(issues,root/"sampling_issues.csv"); _write(download,root/"download_queue.csv"); _write(evidence,root/"evidence_queue.csv")
        safe=pd.DataFrame([{"paper_id":r.get("paper_id",""),"version_stage":"T2","readiness_status":"pending","notes":"PDF保留原文件名，后续自动绑定"} for r in primary.to_dict("records")]); labels=pd.DataFrame([{"paper_id":r.get("paper_id",""),"true_journal_name":r.get("journal",""),"journal_family_name":r.get("journal_family_name",""),"publication_year":r.get("year",""),"period":r.get("period",""),"true_tier":r.get("tier",""),"true_title":r.get("title",""),"true_author":r.get("authors","")} for r in primary.to_dict("records")]); _write(safe,root/"safe_sample_manifest.csv"); _write(labels,root/"labels_vault_seed_DO_NOT_COMMIT.csv")
        (root/"README_NEXT.txt").write_text("只下载download_queue中的正式样本/HOLDOUT PDF；PDF不要改名。按evidence_queue只补required=1的证据。",encoding="utf-8")
        with zipfile.ZipFile(out_path,"w",zipfile.ZIP_DEFLATED) as z:
            for p in root.rglob("*"):
                if p.is_file(): z.write(p,p.relative_to(root))
    return download,evidence,str(out_path)
