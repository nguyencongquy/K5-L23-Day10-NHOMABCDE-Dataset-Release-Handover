"""Prepare YOLO/panoptic matches and propose cases for visual review."""

from __future__ import annotations

import json
import sys
import zlib
from collections import Counter
from math import ceil, isfinite
from pathlib import Path
from struct import error as StructError
from typing import TypedDict

# Support both `python validator/validate.py` and imports from the repo root.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import pngutil


Bbox = tuple[float, float, float, float]
MIN_CLASS_IOU = 0.50
MIN_CLASS_COVERAGE = 0.75
MIN_BOX_IOU = 0.20
MIN_BOX_COVERAGE = 0.25
MIN_MISSING_PIXELS = 256
MIN_MISSING_IMAGE_FRACTION = 0.005


class Box(TypedDict):
    index: int
    class_name: str | None
    bbox: Bbox


class Overlap(TypedDict):
    box_index: int
    bbox_iou: float
    intersection_pixels: int
    segment_coverage: float
    box_coverage: float


class Segment(TypedDict):
    id: int
    class_name: str
    bbox: Bbox
    area: int
    overlaps: list[Overlap]


class ImageMatches(TypedDict):
    image: str
    file_name: str
    width: int
    height: int
    mask_path: Path
    boxes: list[Box]
    segments: list[Segment]


def _delivery_file(delivery: Path, name: str) -> Path:
    path = (delivery / name).resolve()
    if not path.is_relative_to(delivery):
        raise ValueError(f"Path outside delivery: {name}")
    return path


def _read_boxes(path: Path, names: dict[int, str], width: int, height: int) -> list[Box]:
    boxes: list[Box] = []
    for row in path.read_text(encoding="utf-8").splitlines():
        fields = row.split()
        if len(fields) != 5:
            continue
        try:
            class_id = int(fields[0])
            cx, cy, w, h = map(float, fields[1:])
        except ValueError:
            continue
        if not all(map(isfinite, (cx, cy, w, h))) or w <= 0 or h <= 0:
            continue
        bbox = (
            max(0.0, (cx - w / 2) * width),
            max(0.0, (cy - h / 2) * height),
            min(width, (cx + w / 2) * width),
            min(height, (cy + h / 2) * height),
        )
        if bbox[0] < bbox[2] and bbox[1] < bbox[3]:
            boxes.append({"index": len(boxes), "class_name": names.get(class_id), "bbox": bbox})
    return boxes


def _iou(a: Bbox, b: Bbox) -> float:
    x = min(a[2], b[2]) - max(a[0], b[0])
    y = min(a[3], b[3]) - max(a[1], b[1])
    if x <= 0 or y <= 0:
        return 0.0
    intersection = x * y
    return intersection / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection)


def _pixels_in_boxes(
    ids: list[int], boxes: list[Box], width: int
) -> list[tuple[int, Counter[int]]]:
    counts = []
    for box in boxes:
        # x+0.5, y+0.5 are the centers of pixels in a half-open box.
        x0, y0, x1, y1 = (ceil(value - 0.5) for value in box["bbox"])
        counts.append((
            (x1 - x0) * (y1 - y0),
            Counter(
                segment_id
                for y in range(y0, y1)
                for segment_id in ids[y * width + x0 : y * width + x1]
            ),
        ))
    return counts


def _read_segments(
    info: list[dict], thing_names: dict[int, str], boxes: list[Box],
    mask_path: Path, width: int, height: int,
) -> list[Segment]:
    mask_width, mask_height, rgb = pngutil.read_rgb(mask_path)
    if (mask_width, mask_height) != (width, height) or len(rgb) != width * height * 3:
        raise ValueError(f"Mask size differs from image size: {mask_path}")
    ids = [r + 256 * g + 65536 * b for r, g, b in zip(rgb[::3], rgb[1::3], rgb[2::3])]
    areas = Counter(ids)
    box_counts = _pixels_in_boxes(ids, boxes, width)
    segments: list[Segment] = []
    for entry in info:
        name = thing_names.get(entry["category_id"])
        segment_id = entry["id"]
        area = areas[segment_id]
        if not name or entry.get("iscrowd") or not segment_id or not area:
            continue
        x, y, w, h = entry["bbox"]
        bbox = (x, y, x + w, y + h)
        overlaps: list[Overlap] = []
        for box, (box_area, counts) in zip(boxes, box_counts):
            iou = _iou(bbox, box["bbox"])
            pixels = counts[segment_id]
            if iou or pixels:
                overlaps.append({
                    "box_index": box["index"],
                    "bbox_iou": iou,
                    "intersection_pixels": pixels,
                    "segment_coverage": pixels / area,
                    "box_coverage": pixels / box_area if box_area else 0.0,
                })
        segments.append({
            "id": segment_id, "class_name": name, "bbox": bbox, "area": area, "overlaps": overlaps,
        })
    return segments


