# medxpert-ortho-mcp · Orthopedic device testing connector

mcp-name: io.github.zhaoxinghua09-cell/medxpert-ortho-mcp

**English first, Chinese below.**

An MCP server with 8 tools for orthopedic device testing work: lab matching, quotation estimation,
UDI checks, dual-temporal standards lookup, class/path judgment trees, region routes,
registration timelines and gap reports. Offline, standard library only, zero dependencies.

It exists because four MedXpert expert packs (`medxpert-standards`, `medical-device-reg-translator`,
`medical-device-testing-link`, `med-device-compliance-toolkit`) had been referencing a connector called
`medxpert-ortho-mcp` that was never built. This is that connector, built.

## What is real and what is sample

| Aspect | Status |
|---|---|
| The server, the 8 tools, the protocol layer | **Real.** Implemented, unit-tested, published to PyPI and to the official MCP Registry |
| The datasets shipped in `datasets/` | **Sample.** Invented labs, invented prices, invented UDI-DIs. Illustrative only |
| Every tool result | Carries `sample_data: true` until you set `ORTHO_DATA_DIR` |

The bundled data is **not** an accreditation directory, **not** a price commitment, and **not**
a regulatory conclusion. Point `ORTHO_DATA_DIR` at your own JSON files to use real evidence.

## Data that does not fit fails loudly

A wrong data path used to be the most dangerous state this server could be in: the tools would keep
answering, from sample data, and `sample_data: true` was the only clue. That is a silent failure with
a regulatory conclusion on the far end of it, so it is now an error:

| Situation | Behaviour |
|---|---|
| `ORTHO_DATA_DIR` set, directory missing | The call fails with the path in the message. It never falls back to samples |
| A required dataset file missing | Fails, naming the file and the directory in use |
| Malformed JSON | Fails, naming file, line and column |
| JSON valid but top-level keys wrong | Fails, listing the keys that are required |
| Structurally bad content (orphan lab reference, 13-digit UDI, unknown status, empty phase list) | Reported by the check below, per file and per cross-check |

Check your own data before relying on it:

```bash
ORTHO_DATA_DIR=/path/to/your/datasets python -m medxpert_ortho.server --validate-data
```

It prints a structured report, `DATA CHECK: PASS` or `FAIL`, and exits `1` on failure — so it can be
a CI step rather than a ritual.

## Run

```bash
uvx medxpert-ortho-mcp          # stdio MCP server
python -m medxpert_ortho.server --selftest   # offline self-test, no host needed
python -m medxpert_ortho.server --validate-data   # check ORTHO_DATA_DIR (or the bundled samples)
```

MCP host configuration:

```json
{"mcpServers": {"medxpert-ortho-mcp": {"command": "uvx", "args": ["medxpert-ortho-mcp"]}}}
```

Custom data directory:

```json
{"mcpServers": {"medxpert-ortho-mcp": {
  "command": "uvx", "args": ["medxpert-ortho-mcp"],
  "env": {"ORTHO_DATA_DIR": "/path/to/your/datasets"}}}}
```

## Tools

| Tool | What it does | Honest limit |
|---|---|---|
| `match_labs` | Ranks labs by capability keyword, region and device description | Sample data has 3 labs and a few capability items |
| `calc_quote` | Price range by lab and scope, total estimated by quantity (>included samples +12%) | Prices are illustrative; not a commercial offer |
| `check_udi` | 14-digit UDI-DI lookup, returns class / sterile / single-use | Misses are explained as sample-data scope, not proof of absence |
| `query_standard` | Keyword search with `as_of` dual-temporal judgement (in force? superseded?) | Status fields are demo logic; verify against the official current version |
| `find_judgment_tree` | Step-by-step classification / route questions | A demo tree, not a review decision |
| `get_region_path` | Authority, route note and required documents per region | Sample routes only for CN / CN-JS / CN-SH |
| `check_timeline` | Expands relative days into calendar dates, marks completed / in_progress / not_started, flags overdue | Durations are illustrative; official clocks start at acceptance |
| `report_gap` | Compares present documents against the required checklist | Checklist is sample data |

## Design notes

- **Zero dependencies.** JSON-RPC 2.0 over stdin/stdout, implemented with the standard library only.
  No network calls at runtime; nothing leaves the machine.
- **Provenance in every answer.** A tool that cannot say whether it answered from sample data or
  from your own data is a tool you cannot audit, so every result says which.
- **Mismatch is reported, not smoothed over.** A UDI miss says "sample scope", a tree miss lists what
  trees exist, an empty lab match returns a hint rather than an empty success.
