from __future__ import annotations
from collections import defaultdict
import pandas as pd
from .utils import stable_hash, clean

def _issue(rec): return f"{clean(rec.get('year'))}-{clean(rec.get('issue')) or rec['candidate_key'][:8]}"
def _rank(pool,seed,sid):
    groups=defaultdict(list)
    for rec in pool.to_dict("records"):
        x=dict(rec); x["draw_hash"]=stable_hash(seed,sid,x["candidate_key"]); groups[_issue(x)].append(x)
    for k in groups: groups[k].sort(key=lambda r:r["draw_hash"])
    order=sorted(groups,key=lambda k:(groups[k][0]["draw_hash"],k)); ranked=[]; round_i=0
    while True:
        added=False
        for k in order:
            if round_i<len(groups[k]): ranked.append(groups[k][round_i]); added=True
        if not added: break
        round_i+=1
    for i,r in enumerate(ranked,1): r["draw_rank"]=i
    return ranked
def sample(registry,frame,seed="law_sampling_v1",main_prefix="P",hold_prefix="H",reserve_prefix="R",width=3):
    unresolved=registry[(registry["eligibility_status"]=="UNCERTAIN") & (~registry["decision"].isin(["include","exclude"]))]
    if len(unresolved): raise ValueError(f"仍有 {len(unresolved)} 条UNCERTAIN未确认")
    eligible=registry[registry["decision"]=="include"].copy(); used=set(); primary=[]; reserves=[]; issues=[]; ctr={"MAIN":1,"HOLDOUT":1}; pref={"MAIN":main_prefix,"HOLDOUT":hold_prefix}
    for role in ["MAIN","HOLDOUT"]:
        for fr in frame[frame["role"]==role].sort_values("frame_order").to_dict("records"):
            sid=fr["stratum_id"]; target=int(fr["target_n"]); pool=eligible[(eligible["stratum_id"]==sid)&(~eligible["candidate_key"].isin(used))]; chosen=_rank(pool,seed,sid)[:target]
            if len(chosen)<target: issues.append({"stratum_id":sid,"role":role,"requested":target,"selected":len(chosen),"issue":"主样本不足"})
            for rec in chosen:
                x=dict(rec); x["sample_role"]=role; x["paper_id"]=f"{pref[role]}{ctr[role]:0{width}d}"; ctr[role]+=1; primary.append(x); used.add(x["candidate_key"])
    rc=1
    for fr in frame.sort_values("frame_order").to_dict("records"):
        rn=int(fr["reserve_n"]); sid=fr["stratum_id"]
        if rn<=0: continue
        pool=eligible[(eligible["stratum_id"]==sid)&(~eligible["candidate_key"].isin(used))]; chosen=_rank(pool,seed+"|reserve",sid)[:rn]
        for j,rec in enumerate(chosen,1):
            x=dict(rec); x["sample_role"]="RESERVE"; x["paper_id"]=f"{reserve_prefix}{rc:0{max(width,3)}d}"; x["reserve_rank"]=j; x["reserve_for_role"]=fr["role"]; reserves.append(x); used.add(x["candidate_key"]); rc+=1
    return pd.DataFrame(primary),pd.DataFrame(reserves),pd.DataFrame(issues)
