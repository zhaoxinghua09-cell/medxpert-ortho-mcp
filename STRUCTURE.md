# STRUCTURE — 分层与改动代价

## 四层

| 层 | 文件 | 内容 |
|---|---|---|
| L1 数据 | `medxpert_ortho/datasets/{standards,judgment_trees,labs,quotes,timelines,udi}.json` | 标准索引、分类判定树、实验室、报价、时限、UDI |
| L2 逻辑 | `medxpert_ortho/core.py` | 匹配、判定、估算；纯函数，无网络 |
| L3 接口 | `medxpert_ortho/server.py`、`server.json` | MCP 工具声明与路由（8 个工具） |
| L4 检验与发布 | `tests/test_core.py`、`tools/version_gate.py`、`.github/workflows/{ci,publish-mcp,publish-pypi}.yml` | 单测、版本一致性、发布流水线 |

## 改动代价

| 你想做 | 改哪里 | 必须重跑 | 必须同步 |
|---|---|---|---|
| 加一条标准/时限 | `datasets/*.json` | `tests/test_core.py`（结构校验） | `CHANGELOG.md` |
| 改判定树 | `datasets/judgment_trees.json` + `core.py` | 单测中的判定用例 | README 工具说明 |
| 加一个 MCP 工具 | `server.py` + `core.py` | `ci.yml` | `server.json`、`server.json` 版本、PyPI 发布说明 |

## 边界

本仓只做 **路径/费用/UDI 的估算与索引**，不做合规判定。
判定归 `lcas`；证据链归 `uibc-core`；注册文书内容归 `medxpert-reg-connector`。
