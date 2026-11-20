
"""
Day 10 - Dataset Release & Handover

Module: validator/rulelabels.py

Validate 5 annotation rules:
    YOLO:
        1. invalid_class
        2. bbox_out_of_bounds
        3. duplicate_box

    Panoptic:
        4. invalid_category_id
        5. thing_overlap

Public interface:
    find_errors(delivery) -> list[dict]

Each finding:
    {"type": "error_type", "target": "image_id"}

Only reads files inside delivery/.
"""

from pathlib import Path
from collections import Counter
import json
import sys


# --------------------------------------------------
# Import PNG utilities from the provided scripts/
# --------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pngutil import read_rgb, segment_id


# --------------------------------------------------
# Configuration
# --------------------------------------------------

NUM_CLASSES = 80

# Ignore tiny YOLO rounding errors.
BBOX_EPS = 1e-5

# Duplicate boxes must have nearly identical
# centers and sizes in pixel coordinates.
DUPLICATE_PIXEL_TOLERANCE = 2.0


# ==================================================
# MAIN FUNCTION
# ==================================================

def find_errors(delivery):
    """
    Find YOLO and Panoptic annotation errors.

    Args:
        delivery:
            Path to the dataset delivery directory.

    Returns:
        A list of dictionaries:
        [
            {"type": "invalid_class", "target": "000000000139"},
            ...
        ]

    The target is an image filename without extension.
    """

    delivery = Path(delivery)
    errors = []

    # --------------------------------------------------
    # Load panoptic.json
    # --------------------------------------------------

    panoptic_path = delivery / "panoptic.json"

    with panoptic_path.open(encoding="utf-8") as f:
        panoptic = json.load(f)

    # Image dimensions indexed by image stem.
    image_sizes = {
        Path(image["file_name"]).stem: (
            int(image["width"]),
            int(image["height"])
        )
        for image in panoptic["images"]
    }

    # ==================================================
    # PASS 1: YOLO VALIDATION
    # ==================================================

    labels_dir = delivery / "labels"

    for label_file in sorted(labels_dir.glob("*.txt")):

        image_id = label_file.stem

        if image_id not in image_sizes:
            continue

        img_width, img_height = image_sizes[image_id]

        boxes = []

        # ----------------------------------------------
        # Read YOLO annotation lines
        # ----------------------------------------------

        lines = label_file.read_text(
            encoding="utf-8"
        ).splitlines()

        for line in lines:

            parts = line.split()

            if len(parts) != 5:
                continue

            try:
                cls = int(parts[0])

                x, y, w, h = map(
                    float,
                    parts[1:]
                )

            except ValueError:
                continue

            # ==========================================
            # RULE 1: invalid_class
            # ==========================================

            if not (0 <= cls < NUM_CLASSES):

                errors.append({
                    "type": "invalid_class",
                    "target": image_id
                })

            # ==========================================
            # RULE 2: bbox_out_of_bounds
            # ==========================================

            xmin = x - w / 2
            xmax = x + w / 2

            ymin = y - h / 2
            ymax = y + h / 2

            if (
                xmin < -BBOX_EPS
                or ymin < -BBOX_EPS
                or xmax > 1 + BBOX_EPS
                or ymax > 1 + BBOX_EPS
                or w <= 0
                or h <= 0
            ):

                errors.append({
                    "type": "bbox_out_of_bounds",
                    "target": image_id
                })

            # Store box for duplicate detection.
            boxes.append((
                cls,
                x,
                y,
                w,
                h
            ))

        # ==============================================
        # RULE 3: duplicate_box
        # ==============================================

        duplicate_found = False

        for i in range(len(boxes)):

            if duplicate_found:
                break

            for j in range(i + 1, len(boxes)):

                cls1, x1, y1, w1, h1 = boxes[i]
                cls2, x2, y2, w2, h2 = boxes[j]

                # Must belong to the same class.
                if cls1 != cls2:
                    continue

                # Compare in pixel coordinates.
                dx = abs(x1 - x2) * img_width
                dy = abs(y1 - y2) * img_height

                dw = abs(w1 - w2) * img_width
                dh = abs(h1 - h2) * img_height

                if (
                    dx <= DUPLICATE_PIXEL_TOLERANCE
                    and dy <= DUPLICATE_PIXEL_TOLERANCE
                    and dw <= DUPLICATE_PIXEL_TOLERANCE
                    and dh <= DUPLICATE_PIXEL_TOLERANCE
                ):

                    errors.append({
                        "type": "duplicate_box",
                        "target": image_id
                    })

                    duplicate_found = True
                    break

    # ==================================================
    # PASS 2: PANOPTIC VALIDATION
    # ==================================================

    # Map category IDs to category metadata.
    categories = {
        int(category["id"]): category
        for category in panoptic["categories"]
    }

    for annotation in panoptic["annotations"]:

        image_id = Path(
            annotation["file_name"]
        ).stem

        segments = annotation.get(
            "segments_info",
            []
        )

        # ==============================================
        # RULE 4: invalid_category_id
        # ==============================================

        for segment in segments:

            category_id = int(
                segment["category_id"]
            )

            if category_id not in categories:

                errors.append({
                    "type": "invalid_category_id",
                    "target": image_id
                })

        # ==============================================
        # RULE 5: thing_overlap
        # ==============================================

        mask_path = (
            delivery
            / "masks"
            / annotation["file_name"]
        )

        if not mask_path.is_file():
            continue

        # Read 8-bit RGB PNG mask.
        width, height, pixels = read_rgb(mask_path)

        # Count actual pixels for each segment ID.
        # Each RGB pixel occupies 3 bytes.
        pixel_counts = Counter(
            segment_id(pixels, index)
            for index in range(0, len(pixels), 3)
        )

        for segment in segments:

            sid = int(segment["id"])

            category_id = int(
                segment["category_id"]
            )

            # Ignore background segment ID 0.
            if sid == 0:
                continue

            category = categories.get(
                category_id
            )

            # An invalid category is already reported
            # by invalid_category_id.
            if category is None:
                continue

            # Only inspect "thing" categories.
            if int(category.get("isthing", 0)) != 1:
                continue

            declared_area = int(
                segment["area"]
            )

            actual_area = pixel_counts.get(
                sid,
                0
            )

            # The mask contains fewer pixels
            # than the declared segment area.
            if actual_area < declared_area:

                errors.append({
                    "type": "thing_overlap",
                    "target": image_id
                })

    # ==================================================
    # REMOVE DUPLICATE FINDINGS
    # ==================================================

    unique = {
        (item["type"], item["target"])
        for item in errors
    }

    # Sort to make results deterministic.
    result = [
        {
            "type": error_type,
            "target": target
        }
        for error_type, target in sorted(unique)
    ]

    return result