def build_matches(delivery: Path) -> dict[str, ImageMatches]:
    """Read only the delivery. Index image records by the manifest's extensionless name."""
    delivery = Path(delivery).resolve()
    manifest = json.loads(_delivery_file(delivery, "manifest.json").read_text(encoding="utf-8"))
    panoptic = json.loads(_delivery_file(delivery, "panoptic.json").read_text(encoding="utf-8"))
    names = {}
    for row in _delivery_file(delivery, "classes.txt").read_text(encoding="utf-8").splitlines():
        if row.strip():
            key, name = row.split(maxsplit=1)
            names[int(key)] = name.strip()
    detection_names = set(names.values())
    thing_names = {
        cat["id"]: cat["name"] for cat in panoptic["categories"]
        if cat["isthing"] and cat["name"] in detection_names
    }
    images = {image["file_name"]: image for image in panoptic["images"]}
    annotations = {ann["image_id"]: ann["segments_info"] for ann in panoptic["annotations"]}
    matches: dict[str, ImageMatches] = {}
    for image, item in sorted(manifest["items"].items()):
        file_name = Path(item["image"]).name
        info = images.get(file_name)
        if not info or info["id"] not in annotations:
            continue
        width, height = info["width"], info["height"]
        if width <= 0 or height <= 0:
            continue
        try:
            if not _delivery_file(delivery, item["image"]).is_file():
                continue
            mask_path = _delivery_file(delivery, item["mask"])
            boxes = _read_boxes(_delivery_file(delivery, item["label"]), names, width, height)
            segments = _read_segments(annotations[info["id"]], thing_names, boxes, mask_path, width, height)
        except (OSError, ValueError, IndexError, StructError, zlib.error):
            # An unavailable image/label/mask is not evidence of an annotation error.
            continue
        matches[image] = {
            "image": image, "file_name": file_name, "width": width, "height": height,
            "mask_path": mask_path, "boxes": boxes, "segments": segments,
        }
    return matches


def _match_priority(overlap: Overlap, same_class: bool) -> tuple[float, float, bool]:
    return overlap["bbox_iou"], overlap["segment_coverage"], same_class


def find_candidates(matches: dict[str, ImageMatches]) -> list[dict]:
    """Emit class disagreements and missing-box candidates with evidence for reviewers."""
    candidates = []
    for image, item in matches.items():
        boxes = item["boxes"]
        best_for_box = {}
        for segment in item["segments"]:
            for overlap in segment["overlaps"]:
                index = overlap["box_index"]
                priority = _match_priority(overlap, boxes[index]["class_name"] == segment["class_name"])
                if index not in best_for_box or priority > best_for_box[index][0]:
                    best_for_box[index] = (priority, segment["id"])

        min_area = max(MIN_MISSING_PIXELS, MIN_MISSING_IMAGE_FRACTION * item["width"] * item["height"])
        for segment in item["segments"]:
            related = segment["overlaps"]
            best = max(
                related,
                key=lambda pair: _match_priority(
                    pair, boxes[pair["box_index"]]["class_name"] == segment["class_name"],
                ),
                default=None,
            )
            evidence = {
                "image": image, "segment_id": segment["id"], "segment_class": segment["class_name"],
                "segment_bbox": segment["bbox"], "segment_area": segment["area"],
            }
            if best is not None:
                box = boxes[best["box_index"]]
                if (
                    box["class_name"] is not None
                    and box["class_name"] != segment["class_name"]
                    and best_for_box[box["index"]][1] == segment["id"]
                    and best["bbox_iou"] >= MIN_CLASS_IOU
                    and best["segment_coverage"] >= MIN_CLASS_COVERAGE
                ):
                    candidates.append({
                        "type": "class_disagreement", **evidence, **best,
                        "box_bbox": box["bbox"], "box_class": box["class_name"],
                    })
                    continue

            if segment["area"] >= min_area and not any(
                pair["intersection_pixels"] > 0 and (
                    pair["bbox_iou"] >= MIN_BOX_IOU or pair["segment_coverage"] >= MIN_BOX_COVERAGE
                )
                for pair in related
            ):
                candidates.append({"type": "missing_box", **evidence})
    return candidates
