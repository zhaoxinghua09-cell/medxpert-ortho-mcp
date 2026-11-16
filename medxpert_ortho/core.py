#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具实现层：8 个工具，全部离线、确定性、零第三方依赖。

数据从 datasets/ 读取；设置环境变量 ORTHO_DATA_DIR 可整体替换为你自己的目录
（同名 JSON 文件，字段结构见 README）。任何返回值都带 `sample_data: true`，
除非数据目录被替换过——这样调用方一眼能看出结论建立在示例数据还是自有数据上。
"""
import datetime
import json
import os

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

# 每个数据集文件的必需顶层键。缺键会在加载时就失败，而不是等到某个工具
# 在深处抛 KeyError——那种失败看起来像"工具坏了"，实际是数据不合规。
REQUIRED_KEYS = {
    "labs.json": ("labs",),
    "quotes.json": ("quotes",),
    "udi.json": ("entries",),
    "standards.json": ("standards",),
    "judgment_trees.json": ("trees",),
    "timelines.json": ("regions", "timelines"),
}


class DataError(ValueError):
    """数据不可用。错误信息必须写明文件与路径，否则调用方无从修。"""


def custom_dir():
    """返回 ORTHO_DATA_DIR。设了却不可用就报错——绝不静默退回示例数据。"""
    raw = os.environ.get("ORTHO_DATA_DIR", "").strip()
    if not raw:
        return ""
    path = os.path.abspath(os.path.expanduser(raw))
    if not os.path.isdir(path):
        raise DataError("ORTHO_DATA_DIR 指向的目录不存在：%s（不会静默退回示例数据）" % path)
    return path


def data_dir():
    return custom_dir() or DATASET_DIR


def is_sample():
    return not custom_dir()


def load(name):
    path = os.path.join(data_dir(), name)
    if not os.path.exists(path):
        raise DataError("数据集文件缺失：%s（当前数据目录 %s）" % (path, data_dir()))
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataError("数据集不是合法 JSON：%s（第 %d 行第 %d 列：%s）"
                        % (path, e.lineno, e.colno, e.msg))
    if not isinstance(data, dict):
        raise DataError("数据集顶层必须是对象：%s（实际是 %s）" % (path, type(data).__name__))
    missing = [k for k in REQUIRED_KEYS.get(name, ()) if k not in data]
    if missing:
        raise DataError("数据集缺少顶层键 %s：%s（期望含 %s）"
                        % (missing, path, list(REQUIRED_KEYS.get(name, ()))))
    return data


def validate_data():
    """把数据目录整体体检一遍，返回结构化报告。

    存在理由是上一版的一个静默失败：数据放错位置时，工具照常给出示例结论。
    """
    report = {"data_dir": None, "sample_data": None, "ok": True, "files": [], "cross_checks": []}

    def issue(code, message):
        report["ok"] = False
        report["files"].append({"code": code, "message": message})

    try:
        report["data_dir"] = data_dir()
        report["sample_data"] = is_sample()
    except DataError as e:
        issue("data_dir", str(e))
        return report

    loaded = {}
    for fname, keys in REQUIRED_KEYS.items():
        try:
            loaded[fname] = load(fname)
            report["files"].append({"file": fname, "ok": True, "keys": list(keys)})
        except DataError as e:
            issue("load:" + fname, str(e))

    if not report["ok"]:
        return report

    labs = [l for l in loaded["labs.json"]["labs"] if isinstance(l, dict) and l.get("id")]
    lab_ids = {l["id"] for l in labs}
    bad_lab = [l for l in loaded["labs.json"]["labs"] if not (isinstance(l, dict) and l.get("id"))]
    if bad_lab:
        issue("labs:shape", "labs.json 有 %d 条机构缺少 id" % len(bad_lab))

    orphan_quotes = sorted({q["lab_id"] for q in loaded["quotes.json"]["quotes"]
                            if q.get("lab_id") not in lab_ids})
    if orphan_quotes:
        issue("quotes:orphan", "quotes.json 引用了 labs.json 里不存在的机构：%s" % orphan_quotes)

    bad_udi = [e for e in loaded["udi.json"]["entries"]
               if not (str(e.get("udi_di", "")).isdigit() and len(str(e.get("udi_di"))) == 14)]
    if bad_udi:
        issue("udi:format", "udi.json 有 %d 条不是 14 位数字 UDI-DI" % len(bad_udi))

    bad_status = [s.get("code") for s in loaded["standards.json"]["standards"]
                  if s.get("status") not in ("current", "superseded")]
    if bad_status:
        issue("standards:status", "standards.json 的 status 只接受 current/superseded：%s" % bad_status)

    region_codes = {r["code"] for r in loaded["timelines.json"]["regions"] if r.get("code")}
    for tl in loaded["timelines.json"]["timelines"]:
        if not tl.get("phases"):
            issue("timelines:phases", "时间轴 %s 没有 phases" % tl.get("procedure"))
        for ph in tl.get("phases") or []:
            if not isinstance(ph.get("offset_days"), int) or not isinstance(ph.get("duration_days"), int):
                issue("timelines:phase_shape",
                      "%s 的阶段 %s 的 offset_days/duration_days 必须是整数"
                      % (tl.get("procedure"), ph.get("name")))
        if not tl.get("required_documents"):
            issue("timelines:docs", "时间轴 %s 没有 required_documents" % tl.get("procedure"))

    report["cross_checks"] = [
        {"check": "quotes.lab_id ⊆ labs.id", "ok": not orphan_quotes},
        {"check": "udi_di 均 14 位数字", "ok": not bad_udi},
        {"check": "standards.status 枚举", "ok": not bad_status},
        {"check": "timelines 阶段与要件齐备", "ok": report["ok"]},
        {"check": "regions 编码可用", "ok": bool(region_codes)},
    ]
    if not region_codes:
        issue("regions:empty", "timelines.json 的 regions 为空")
    return report


def _norm(s):
    return (s or "").strip().lower()


def _today(day=None):
    if day:
        return datetime.date.fromisoformat(day)
    return datetime.date.today()


# ---------- 1. match_labs ----------
def match_labs(scope_keyword=None, region=None, device=None, limit=5):
    """按能力关键词 / 地区 / 器械描述给机构打分排序。"""
    labs = load("labs.json")["labs"]
    kw = _norm(scope_keyword)
    dev = _norm(device)
    reg = _norm(region)

    scored = []
    for lab in labs:
        score = 0
        hits = []
        for cap in lab.get("scope", []):
            c = _norm(cap)
            if kw and (kw in c or c in kw):
                score += 30
                hits.append(cap)
            if dev and (dev in c or c in dev):
                score += 12
                hits.append(cap)
        if reg and _norm(lab.get("region")) != reg:
            score -= 8
        if reg and _norm(lab.get("region")) == reg:
            score += 10
        if score > 0:
            scored.append((score, lab, sorted(set(hits))))
    scored.sort(key=lambda t: (-t[0], t[1]["id"]))
    out = [{"id": lab["id"], "name": lab["name"], "region": lab["region"],
            "matched_scope": hits, "score": score,
            "accreditation": lab.get("accreditation", []),
            "contact": lab.get("contact")}
           for score, lab, hits in scored[:max(1, int(limit or 5))]]
    if not out:
        return {"matches": [], "hint": "无机构命中该关键词；示例数据仅覆盖 3 家机构的少数能力项。",
                "sample_data": is_sample()}
    return {"matches": out, "count": len(out), "sample_data": is_sample()}


# ---------- 2. calc_quote ----------
def calc_quote(lab_id, scope, quantity=1):
    """按机构与能力项取示例报价区间，并按数量给出估算总额区间。"""
    q = load("quotes.json")
    qty = max(1, int(quantity or 1))
    rows = [r for r in q["quotes"]
            if _norm(r["lab_id"]) == _norm(lab_id) and (scope or "").strip() in r["scope"]]
    if not rows:
        raise ValueError("该机构在示例数据中没有此能力项的报价：%s / %s" % (lab_id, scope))
    r = rows[0]
    over = max(0, qty - int(r.get("included_samples", 0)))
    factor = 1 + 0.12 * over            # 超出含样量的加价率，示例规则
    return {"lab_id": r["lab_id"], "scope": r["scope"], "quantity": qty,
            "unit_price_range": {"low": r["low"], "high": r["high"]},
            "estimated_total_range": {"low": round(r["low"] * factor),
                                      "high": round(r["high"] * factor)},
            "currency": q.get("currency", "CNY"),
            "lead_time_days": r["lead_time_days"],
            "pricing_rule": "含 %d 个样；每超 1 个加价 12%%（示例规则）" % r.get("included_samples", 0),
            "sample_data": is_sample()}


# ---------- 3. check_udi ----------
def check_udi(udi_di):
    """校验 UDI-DI：命中的条目回出分类与一次性/无菌属性，未命中给可操作提示。"""
    key = (udi_di or "").strip()
    if not key:
        raise ValueError("udi_di 必填")
    entries = load("udi.json")["entries"]
    for e in entries:
        if e["udi_di"] == key:
            return {"found": True, "entry": e, "sample_data": is_sample()}
    near = [e["udi_di"] for e in entries if e["udi_di"].startswith(key[:8])]
    return {"found": False,
            "hint": "示例数据仅含 %d 条虚构 UDI-DI；未命中不代表真实 UDI 数据库无此编号。" % len(entries),
            "same_prefix": near[:5],
            "format_ok": key.isdigit() and len(key) == 14,
            "sample_data": is_sample()}


# ---------- 4. query_standard ----------
def query_standard(keyword, as_of=None):
    """查标准，支持双时态：按 as_of 判断某日是否已生效、是否已被替代。"""
    kw = (keyword or "").strip()
    if not kw:
        raise ValueError("keyword 必填")
    day = _today(as_of) if as_of else None
    rows = []
    for s in load("standards.json")["standards"]:
        hay = (s["code"] + " " + s["title"] + " " + s.get("family", "")).lower()
        if kw.lower() in hay:
            item = dict(s)
            if day:
                eff = s.get("effective_date")
                item["in_force_on_as_of"] = bool(eff and datetime.date.fromisoformat(eff) <= day)
                item["superseded_on_as_of"] = bool(
                    s.get("superseded_by") and s.get("status") == "superseded")
            rows.append(item)
    return {"query": kw, "as_of": day.isoformat() if day else "current-view",
            "matches": rows, "count": len(rows),
            "rule": "as_of 早于 effective_date 时 in_force_on_as_of=false——版本判定必须带时间轴。",
            "sample_data": is_sample()}


# ---------- 5. find_judgment_tree ----------
def find_judgment_tree(procedure=None, region="CN"):
    """取判定树：按程序名与地区模糊匹配，返回逐步问答结构。"""
    trees = load("judgment_trees.json")["trees"]
    p = _norm(procedure)
    cands = [t for t in trees if not p or p in _norm(t["procedure"]) or _norm(t["procedure"]) in p]
    if not cands:
        return {"tree": None, "available": [t["procedure"] for t in trees],
                "sample_data": is_sample()}
    t = cands[0]
    return {"tree": t, "note": "判定树是演示结构；最终分类以分类目录与界定结论为准。",
            "sample_data": is_sample()}


# ---------- 6. get_region_path ----------
def get_region_path(region, procedure=None):
    """取地区路径：受理机关、路径说明、该程序在该地区的必备材料清单。"""
    d = load("timelines.json")
    r = (region or "CN").strip()
    hit = [x for x in d["regions"] if _norm(x["code"]) == _norm(r)]
    tl = [t for t in d["timelines"] if not procedure or _norm(procedure) in _norm(t["procedure"])]
    return {"region": hit[0] if hit else None,
            "available_regions": [x["code"] for x in d["regions"]],
            "required_documents": tl[0]["required_documents"] if tl else [],
            "procedure": tl[0]["procedure"] if tl else None,
            "sample_data": is_sample()}


# ---------- 7. check_timeline ----------
def check_timeline(procedure="骨科植入物注册", region="CN", start_date=None, as_of=None):
    """把相对天数展开成日历日期，并按 as_of 标出已完成/进行中/逾期未启动。"""
    d = load("timelines.json")
    p = _norm(procedure)
    tl = [t for t in d["timelines"] if p in _norm(t["procedure"])]
    if not tl:
        raise ValueError("无此程序的示例时间轴：%s" % procedure)
    tl = tl[0]
    start = _today(start_date) if start_date else datetime.date.today()
    now = _today(as_of) if as_of else datetime.date.today()
    phases = []
    for ph in tl["phases"]:
        s = start + datetime.timedelta(days=ph["offset_days"])
        e = s + datetime.timedelta(days=ph["duration_days"])
        if now > e:
            status = "completed"
        elif s <= now <= e:
            status = "in_progress"
        else:
            status = "not_started"
        phases.append({"name": ph["name"], "start": s.isoformat(),
                       "end": e.isoformat(), "status": status,
                       "days_to_start": (s - now).days})
    overdue = [x["name"] for x in phases
               if x["status"] == "not_started" and x["days_to_start"] < 0]
    return {"procedure": tl["procedure"], "region": region,
            "start_date": start.isoformat(), "as_of": now.isoformat(),
            "phases": phases, "overdue": overdue,
            "note": "相对天数为示例；官方审评时限以受理通知书为准。",
            "sample_data": is_sample()}


# ---------- 8. report_gap ----------
def report_gap(present, procedure="骨科植入物注册"):
    """对照必备材料清单报缺口：present 为已具备的材料名列表。"""
    d = load("timelines.json")
    p = _norm(procedure)
    tl = [t for t in d["timelines"] if p in _norm(t["procedure"])]
    if not tl:
        raise ValueError("无此程序的示例材料清单：%s" % procedure)
    required = tl[0]["required_documents"]
    have = set(_norm(x) for x in (present or []))
    missing = [r for r in required if _norm(r) not in have]
    return {"procedure": tl[0]["procedure"],
            "required_count": len(required), "have_count": len(required) - len(missing),
            "missing": missing,
            "completeness": round((len(required) - len(missing)) / len(required), 3),
            "sample_data": is_sample()}
