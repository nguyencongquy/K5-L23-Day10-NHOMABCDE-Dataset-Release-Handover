import json
import tempfile
import unittest
from pathlib import Path

from scripts import pngutil
from validator import labelmatch


class LabelMatchTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.delivery = Path(temp.name)
        for folder in ("images", "labels", "masks"):
            (self.delivery / folder).mkdir()
        self.images = []
        self.annotations = []
        self.items = {}
        (self.delivery / "classes.txt").write_text("0 person\n1 fire hydrant\n", encoding="utf-8")

    def add_image(self, name, labels, regions):
        image_id = len(self.images) + 1
        self.images.append({"id": image_id, "file_name": f"{name}.jpg", "width": 100, "height": 100})
        paths = {"image": f"images/{name}.jpg", "label": f"labels/{name}.txt", "mask": f"masks/{name}.png"}
        self.items[name] = paths
        (self.delivery / paths["image"]).touch()
        (self.delivery / paths["label"]).write_text(labels, encoding="utf-8")
        rgb = bytearray(100 * 100 * 3)
        segments = []
        for segment_id, category, bbox, crowd in regions:
            x, y, w, h = bbox
            for row in range(y, y + h):
                offset = (row * 100 + x) * 3
                rgb[offset : offset + w * 3] = bytes(pngutil.segment_rgb(segment_id)) * w
            segments.append({
                "id": segment_id, "category_id": category, "bbox": bbox, "iscrowd": crowd,
                "area": 1,  # the overlap must use the actual PNG count
            })
        self.annotations.append({"image_id": image_id, "file_name": f"{name}.png", "segments_info": segments})
        pngutil.write_rgb(self.delivery / paths["mask"], 100, 100, rgb)

    def build(self):
        for name, data in {
            "manifest.json": {"items": self.items},
            "panoptic.json": {
                "images": list(reversed(self.images)),
                "annotations": self.annotations,
                "categories": [
                    {"id": 1, "name": "person", "isthing": 1},
                    {"id": 11, "name": "fire hydrant", "isthing": 1},
                    {"id": 104, "name": "grass", "isthing": 0},
                ],
            },
        }.items():
            (self.delivery / name).write_text(json.dumps(data), encoding="utf-8")
        return labelmatch.build_matches(self.delivery)

    def test_one_segment_keeps_both_box_overlaps_and_uses_class_names(self):
        self.add_image(
            "opaque_A",
            "0 0.25 0.50 0.30 0.40\n0 0.65 0.50 0.30 0.40\n",
            [(70001, 1, (10, 30, 70, 40), 0)],
        )
        matches = self.build()
        item = matches["opaque_A"]
        segment, = item["segments"]
        self.assertEqual(item["file_name"], "opaque_A.jpg")
        self.assertEqual(item["boxes"][0]["bbox"], (10, 30, 40, 70))
        self.assertEqual(item["boxes"][0]["class_name"], segment["class_name"])
        self.assertEqual((segment["id"], segment["area"]), (70001, 2800))
        self.assertEqual([pair["box_index"] for pair in segment["overlaps"]], [0, 1])
        self.assertEqual([pair["intersection_pixels"] for pair in segment["overlaps"]], [1200, 1200])
        self.assertTrue(all(pair["box_coverage"] == 1 for pair in segment["overlaps"]))
        self.assertEqual(labelmatch.find_candidates(matches), [])

    def test_disagreement_and_missing_emit_review_evidence(self):
        self.add_image("wrong_class", "0 0.3 0.3 0.4 0.4\n", [(12, 11, (10, 10, 40, 40), 0)])
        self.add_image("empty", "", [
            (32, 1, (10, 10, 30, 30), 0),
            (33, 1, (42, 10, 10, 10), 0),
            (34, 1, (55, 10, 30, 30), 1),
            (35, 104, (10, 55, 30, 30), 0),
        ])
        missing, disagreement = labelmatch.find_candidates(self.build())
        self.assertEqual((missing["type"], missing["image"], missing["segment_id"]), ("missing_box", "empty", 32))
        self.assertEqual(disagreement["type"], "class_disagreement")
        self.assertEqual(disagreement["box_class"], "person")
        self.assertEqual(disagreement["segment_class"], "fire hydrant")
        self.assertAlmostEqual(disagreement["bbox_iou"], 1.0)
        self.assertEqual(disagreement["segment_coverage"], 1.0)

    def test_absent_label_and_unknown_class_do_not_look_like_missing_box(self):
        for name in ("unavailable", "invalid_id"):
            self.add_image(name, "99 0.3 0.3 0.4 0.4\n", [(42, 1, (10, 10, 40, 40), 0)])
        (self.delivery / self.items["unavailable"]["label"]).unlink()
        matches = self.build()
        self.assertEqual(list(matches), ["invalid_id"])
        self.assertEqual(labelmatch.find_candidates(matches), [])
