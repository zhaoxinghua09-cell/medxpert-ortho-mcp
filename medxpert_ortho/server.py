#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""medxpert-ortho-mcp — stdio JSON-RPC 2.0 MCP server（纯标准库）。

8 个工具：
  match_labs           按能力关键词/地区/器械描述给机构打分排序
  calc_quote           按机构与能力项取示例报价区间，按数量估算总额
  check_udi            校验 UDI-DI，回出分类与属性
  query_standard       查标准（支持 as_of 双时态判定）
  find_judgment_tree   取判定树
  get_region_path      取地区路径与必备材料
  check_timeline       把相对天数展开成日历并标状态
  report_gap           对照必备清单报缺口

运行：uvx medxpert-ortho-mcp     |  python -m medxpert_ortho.server
自测：python -m medxpert_ortho.server --selftest
"""
import json
import sys

from . import __version__
from . import core

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "medxpert-ortho-mcp",
    "version": __version__,
    "title": "MedXpert 骨科器械检测对接（8 工具，离线，示例数据）",
}

TOOLS = [
    {"name": "match_labs",
     "description": "按能力关键词 / 地区 / 器械描述给检测机构打分排序。例：scope_keyword='力学疲劳'。返回命中能力项与联系方式；示例数据仅 3 家机构。",
     "inputSchema": {"type": "object", "properties": {
         "scope_keyword": {"type": "string", "description": "能力关键词，如 力学疲劳、生物相容性"},
         "region": {"type": "string", "description": "地区码，如 CN-JS"},
         "device": {"type": "string", "description": "器械描述，如 接骨板"},
         "limit": {"type": "number", "description": "返回条数，默认 5"}}}},
    {"name": "calc_quote",
     "description": "按机构与能力项取报价区间并按数量估算总额（含超出含样量加价规则）。价格是示例区间，不构成商务承诺。",
     "inputSchema": {"type": "object", "required": ["lab_id", "scope"], "properties": {
         "lab_id": {"type": "string", "description": "机构 ID，来自 match_labs"},
         "scope": {"type": "string", "description": "能力项，如 力学疲劳"},
         "quantity": {"type": "number", "description": "样品数量，默认 1"}}}},
    {"name": "check_udi",
     "description": "校验 14 位 UDI-DI 并回出分类/无菌/一次性属性。未命中会说明示例数据范围，不代表真实数据库无此编号。",
     "inputSchema": {"type": "object", "required": ["udi_di"], "properties": {
         "udi_di": {"type": "string", "description": "14 位 UDI-DI"}}}},
    {"name": "query_standard",
     "description": "按关键词查标准，并可带 as_of 做双时态判定：该日是否已生效、是否已被替代。",
     "inputSchema": {"type": "object", "required": ["keyword"], "properties": {
         "keyword": {"type": "string", "description": "标准号或题名关键词"},
         "as_of": {"type": "string", "description": "判定基准日 YYYY-MM-DD（可选）"}}}},
    {"name": "find_judgment_tree",
     "description": "取分类/路径判定树（逐步问答结构）。演示结构，最终以分类目录与界定结论为准。",
     "inputSchema": {"type": "object", "properties": {
         "procedure": {"type": "string", "description": "程序名，如 骨科植入物注册"},
         "region": {"type": "string", "description": "地区码，默认 CN"}}}},
    {"name": "get_region_path",
     "description": "取地区路径：受理机关、路径说明与该程序的必备材料清单。",
     "inputSchema": {"type": "object", "required": ["region"], "properties": {
         "region": {"type": "string", "description": "地区码，如 CN、CN-JS"},
         "procedure": {"type": "string", "description": "程序名（可选）"}}}},
    {"name": "check_timeline",
     "description": "把相对天数展开成日历日期，并按 as_of 标出 completed/in_progress/not_started 与逾期未启动项。",
     "inputSchema": {"type": "object", "properties": {
         "procedure": {"type": "string", "description": "程序名，默认 骨科植入物注册"},
         "region": {"type": "string", "description": "地区码，默认 CN"},
         "start_date": {"type": "string", "description": "起始日 YYYY-MM-DD（默认今天）"},
         "as_of": {"type": "string", "description": "判定基准日 YYYY-MM-DD（默认今天）"}}}},
    {"name": "report_gap",
     "description": "对照必备材料清单报缺口：给已具备材料名列表，返回缺失项与完整度。",
     "inputSchema": {"type": "object", "required": ["present"], "properties": {
         "present": {"type": "array", "items": {"type": "string"},
                     "description": "已具备的材料名列表"},
         "procedure": {"type": "string", "description": "程序名，默认 骨科植入物注册"}}}},
]

DISPATCH = {
    "match_labs": core.match_labs,
    "calc_quote": core.calc_quote,
    "check_udi": core.check_udi,
    "query_standard": core.query_standard,
    "find_judgment_tree": core.find_judgment_tree,
    "get_region_path": core.get_region_path,
    "check_timeline": core.check_timeline,
    "report_gap": core.report_gap,
}


def dispatch_tool(name, args):
    fn = DISPATCH.get(name)
    if fn is None:
        raise ValueError("未知工具: %s" % name)
    res = fn(**(args or {}))
    text = json.dumps(res, ensure_ascii=False)
    body = {"content": [{"type": "text", "text": text}], "structuredContent": {"result": res}}
    if res.get("sample_data"):
        body["content"].append({"type": "text",
                                "text": "数据来源：本包示例数据（非官方资质目录/报价/法规结论）。"})
    return body


def make_response(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def make_error(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def handle(msg):
    method = msg.get("method")
    mid = msg.get("id")
    params = msg.get("params") or {}
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return make_response(mid, {})
    if method == "initialize":
        return make_response(mid, {"protocolVersion": PROTOCOL_VERSION,
                                   "capabilities": {"tools": {"listChanged": False}},
                                   "serverInfo": SERVER_INFO})
    if method == "tools/list":
        return make_response(mid, {"tools": TOOLS})
    if method == "tools/call":
        try:
            return make_response(mid, dispatch_tool(params.get("name"), params.get("arguments")))
        except Exception as e:
            return make_response(mid, {"content": [{"type": "text", "text": "错误: %s" % e}],
                                       "isError": True})
    return make_error(mid, -32601, "方法不存在: %s" % method)


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        out = handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def selftest():
    print("=== medxpert-ortho-mcp 自测 ===")
    r = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    si = r["result"]["serverInfo"]
    print("[initialize] %s v%s" % (si["name"], si["version"]))
    r = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    print("[tools/list] %d 个: %s" % (len(r["result"]["tools"]),
                                       ", ".join(t["name"] for t in r["result"]["tools"])))
    for i, (name, args) in enumerate([
            ("match_labs", {"scope_keyword": "力学疲劳"}),
            ("calc_quote", {"lab_id": "LAB-DEMO-01", "scope": "力学疲劳", "quantity": 8}),
            ("check_udi", {"udi_di": "06900000000002"}),
            ("query_standard", {"keyword": "16886", "as_of": "2020-01-01"}),
            ("find_judgment_tree", {"procedure": "骨科植入物注册"}),
            ("get_region_path", {"region": "CN-JS"}),
            ("check_timeline", {"start_date": "2026-01-01", "as_of": "2026-11-16"}),
            ("report_gap", {"present": ["产品技术要求", "检验报告"]})], start=10):
        res = handle({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                      "params": {"name": name, "arguments": args}})
        body = res["result"]
        ok = not body.get("isError")
        print("[%s] %s" % (name, "OK" if ok else body["content"][0]["text"]))
    print("=== 自测结束 ===")


def validate_data_cli():
    """体检当前数据目录。放错路径或字段不合规时，这里退出码 1，而不是让工具给出示例结论。"""
    rep = core.validate_data()
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    if not rep["ok"]:
        print("DATA CHECK: FAIL")
        for f in rep.get("files", []):
            if f.get("code"):
                print("  - %s: %s" % (f["code"], f["message"]))
        return 1
    print("DATA CHECK: PASS (files=%d, data_dir=%s)"
          % (len(rep["files"]), rep["data_dir"]))
    return 0


def main():
    if "--validate-data" in sys.argv:
        return validate_data_cli()
    if "--selftest" in sys.argv:
        selftest()
    else:
        serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
