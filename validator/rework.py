"""Chuẩn bị ảnh/nhãn detection cho v2 và tạo hàng đợi gán nhãn lại."""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


# Chỉ các lỗi làm nhãn detection hoặc ảnh không dùng được mới bị loại khỏi v2.
# Lỗi panoptic và metadata/hash được xử lý riêng, không giao gán lại detection.
DETECTION_REWORK_TYPES = {
    "missing_image", "invalid_class", "bbox_out_of_bounds", "duplicate_box",
    "class_swap", "bbox_drift", "missing_box",
}


def _safe_path(root: Path, relative: str) -> Path | None:
    """Chỉ cho phép đọc file nằm bên trong delivery, kể cả khi có symlink."""
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


def prepare_v2_inputs(delivery: Path, errors_file: Path, v2_dir: Path) -> dict[str, int]:
    """Tạo bản nháp phần ảnh/nhãn của v2 và rework_queue.csv.

    `errors_file` phải là errors.json cuối đã được review. Thư mục v2 có sẵn
    sẽ không bị ghi đè. Ảnh lỗi detection/thiếu ảnh được đưa vào hàng đợi;
    ảnh còn lại được chép nguyên trạng. Lỗi panoptic và lỗi metadata/hash vẫn
    ở v2 để xử lý theo quy trình tương ứng.
    """
    delivery, errors_file, v2_dir = Path(delivery).resolve(), Path(errors_file).resolve(), Path(v2_dir).resolve()
    # Bảo vệ bản v2 cũ: helper không xóa hoặc ghi đè đầu ra đã tồn tại.
    if v2_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing v2 directory: {v2_dir}")
    # Đọc manifest, metadata, jobs để biết đường dẫn file và người phụ trách ảnh.
    payload = json.loads(errors_file.read_text(encoding="utf-8"))
    errors = payload.get("errors", [])
    manifest = json.loads((delivery / "manifest.json").read_text(encoding="utf-8"))["items"]
    metadata = json.loads((delivery / "metadata.json").read_text(encoding="utf-8"))["items"]
    meta_by_image = {str(row["image"]): row for row in metadata}
    with (delivery / "jobs.csv").open(encoding="utf-8", newline="") as handle:
        jobs = {row["job_id"]: row for row in csv.DictReader(handle)}

    # Gom lỗi detection theo ảnh; các target kiểu scene_id không vào rework queue.
    by_image: dict[str, set[str]] = defaultdict(set)
    for error in errors:
        kind, target = str(error["type"]), str(error["target"])
        if kind in DETECTION_REWORK_TYPES and target in manifest:
            by_image[target].add(kind)

    # Tạo cấu trúc v2. Ảnh/nhãn có lỗi detection được giữ ngoài bản giao.
    (v2_dir / "images").mkdir(parents=True)
    (v2_dir / "labels").mkdir()
    for image, item in manifest.items():
        if image in by_image:
            continue
        # Chép bytes gốc, không sửa tay nhãn và không thay đổi delivery v1.
        for key, subdir, suffix in (("image", "images", ".jpg"), ("label", "labels", ".txt")):
            source = _safe_path(delivery, item[key])
            if source is None or not source.is_file():
                continue
            shutil.copyfile(source, v2_dir / subdir / f"{image}{suffix}")

    # Tra annotator/reviewer qua metadata -> job_id -> jobs.csv.
    queue = []
    for image, kinds in sorted(by_image.items()):
        row = meta_by_image.get(image)
        if row is None:
            raise ValueError(f"no metadata row for rework image {image}")
        job = jobs.get(str(row["job_id"]))
        if job is None:
            raise ValueError(f"no jobs.csv entry for {image}: {row['job_id']}")
        queue.append({
            "image": image,
            "type": ";".join(sorted(kinds)),
            "annotator": job["annotator"],
            "reviewer": job["reviewer"],
            "action": "relabel_detection",
        })
    # Ghi đúng các cột mà check_handover.py và nhóm bàn giao yêu cầu.
    with (v2_dir / "rework_queue.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["image", "type", "annotator", "reviewer", "action"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(queue)

    # Trả số lượng để người gọi đối chiếu nhanh trước khi tạo manifest/summary.
    return {
        "rework_images": len(queue),
        "v2_images": len(list((v2_dir / "images").glob("*.jpg"))),
        "v2_labels": len(list((v2_dir / "labels").glob("*.txt"))),
    }
