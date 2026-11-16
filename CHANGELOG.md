## 0.1.2 — 2026-11-16

**Data errors stop being quiet.** In 0.1.1 a wrong ORTHO_DATA_DIR (typo, unmounted path) was silently
ignored and every tool answered from the bundled samples, with only sample_data: true as a clue. A
regulatory-facing answer computed from the wrong dataset is the failure mode this whole release set is
about, so the loader now fails with the path, the filename, the JSON position or the missing keys, and
never falls back.

- Adds --validate-data: per-file and cross-file checks (orphan quote lab, 14-digit UDI, status enum,
  phase shape, empty document list, region codes), DATA CHECK: PASS/FAIL, exit code 1 on failure.
- Adds 7 unit tests covering the guard itself, including a broken-JSON case and an orphan-quote case.
- One correction during implementation: the validator first rejected the bundled standards with
  status: current because I had written the enum as in_force/superseded. The check was wrong, not
  the data — the enum follows what the data and query_standard actually use.
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