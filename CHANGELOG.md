# Changelog

## 0.1.0 — 2026-11-16

First release. Built to satisfy a dependency that four MedXpert expert packs had referenced
since 2026 while no such connector existed anywhere (PyPI, official registry and all four
accounts returned 404 on 2026-11-16).

- 8 tools implemented and unit-tested: `match_labs`, `calc_quote`, `check_udi`,
  `query_standard`, `find_judgment_tree`, `get_region_path`, `check_timeline`, `report_gap`
- stdio JSON-RPC 2.0, standard library only, zero dependencies, no runtime egress
- bundled datasets are illustrative samples; every result carries `sample_data: true` unless
  `ORTHO_DATA_DIR` points at user-supplied data
- `tools/version_gate.py` enforces a single version source and consistent tool counts, and
  self-reports action pin coverage