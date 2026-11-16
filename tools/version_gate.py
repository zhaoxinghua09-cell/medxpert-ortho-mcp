#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布前门禁：版本单一源、声明一致、工具数一致、action 钉版自报。

它检查的是"四份东西说的是不是同一个事实"：
  medxpert_ortho/__init__.py __version__  ← 唯一权威版本
  pyproject.toml（dynamic attr 读的就是上面那个）
  server.json（顶层 version、packages[0].version）
  server.json _meta 里声明的 tool_count / tools 列表 ↔ 代码里真实的 TOOLS

退出码：不一致即 1，绝不"警告后继续"。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from medxpert_ortho import __version__ as V  # noqa: E402
from medxpert_ortho.server import TOOLS  # noqa: E402

problems = []


def fail(msg):
    problems.append(msg)


# 1. server.json 版本与包版本
sj = json.load(open(os.path.join(ROOT, "server.json"), encoding="utf-8"))
if sj.get("version") != V:
    fail("server.json version %r != __version__ %r" % (sj.get("version"), V))
for p in sj.get("packages", []):
    if p.get("version") != V:
        fail("server.json packages version %r != %r" % (p.get("version"), V))

# 2. pyproject 版本来源必须是 attr，不能另写一个字面量
py = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
if 'version = { attr = "medxpert_ortho.__version__" }' not in py:
    fail("pyproject.toml does not read version from medxpert_ortho.__version__")
if re.search(r'^version\s*=\s*"', py, re.M):
    fail("pyproject.toml hard-codes a version literal as well as the attr")

# 3. 工具数：声明与代码必须一致
meta = (sj.get("_meta") or {}).get("io.modelcontextprotocol.registry/publisher-provided") or {}
declared_count = meta.get("tool_count")
declared_names = [x.strip() for x in (meta.get("tools") or "").split(",") if x.strip()]
real_names = [t["name"] for t in TOOLS]
if declared_count != len(real_names) or len(declared_names) != len(real_names):
    fail("tool_count declared %r / names %d, code has %d"
         % (declared_count, len(declared_names), len(real_names)))
if declared_names != real_names:
    fail("declared tools %s != code tools %s" % (declared_names, real_names))

# 4. 每个工具必须有 name / description / inputSchema
for t in TOOLS:
    for k in ("name", "description", "inputSchema"):
        if not t.get(k):
            fail("tool %r missing %s" % (t.get("name"), k))

# 5. action 钉版自报：核到几处、浮动几处，都要说出来
wf_dir = os.path.join(ROOT, ".github", "workflows")
pin_lines = []
if os.path.isdir(wf_dir):
    files, uses, pinned, floating = 0, 0, 0, 0
    for fn in sorted(os.listdir(wf_dir)):
        if not fn.endswith((".yml", ".yaml")):
            continue
        files += 1
        for line in open(os.path.join(wf_dir, fn), encoding="utf-8"):
            m = re.match(r"\s*(?:- )?uses:\s*(\S+)", line)
            if not m:
                continue
            uses += 1
            ref = m.group(1)
            if re.search(r"@[0-9a-f]{40}$", ref):
                pinned += 1
            elif "@" in ref and not ref.startswith("./"):
                floating += 1
                pin_lines.append("%s: %s" % (fn, ref))
    print("PIN CHECK: %d 个 workflow、%d 处 uses 已核，钉 %d 处，浮动 %d 处"
          % (files, uses, pinned, floating))
    for line in pin_lines:
        print("  浮动: %s" % line)
    if floating:
        fail("%d action references are not pinned to a full SHA" % floating)
else:
    print("PIN SKIP: 未找到 .github/workflows，钉版规则未生效")

print("VERSION: %s" % V)
print("TOOLS: %d (%s)" % (len(TOOLS), ", ".join(real_names)))

if problems:
    print("GATE FAIL")
    for p in problems:
        print(" - %s" % p)
    sys.exit(1)
print("GATE PASS")
