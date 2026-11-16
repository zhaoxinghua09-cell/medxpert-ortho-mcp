"""确定性测试：每个工具都要有正例与反例，反例必须真的报错或返回 found=False。"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from medxpert_ortho import core  # noqa: E402


class TestMatchLabs(unittest.TestCase):
    def test_hits_capability(self):
        r = core.match_labs(scope_keyword="力学疲劳")
        self.assertGreaterEqual(r["count"], 1)
        self.assertEqual(r["matches"][0]["id"], "LAB-DEMO-01")

    def test_unknown_keyword_returns_empty_not_error(self):
        r = core.match_labs(scope_keyword="完全不存在的能力")
        self.assertEqual(r["matches"], [])
        self.assertIn("hint", r)

    def test_region_boost(self):
        r = core.match_labs(scope_keyword="电气安全", region="CN-GD")
        self.assertEqual(r["matches"][0]["id"], "LAB-DEMO-03")


class TestCalcQuote(unittest.TestCase):
    def test_base_quote(self):
        r = core.calc_quote("LAB-DEMO-01", "力学疲劳", 5)
        self.assertEqual(r["estimated_total_range"]["low"], 38000)

    def test_overage_multiplies(self):
        base = core.calc_quote("LAB-DEMO-01", "力学疲劳", 5)["estimated_total_range"]["low"]
        over = core.calc_quote("LAB-DEMO-01", "力学疲劳", 8)["estimated_total_range"]["low"]
        self.assertGreater(over, base)

    def test_missing_scope_raises(self):
        with self.assertRaises(ValueError):
            core.calc_quote("LAB-DEMO-01", "不存在的能力项")


class TestUdi(unittest.TestCase):
    def test_found(self):
        r = core.check_udi("06900000000002")
        self.assertTrue(r["found"])
        self.assertEqual(r["entry"]["class"], "III")

    def test_not_found_says_so(self):
        r = core.check_udi("00000000000000")
        self.assertFalse(r["found"])
        self.assertTrue(r["hint"])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            core.check_udi("")


class TestStandard(unittest.TestCase):
    def test_dual_temporal_before_effective(self):
        r = core.query_standard("16886", as_of="2020-01-01")
        self.assertEqual(r["matches"][0]["in_force_on_as_of"], False)

    def test_dual_temporal_after_effective(self):
        r = core.query_standard("16886", as_of="2026-11-16")
        self.assertEqual(r["matches"][0]["in_force_on_as_of"], True)

    def test_superseded_flagged(self):
        r = core.query_standard("YY/T 0316")
        self.assertEqual(r["matches"][0]["status"], "superseded")
        self.assertIn("superseded_by", r["matches"][0])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            core.query_standard("  ")


class TestTreeAndPath(unittest.TestCase):
    def test_tree(self):
        r = core.find_judgment_tree("骨科植入物注册")
        self.assertIsNotNone(r["tree"])
        self.assertGreaterEqual(len(r["tree"]["steps"]), 2)

    def test_tree_miss_lists_available(self):
        r = core.find_judgment_tree("完全不存在的程序")
        self.assertIsNone(r["tree"])
        self.assertTrue(r["available"])

    def test_region_path(self):
        r = core.get_region_path("CN-JS", "骨科植入物注册")
        self.assertIn("江苏省", r["region"]["name"])
        self.assertIn("产品技术要求", r["required_documents"])

    def test_region_unknown_returns_none(self):
        r = core.get_region_path("XX-999")
        self.assertIsNone(r["region"])
        self.assertTrue(r["available_regions"])


class TestTimeline(unittest.TestCase):
    def test_statuses(self):
        r = core.check_timeline(start_date="2026-01-01", as_of="2026-11-16")
        st = {p["name"]: p["status"] for p in r["phases"]}
        self.assertEqual(st["体系建立与型式检验"], "completed")
        self.assertTrue(all(p["start"] <= p["end"] for p in r["phases"]))

    def test_dates_expand_from_offset(self):
        r = core.check_timeline(start_date="2026-01-01", as_of="2026-01-01")
        first = r["phases"][0]
        self.assertEqual(first["start"], "2026-01-01")

    def test_bad_procedure_raises(self):
        with self.assertRaises(ValueError):
            core.check_timeline("不存在程序")


class TestGap(unittest.TestCase):
    def test_gap(self):
        r = core.report_gap(["产品技术要求", "检验报告"])
        self.assertEqual(r["have_count"], 2)
        self.assertIn("生物学评价资料", r["missing"])
        self.assertLess(r["completeness"], 1)

    def test_complete(self):
        req = core.get_region_path("CN", "骨科植入物注册")["required_documents"]
        r = core.report_gap(req)
        self.assertEqual(r["missing"], [])
        self.assertEqual(r["completeness"], 1.0)


class TestProvenance(unittest.TestCase):
    def test_every_result_marks_sample_data(self):
        self.assertTrue(core.match_labs("力学疲劳")["sample_data"])
        self.assertTrue(core.check_udi("06900000000001")["sample_data"])
        self.assertTrue(core.report_gap(["产品技术要求"])["sample_data"])


class TestDataGuard(unittest.TestCase):
    """数据层必须"坏就吼"。上一版最危险的失败是：路径写错，工具照常给出示例结论。"""

    def setUp(self):
        self._old = os.environ.get("ORTHO_DATA_DIR")
        self.tmp = tempfile.mkdtemp(prefix="ortho_bad_")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("ORTHO_DATA_DIR", None)
        else:
            os.environ["ORTHO_DATA_DIR"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_dir_fails_loudly_not_silently(self):
        os.environ["ORTHO_DATA_DIR"] = os.path.join(self.tmp, "nope")
        with self.assertRaises(core.DataError) as ctx:
            core.match_labs("力学疲劳")
        self.assertIn("nope", str(ctx.exception))
        self.assertIn("不会静默退回", str(ctx.exception))

    def test_missing_file_names_the_file(self):
        os.environ["ORTHO_DATA_DIR"] = self.tmp
        with self.assertRaises(core.DataError) as ctx:
            core.check_udi("06900000000002")
        self.assertIn("udi.json", str(ctx.exception))

    def test_broken_json_reports_position(self):
        os.environ["ORTHO_DATA_DIR"] = self.tmp
        path = os.path.join(self.tmp, "labs.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"labs": [}')
        with self.assertRaises(core.DataError) as ctx:
            core.match_labs("力学疲劳")
        self.assertIn("不是合法 JSON", str(ctx.exception))

    def test_missing_top_level_key_is_named(self):
        os.environ["ORTHO_DATA_DIR"] = self.tmp
        with open(os.path.join(self.tmp, "labs.json"), "w", encoding="utf-8") as f:
            f.write('{"institutions": []}')
        with self.assertRaises(core.DataError) as ctx:
            core.match_labs("力学疲劳")
        self.assertIn("labs", str(ctx.exception))

    def test_validate_passes_on_bundled_data(self):
        os.environ.pop("ORTHO_DATA_DIR", None)
        rep = core.validate_data()
        self.assertTrue(rep["ok"], rep)
        self.assertTrue(rep["sample_data"])

    def test_validate_flags_orphan_quote(self):
        os.environ["ORTHO_DATA_DIR"] = self.tmp
        shutil.copytree(core.DATASET_DIR, self.tmp, dirs_exist_ok=True)
        q = os.path.join(self.tmp, "quotes.json")
        data = json.loads(open(q, encoding="utf-8").read())
        data["quotes"][0]["lab_id"] = "LAB-GHOST"
        with open(q, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        rep = core.validate_data()
        self.assertFalse(rep["ok"])
        self.assertTrue(any(f.get("code") == "quotes:orphan" for f in rep["files"]))

    def test_validate_flags_short_udi(self):
        os.environ["ORTHO_DATA_DIR"] = self.tmp
        shutil.copytree(core.DATASET_DIR, self.tmp, dirs_exist_ok=True)
        p = os.path.join(self.tmp, "udi.json")
        data = json.loads(open(p, encoding="utf-8").read())
        data["entries"][0]["udi_di"] = "0690000000000"   # 13 位
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        rep = core.validate_data()
        self.assertFalse(rep["ok"])
        self.assertTrue(any(f.get("code") == "udi:format" for f in rep["files"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
