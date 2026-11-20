
"""Generate manifest.csv and label_summary.csv for YOLO release v2."""

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path


def sha256_file(path):
    """Calculate actual SHA-256 hash of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def generate_csv(release_dir, classes_file):
    release_dir = Path(release_dir)
    classes_file = Path(classes_file)

    images_dir = release_dir / "images"
    labels_dir = release_dir / "labels"

    if not images_dir.is_dir() or not labels_dir.is_dir():
        raise FileNotFoundError("Missing images/ or labels/ directory")

    classes = [
        name.strip()
        for name in classes_file.read_text(encoding="utf-8").splitlines()
    ]

    images = sorted(images_dir.glob("*.jpg"))
    labels = sorted(labels_dir.glob("*.txt"))

    image_ids = {file.stem for file in images}
    label_ids = {file.stem for file in labels}

    # Verify image-label pairs
    if image_ids != label_ids:
        raise ValueError(
            f"Image-label mismatch: "
            f"images_only={sorted(image_ids - label_ids)}, "
            f"labels_only={sorted(label_ids - image_ids)}"
        )

    # Count YOLO annotations before generating output
    counts = Counter()

    for label_file in labels:
        for line in label_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue

            parts = line.split()

            if len(parts) != 5:
                raise ValueError(f"Invalid YOLO line in {label_file}")

            class_id = int(parts[0])

            if not 0 <= class_id < len(classes):
                raise ValueError(
                    f"Invalid class ID {class_id} in {label_file}"
                )

            counts[classes[class_id]] += 1

    # Generate manifest.csv
    manifest_path = release_dir / "manifest.csv"

    with manifest_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["file", "sha256"])

        for file in sorted(images + labels):
            relative_path = file.relative_to(release_dir).as_posix()
            writer.writerow([relative_path, sha256_file(file)])

    # Generate label_summary.csv
    summary_path = release_dir / "label_summary.csv"

    with summary_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["class", "count"])

        for class_name in classes:
            if counts[class_name] > 0:
                writer.writerow([class_name, counts[class_name]])

        writer.writerow(["TOTAL", sum(counts.values())])

    print(f"Images: {len(images)}")
    print(f"Labels: {len(labels)}")
    print(f"Manifest entries: {len(images) + len(labels)}")
    print(f"Total annotations: {sum(counts.values())}")
    print(f"Created: {manifest_path}")
    print(f"Created: {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate release manifest and label summary"
    )

    parser.add_argument("release_dir")
    parser.add_argument("--classes", required=True)

    args = parser.parse_args()
    generate_csv(args.release_dir, args.classes)


if __name__ == "__main__":
    main()