- **Bad input is an error, not a quiet fallback.** See above: the server will not answer from samples
  while your data path is broken. The check is also runnable as `--validate-data` with a non-zero exit.

## Gate

`.github/workflows/ci.yml` runs the unit tests and `tools/version_gate.py`, which checks
version consistency across `pyproject.toml`, `__init__.py`, `server.json` and the declared tool
count, and reports how many `uses:` references are pinned to full SHAs.

---

# medxpert-ortho-mcp · 骨科器械检测对接连接器

**先英后中。**

一个 8 工具的 MCP server，用于骨科器械检测对接：机构匹配、报价估算、UDI 校验、双时态标准检索、
分类/路径判定树、地区路径、注册时间轴、缺口报告。离线、仅标准库、零依赖。

它存在的理由：四个 MedXpert 专家包（`medxpert-standards`、`medical-device-reg-translator`、
`medical-device-testing-link`、`med-device-compliance-toolkit`）从 2026 年起一直引用一个叫
`medxpert-ortho-mcp` 的连接器，而那个连接器从未被造出来。这就是它，现在有了。

## 哪些是真的，哪些是示例

| 方面 | 状态 |
|---|---|
| 服务本身、8 个工具、协议层 | **真的。** 已实现、有单元测试、已发布到 PyPI 与官方 MCP Registry |
| `datasets/` 里的数据 | **示例。** 虚构机构、虚构价格、虚构 UDI-DI，仅供演示 |
| 每个工具返回值 | 只要没设 `ORTHO_DATA_DIR`，一律带 `sample_data: true` |

包内数据**不是**资质目录、**不是**报价承诺、**不是**法规结论。要用于真实工作，把
`ORTHO_DATA_DIR` 指向你自己的 JSON 数据目录。

## 数据不合规就报错，不静默降级

数据路径写错，曾是这台服务最危险的状态：工具照常作答，用示例数据答，唯一线索只有一个
`sample_data: true`。这是会一路传导到法规结论的静默失败，所以现在改成报错：

| 情形 | 行为 |
|---|---|
| `ORTHO_DATA_DIR` 设了但目录不存在 | 调用直接失败，错误信息里带路径；**绝不退回示例数据** |
| 必需的数据集文件缺失 | 失败，并指出文件名与当前数据目录 |
| JSON 语法错 | 失败，并指出文件、行、列 |
| JSON 合法但顶层键不对 | 失败，并列出必需的顶层键 |
| 结构性问题（报价指向不存在的机构、13 位 UDI、非法 status、阶段为空） | 由下面的体检逐文件、逐交叉项报出 |

用自己的数据之前先体检：

```bash
ORTHO_DATA_DIR=/path/to/your/datasets python -m medxpert_ortho.server --validate-data
```

输出结构化报告，末行 `DATA CHECK: PASS` 或 `FAIL`，失败时退出码 `1`——因此它可以进 CI，
而不只是一次仪式。

## 运行

```bash
uvx medxpert-ortho-mcp                        # 起 stdio MCP 服务
python -m medxpert_ortho.server --selftest   # 离线自测，不需要宿主
python -m medxpert_ortho.server --validate-data   # 体检 ORTHO_DATA_DIR（或包内示例）
```

## 工具与诚实的边界

| 工具 | 做什么 | 边界 |
|---|---|---|
| `match_labs` | 按能力关键词、地区、器械描述给机构打分 | 示例数据仅 3 家机构、少数能力项 |
| `calc_quote` | 按机构与能力项给价格区间，超出含样量 +12% | 价格为演示值，不构成商务报价 |
| `check_udi` | 14 位 UDI-DI 查表，回出分类/无菌/一次性 | 未命中会说明是示例范围，不是"不存在"的证据 |
| `query_standard` | 关键词检索 + `as_of` 双时态判定（是否生效、是否被替代） | 状态字段为演示逻辑，以官方现行版为准 |
| `find_judgment_tree` | 逐步问答式分类/路径判定 | 演示结构，不是审评结论 |
| `get_region_path` | 受理机关、路径说明、必备材料 | 仅 CN / CN-JS / CN-SH 三条示例路径 |
| `check_timeline` | 相对天数展开成日历，标 completed / in_progress / not_started 与逾期 | 天数为示例；官方时限自受理起算 |
| `report_gap` | 已具备材料对照必备清单，报缺口与完整度 | 清单为示例数据 |

## 门禁

`ci.yml` 跑单元测试 + `tools/version_gate.py`：核对 `pyproject.toml`、`__init__.py`、`server.json`
与声明的工具数是否一致，并自报 `uses:` 有多少处钉了完整 SHA。
