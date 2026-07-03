# codes/tests/test_smoke.py
"""
Smoke tests for PAINDICATOR's pure (VTK-free, Qt-free) modules.

These are the regression safety net for the improvement work:
  1. SessionManager save -> load round-trip on a temporary directory
  2. dermatome_coverage.compute_dermatome_coverage on a tiny synthetic input
  3. DermatomeMapper loads both male and female .u8 maps + meta files

Run from the project root:
    venv311\\Scripts\\activate
    python -m pytest codes/tests/test_smoke.py -v
or without pytest:
    python -m codes.tests.test_smoke
"""

import json
import os
import sys
import tempfile
import unittest

# Ensure project root is importable when run directly
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from codes.session_manager import SessionManager
from codes.dermatome_coverage import (
    compute_dermatome_coverage,
    serialize_dermatome_coverage,
    format_dermatome_coverage_for_display,
)
from codes.dermatome_mapper import DermatomeMapper
from codes import config


class TestSessionManagerRoundTrip(unittest.TestCase):
    def test_save_load_round_trip(self):
        sm = SessionManager()
        sm.start_new_session("test_patient_001", gender="male",
                             clinician_name="Dr. Test")
        sm.set_questionnaire({"age": 42, "pain peak": 7, "pain average": 4})
        sm.set_model_data({
            "mode": "paint_v2",
            "paint_v2": {"point_level": [0, 1, 2, 3, 0]},
            "comments": ["test comment"],
        })

        with tempfile.TemporaryDirectory() as tmp:
            folder = sm.get_session_folder(base_dir=tmp)
            json_path = sm.save_to_file(folder)
            self.assertTrue(os.path.exists(json_path))

            summary_path = sm.save_to_human_readable_file(folder)
            self.assertTrue(os.path.exists(summary_path))

            # Load into a fresh manager and compare
            sm2 = SessionManager()
            data = sm2.load_from_file(json_path)
            self.assertEqual(
                data["subject_info"]["subject_id"], "test_patient_001")
            self.assertEqual(data["subject_info"]["gender"], "male")
            self.assertEqual(data["questionnaire"]["age"], 42)
            self.assertEqual(
                data["model_data"]["paint_v2"]["point_level"], [0, 1, 2, 3, 0])
            # Sticky folder derived from path
            self.assertEqual(sm2.current_session_folder,
                             os.path.basename(folder))

    def test_get_marks_and_paint_v2_are_safe_on_empty(self):
        sm = SessionManager()
        self.assertEqual(sm.get_marks(), {})
        self.assertEqual(sm.get_paint_v2(), {})

    def test_subject_info_validation(self):
        sm = SessionManager()
        # Unsafe chars stripped from subject_id (it becomes a folder name)
        sm.set_subject_info('ab<>:"/\\|?*cd', gender="MALE")
        info = sm.data["subject_info"]
        self.assertEqual(info["subject_id"], "abcd")
        self.assertEqual(info["gender"], "male")  # normalized to lowercase
        # Invalid gender is rejected, previous value kept
        sm.set_subject_info(None, gender="banana")
        self.assertEqual(sm.data["subject_info"]["gender"], "male")

    def test_questionnaire_validation_clamps(self):
        sm = SessionManager()
        sm.set_questionnaire({
            "age": 999,           # out of range -> clamped to 120
            "pain peak": -5,      # clamped to 0
            "pain average": "7",  # numeric string -> accepted as 7
            "pain anamnesis": "abc",  # non-numeric -> dropped
            "frequency comment": "free text stays untouched",
        })
        q = sm.data["questionnaire"]
        self.assertEqual(q["age"], 120)
        self.assertEqual(q["pain peak"], 0)
        self.assertEqual(q["pain average"], 7)
        self.assertNotIn("pain anamnesis", q)
        self.assertEqual(q["frequency comment"], "free text stays untouched")

    def test_load_corrupted_json_raises_clean_error(self):
        from codes.session_manager import SessionLoadError
        sm = SessionManager()
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = os.path.join(tmp, "session.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write("{ this is not valid json !!!")
            with self.assertRaises(SessionLoadError):
                sm.load_from_file(bad_path)
            # Missing file also raises SessionLoadError (not a bare crash)
            with self.assertRaises(SessionLoadError):
                sm.load_from_file(os.path.join(tmp, "missing.json"))

    def test_schema_version_written_and_legacy_load_ok(self):
        sm = SessionManager()
        sm.start_new_session("p1", gender="female")
        with tempfile.TemporaryDirectory() as tmp:
            folder = sm.get_session_folder(base_dir=tmp)
            json_path = sm.save_to_file(folder)
            with open(json_path, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["schema_version"], 1)

            # Legacy session without schema_version must still load
            legacy_path = os.path.join(tmp, "legacy.json")
            with open(legacy_path, "w", encoding="utf-8") as f:
                json.dump({"subject_info": {"subject_id": "old"},
                           "model_data": {}}, f)
            sm2 = SessionManager()
            data = sm2.load_from_file(legacy_path)
            self.assertEqual(data["subject_info"]["subject_id"], "old")


class TestDermatomeCoverage(unittest.TestCase):
    def _tiny_inputs(self):
        # 10 vertices, dermatomes 5 (C5) and 6 (C6)
        point_levels = [0, 1, 2, 3, 0, 3, 3, 0, 1, 0]
        derm_map =     [5, 5, 5, 5, 5, 6, 6, 6, 6, 0]
        totals = {5: 5, 6: 4}
        id_to_name = {0: "UNASSIGNED", 5: "C5", 6: "C6"}
        order = [5, 6]
        return point_levels, derm_map, totals, id_to_name, order

    def test_basic_metrics(self):
        pl, dm, totals, names, order = self._tiny_inputs()
        result = compute_dermatome_coverage(pl, dm, totals, names, order)

        self.assertEqual(result["analysis_type"], "anatomical_mapping_only")
        overall = result["overall"]
        # painted: pids 1,2,3 (C5) + 5,6,8 (C6) = 6 vertices
        self.assertEqual(overall["total_painted_vertices"], 6)
        # mass: 1+2+3 (C5=6) + 3+3+1 (C6=7) = 13
        self.assertEqual(overall["total_painted_mass"], 13)

        rows = {r["name"]: r for r in result["dermatomes"]}
        self.assertIn("C5", rows)
        self.assertIn("C6", rows)
        self.assertAlmostEqual(rows["C5"]["weighted_pain_burden"], 6 / 13)
        self.assertAlmostEqual(rows["C6"]["weighted_pain_burden"], 7 / 13)
        self.assertAlmostEqual(rows["C5"]["local_involvement"], 3 / 5)
        self.assertAlmostEqual(rows["C6"]["mean_local_intensity"], 7 / 3)
        # C6 has higher burden -> rank 1
        self.assertEqual(rows["C6"]["rank"], 1)

    def test_empty_paint_returns_empty(self):
        pl = [0] * 10
        _, dm, totals, names, order = self._tiny_inputs()
        result = compute_dermatome_coverage(pl, dm, totals, names, order)
        self.assertEqual(result["dermatomes"], [])
        self.assertEqual(result["overall"]["total_painted_vertices"], 0)

    def test_none_derm_map_unavailable(self):
        result = compute_dermatome_coverage([1, 2], None, {}, {}, [])
        self.assertEqual(result["analysis_type"], "unavailable")

    def test_serialize_is_json_safe(self):
        pl, dm, totals, names, order = self._tiny_inputs()
        result = compute_dermatome_coverage(pl, dm, totals, names, order)
        serialized = serialize_dermatome_coverage(result)
        # Must round-trip through JSON without error
        json.dumps(serialized)

    def test_format_for_display_returns_text(self):
        pl, dm, totals, names, order = self._tiny_inputs()
        result = compute_dermatome_coverage(pl, dm, totals, names, order)
        text = format_dermatome_coverage_for_display(result)
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)


class TestDermatomeMapperLoads(unittest.TestCase):
    """Load the real .u8 + meta files for both models (skip if missing)."""

    def _check_mapper(self, info: dict):
        if not (os.path.exists(info["derm_bin"])
                and os.path.exists(info["derm_meta"])):
            self.skipTest("model dermatome files not present")

        mapper = DermatomeMapper(info["derm_bin"], info["derm_meta"])
        self.assertIsNotNone(mapper.derm_map)
        self.assertGreater(len(mapper.derm_map), 0)
        # id_to_name must contain UNASSIGNED and at least a few dermatomes
        self.assertEqual(mapper.id_to_name.get(0), "UNASSIGNED")
        self.assertGreater(len(mapper.id_to_name), 5)
        # Order must be ascending and exclude UNASSIGNED
        order = mapper.get_dermatome_order()
        self.assertNotIn(0, order)
        self.assertEqual(order, sorted(order))
        # Lookup within range returns a valid hit; out of range -> UNASSIGNED
        hit = mapper.get_dermatome_for_point(0)
        self.assertIn(hit.derm_id, mapper.id_to_name)
        oob = mapper.get_dermatome_for_point(len(mapper.derm_map) + 100)
        self.assertEqual(oob.derm_id, 0)

    def test_male_mapper_loads(self):
        self._check_mapper(config.get_male_model_info())

    def test_female_mapper_loads(self):
        self._check_mapper(config.get_female_model_info())


if __name__ == "__main__":
    unittest.main(verbosity=2)