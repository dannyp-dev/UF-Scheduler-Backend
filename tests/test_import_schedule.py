import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pythonScripts import import_schedule


def sample(meetings):
    return {
        "code": "MAC2311",
        "name": "Calculus 1",
        "termInd": " ",
        "sections": [{
            "classNumber": 12345,
            "sectWeb": "PC",
            "meetTimes": meetings,
        }],
    }


class ImportScheduleTests(unittest.TestCase):
    def test_raw_pages_merge_sections_and_convert_times(self):
        meeting = {
            "meetDays": ["M", "W"],
            "meetTimeBegin": "9:35 AM",
            "meetTimeEnd": "10:25 AM",
        }
        result = import_schedule.prepare_courses([
            {"COURSES": [sample([])]},
            {"COURSES": [sample([meeting])]},
        ])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sections"][0]["meetTimes"][0]["meetTimeBegin"], "09:35")
        self.assertEqual(import_schedule.meeting_coverage(result), (1, 1))

    def test_empty_times_do_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            course_dir = Path(folder)
            source = course_dir / "export.json"
            destination = course_dir / "UF_Imported_26_fall_final.json"
            destination.write_text("previous valid data", encoding="utf-8")
            source.write_text(json.dumps([sample([])]), encoding="utf-8")
            with patch.object(import_schedule, "COURSES_DIR", course_dir):
                with self.assertRaisesRegex(ValueError, "meeting times"):
                    import_schedule.import_export(source, "26", "fall")
            self.assertEqual(destination.read_text(encoding="utf-8"), "previous valid data")

    def test_valid_export_writes_complete_file(self):
        with tempfile.TemporaryDirectory() as folder:
            course_dir = Path(folder)
            source = course_dir / "export.json"
            source.write_text(json.dumps([sample([{
                "meetDays": ["M"],
                "meetTimeBegin": "13:55",
                "meetTimeEnd": "14:45",
            }])]), encoding="utf-8")
            with patch.object(import_schedule, "COURSES_DIR", course_dir):
                destination, count, timed, total = import_schedule.import_export(source, "26", "fall")
            self.assertEqual((count, timed, total), (1, 1, 1))
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))[0]["sections"][0]["meetTimes"][0]["meetTimeBegin"], "13:55")


if __name__ == "__main__":
    unittest.main()
