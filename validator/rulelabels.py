
from pathlib import Path
import json


def find_errors(delivery):
    """Validate YOLO labels and panoptic annotations."""
    delivery = Path(delivery)
    errors = []

    # Load image dimensions
    with (delivery / "panoptic.json").open(encoding="utf-8") as f:
        panoptic = json.load(f)

    image_sizes = {
        Path(img["file_name"]).stem: (
            img["width"],
            img["height"]
        )
        for img in panoptic["images"]
    }

    # PASS 1: YOLO validation
    for label_file in sorted((delivery / "labels").glob("*.txt")):
        image_id = label_file.stem

        if image_id not in image_sizes:
            continue

        img_width, img_height = image_sizes[image_id]
        boxes = []

        for line in label_file.read_text(
            encoding="utf-8"
        ).splitlines():

            parts = line.split()

            if len(parts) != 5:
                continue

            try:
                cls = int(parts[0])
                x, y, w, h = map(float, parts[1:])
            except ValueError:
                continue

            # Rule 1: invalid_class
            if not (0 <= cls <= 79):
                errors.append({
                    "type": "invalid_class",
                    "target": image_id
                })

            # Rule 2: bbox_out_of_bounds
            xmin = x - w / 2
            xmax = x + w / 2
            ymin = y - h / 2
            ymax = y + h / 2

            EPS = 1e-5

            if (
                xmin < -EPS
                or ymin < -EPS
                or xmax > 1 + EPS
                or ymax > 1 + EPS
                or w <= 0
                or h <= 0
            ):
                errors.append({
                    "type": "bbox_out_of_bounds",
                    "target": image_id
                })

            boxes.append((cls, x, y, w, h))

        # Rule 3: duplicate_box
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                cls1, x1, y1, w1, h1 = boxes[i]
                cls2, x2, y2, w2, h2 = boxes[j]

                if cls1 != cls2:
                    continue

                dx = abs(x1 - x2) * img_width
                dy = abs(y1 - y2) * img_height
                dw = abs(w1 - w2) * img_width
                dh = abs(h1 - h2) * img_height

                if (
                    dx <= 2
                    and dy <= 2
                    and dw <= 2
                    and dh <= 2
                ):
                    errors.append({
                        "type": "duplicate_box",
                        "target": image_id
                    })
                    break

    # Remove duplicate findings
    unique = {
        (item["type"], item["target"])
        for item in errors
    }

    return [
        {"type": kind, "target": target}
        for kind, target in sorted(unique)
    ]
