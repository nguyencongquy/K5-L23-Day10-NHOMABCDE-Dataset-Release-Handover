"""Tìm ứng viên box lệch và instance bị gộp bằng pixel mask.

Đầu vào là danh sách dữ liệu ghép theo ảnh. Mỗi mục có image, width, height,
mask_pixels (buffer RGB), boxes (bbox_xyxy theo pixel và tên lớp), segments
(ID, lớp, area, isthing, iscrowd). ID pixel theo COCO: R + G*256 + B*65536.
Hàm chỉ tạo ứng viên để con người xem ảnh xác nhận, không tự kết luận lỗi.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import pngutil  # noqa: E402

# Các ngưỡng bên dưới chỉ tạo ứng viên. Cần đo trên calib sạch và để người review
# mở ảnh xác nhận; không dùng riêng ngưỡng để kết luận annotation sai.
MIN_SEGMENT_PIXELS = 1024
# Nếu box cùng lớp chứa ít hơn 75% pixel segment, box có thể bị lệch.
DRIFT_MIN_COVERAGE = 0.75
# Với merge, mỗi box phải phủ ít nhất 25% diện tích pixel của cùng segment.
MERGE_MIN_SEGMENT_SHARE = 0.25
# Bỏ qua giao pixel quá nhỏ.
MERGE_MIN_PIXELS = 32
# Segment phải chiếm ít nhất 20% diện tích mỗi box; loại box lớn chỉ bao trùm vật.
MERGE_MIN_BOX_SHARE = 0.20
# Hai box phải đủ tách biệt để không xem box trùng/bao nhau là hai instance.
MERGE_MAX_BOX_IOU = 0.40


def _pixel_counts_in_box(
    pixels: bytes | bytearray,
    width: int,
    height: int,
    bbox_xyxy: Iterable[float],
    wanted_ids: set[int],
) -> Counter[int]:
    """Đếm pixel của từng segment nằm trong box tọa độ pixel [x1,y1,x2,y2)."""
    x1, y1, x2, y2 = map(float, bbox_xyxy)
    # Cắt box vào biên ảnh trước khi đọc buffer để không truy cập ngoài mask.
    left = max(0, min(width, int(x1)))
    top = max(0, min(height, int(y1)))
    right = max(left, min(width, int(x2 + 0.999999)))
    bottom = max(top, min(height, int(y2 + 0.999999)))
    found: Counter[int] = Counter()
    for y in range(top, bottom):
        # Mỗi pixel RGB chiếm 3 byte; segment_id đổi 3 byte thành ID COCO.
        offset = (y * width + left) * 3
        for _x in range(left, right):
            sid = pngutil.segment_id(pixels, offset)
            if sid in wanted_ids:
                found[sid] += 1
            offset += 3
    return found


def _bbox_iou(a: Iterable[float], b: Iterable[float]) -> float:
    """IoU hai box pixel; dùng để loại cặp box gần trùng nhau."""
    ax1, ay1, ax2, ay2 = map(float, a)
    bx1, by1, bx2, by2 = map(float, b)
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(
        0.0, min(ay2, by2) - max(ay1, by1)
    )
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return intersection / max(1e-12, area_a + area_b - intersection)


def _image_candidates(match: dict[str, Any]) -> list[dict[str, Any]]:
    """Tìm ứng viên của một ảnh; dùng overlaps dựng sẵn hoặc tự đếm mask thô."""
    image = str(match["image"])
    boxes = list(match.get("boxes", []))
    segments = list(match.get("segments", []))
    # Ảnh không có segment thing thì không có ứng viên cho hai loại lỗi này.
    # Trả sớm cũng tránh yêu cầu mask_pixels khi adapter chỉ có mask_path.
    if not segments:
        return []

    # Khoa gửi sẵn overlaps, gồm mọi cặp box-segment cần giữ lại. Dùng lại số
    # liệu đó để không phải đọc PNG và không làm mất ca pixel giao nhưng bbox lệch.
    has_precomputed = any("overlaps" in segment for segment in segments)
    if has_precomputed:
        # Chuẩn hóa bảng tra theo (chỉ số box, ID segment). Bộ ghép của Khoa đã
        # tính giao pixel và hai coverage; giữ luôn bbox_iou để tiện xem bằng chứng.
        overlap_counts: dict[tuple[int, int], tuple[int, float, float, float]] = {}
        for segment in segments:
            sid = int(segment["id"])
            for overlap in segment.get("overlaps", []):
                bi = int(overlap["box_index"])
                overlap_counts[(bi, sid)] = (
                    int(overlap.get("intersection_pixels", 0)),
                    float(overlap.get("segment_coverage", 0.0)),
                    float(overlap.get("box_coverage", 0.0)),
                    float(overlap.get("bbox_iou", 0.0)),
                )
    else:
        # Tương thích với labelmatch.build_matches() hiện có trong repo.
        # Nếu chưa có overlaps, đọc buffer RGB và tự đếm pixel mask trong từng box.
        width, height = int(match["width"]), int(match["height"])
        pixels = match["mask_pixels"]
        if width <= 0 or height <= 0 or len(pixels) != width * height * 3:
            raise ValueError(f"{image}: mask_pixels must be width*height*3 RGB bytes")
        ids = {int(s["id"]) for s in segments}
        overlap_counts = {}
        for bi, box in enumerate(boxes):
            bbox = box.get("bbox_xyxy", box.get("bbox"))
            counts = _pixel_counts_in_box(pixels, width, height, bbox, ids)
            x1, y1, x2, y2 = map(float, bbox)
            box_area = max(1.0, (x2 - x1) * (y2 - y1))
            for sid, count in counts.items():
                segment = next(s for s in segments if int(s["id"]) == sid)
                area = max(1, int(segment.get("area", 0)))
                seg_cov = count / area
                box_cov = count / box_area
                bbox_iou = _bbox_iou(bbox, segment.get("bbox", bbox))
                overlap_counts[(bi, sid)] = (count, seg_cov, box_cov, bbox_iou)

    # Chỉ xét vật thể thing đủ lớn. Crowd/stuff không có một box detection
    # tương ứng theo quy ước của bài.
    segments = [
        s for s in segments
        if s.get("isthing", True) and not s.get("iscrowd", False)
        and int(s.get("area", 0)) >= MIN_SEGMENT_PIXELS
    ]
    result: list[dict[str, Any]] = []
    for segment in segments:
        sid = int(segment["id"])
        category = segment.get("class_name")
        area = int(segment["area"])
        same_class = [
            (bi, box) for bi, box in enumerate(boxes)
            if category is not None and box.get("class_name") == category
        ]
        substantial = []
        overlaps = []
        for bi, box in same_class:
            # Thiếu cặp trong bảng nghĩa là box không giao segment nên coverage = 0.
            count, segment_share, box_share, bbox_iou = overlap_counts.get(
                (bi, sid), (0, 0.0, 0.0, 0.0)
            )
            # Skip pairs with no pixel or bbox intersection.
            if count <= 0 and bbox_iou <= 0:
                continue
            overlaps.append((bi, box, count, segment_share, box_share, bbox_iou))
            # Để nghi instance_merge, giao pixel phải đáng kể so với cả mask lẫn box.
            if (count >= MERGE_MIN_PIXELS
                    and segment_share >= MERGE_MIN_SEGMENT_SHARE
                    and box_share >= MERGE_MIN_BOX_SHARE):
                substantial.append((bi, box, count, segment_share, box_share, bbox_iou))

        # Hai box detection cần phủ các phần khác nhau của cùng segment và phải
        # tách nhau đủ rõ. Nhờ vậy không nhầm box trùng hoặc box bao quanh cùng
        # một vật thể thành trường hợp nhiều instance bị gộp.
        # Loại cặp box chồng quá nhiều: thường là hai box mô tả cùng một vật.
        pairs = [
            (a, b) for a, b in combinations(substantial, 2)
            if _bbox_iou(
                a[1].get("bbox_xyxy", a[1].get("bbox")),
                b[1].get("bbox_xyxy", b[1].get("bbox")),
            ) < MERGE_MAX_BOX_IOU
        ]
        if pairs:
            # Chọn cặp có mức phủ tối thiểu tốt nhất để bằng chứng cho cả hai box mạnh.
            first, second = max(
                pairs,
                key=lambda pair: (
                    min(pair[0][3], pair[1][3]),
                    min(pair[0][4], pair[1][4]),
                ),
            )
            result.append({
                "image": image,
                "type": "instance_merge",
                "box_indices": [
                    int(first[1].get("index", first[0])),
                    int(second[1].get("index", second[0])),
                ],
                "segment_ids": [sid],
                "evidence": {
                    "segment_area": area,
                    "box_pixel_intersections": [first[2], second[2]],
                    "segment_share_per_box": [round(first[3], 4), round(second[3], 4)],
                    "box_share_per_box": [round(first[4], 4), round(second[4], 4)],
                    "box_iou": round(_bbox_iou(
                        first[1].get("bbox_xyxy", first[1].get("bbox")),
                        second[1].get("bbox_xyxy", second[1].get("bbox")),
                    ), 4),
                },
            })
            continue

        # Box lệch cần có box cùng lớp để đối chiếu. Nếu không có box cùng lớp,
        # phần kiểm tra missing_box sẽ xử lý; độ phủ mask thấp gợi ý box bị lệch.
        if overlaps:
            # Nếu không có cặp merge thuyết phục, kiểm tra box cùng lớp phủ mask tốt nhất.
            bi, box, count, coverage, _box_coverage, _bbox_iou_value = max(
                overlaps, key=lambda item: item[3]
            )
            if coverage < DRIFT_MIN_COVERAGE:
                # Box cùng lớp không chứa đủ pixel của segment: xếp vào hàng đợi
                # xem ảnh; che khuất/crowd có thể giải thích bất đồng này.
                result.append({
                    "image": image,
                    "type": "bbox_drift",
                    "box_indices": [int(box.get("index", bi))],
                    "segment_ids": [sid],
                    "evidence": {
                        "segment_area": area,
                        "pixels_inside_box": count,
                        "segment_coverage": round(coverage, 4),
                    },
                })
    return result


def find_candidates(matches: Iterable[dict[str, Any]] | dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Trả ứng viên bbox_drift/instance_merge cho mọi ảnh, chưa phải lỗi xác nhận.

    Nhận cả mapping {image_stem: match} mà Khoa gửi lẫn iterable của adapter cũ.
    Mỗi ứng viên có image, type, các box/segment liên quan và evidence để review.
    """
    findings: list[dict[str, Any]] = []
    # Khoa gửi mapping image_stem -> dữ liệu ảnh; vẫn nhận iterable cũ của repo.
    rows = matches.values() if isinstance(matches, dict) else matches
    for match in rows:
        findings.extend(_image_candidates(match))
    return findings

