# Validator của nhóm

Chạy từ thư mục gốc repo. Trên Windows PowerShell, dùng `py` thay cho `python3`.

```sh
python3 validator/validate.py runs/r3007/delivery --out runs/r3007/rules.json --candidates runs/r3007/candidates.json
```

Validator chỉ đọc thư mục delivery được truyền vào, dùng thư viện chuẩn và chạy ngoại tuyến. Xem [GUIDE.md](../GUIDE.md) và [RULES.md](../RULES.md).

## Giao diện cho nhóm

| Người | File và hàm |
|---|---|
| Trần Phạm Hoàng Phong | `rulefiles.py` có `find_errors(delivery)` để kiểm file và metadata. |
| Trần Đình Quang Vinh | `rulelabels.py` có `find_errors(delivery)` để kiểm nhãn YOLO và panoptic. |
| Phùng Danh Khoa | `labelmatch.py` có `build_matches(delivery)` để chuẩn bị dữ liệu ghép theo ảnh và `find_candidates(matches)` để tìm lệch lớp, thiếu box. |
| Đinh Quốc Tiến | `maskchecks.py` có `find_candidates(matches)` để tìm box lệch và vật thể bị gộp. Khoa và Tiến thống nhất cấu trúc `matches` trước khi viết hai hàm kiểm. |
| Nguyễn Công Quý | `validate.py` gọi các hàm, gộp lỗi luật và ghi hai file JSON. |

`delivery` là một `pathlib.Path`. Mỗi hàm `find_errors` trả về danh sách mục có `type` và `target`. Với `scene_leak`, `target` là mã cảnh. Các lỗi còn lại dùng tên ảnh bỏ đuôi.

Hai hàm `find_candidates` dùng chung kết quả ghép và trả về danh sách mục có `image` (tên ảnh bỏ đuôi), `type` và thông tin hỗ trợ xem ảnh khi có. Có thể dùng `class_disagreement` cho ca lệch lớp chưa xác định nguồn sai. Khi xem ảnh, chọn `class_swap` hoặc `category_swap` để ghi lỗi đã xác nhận.

`--out` ghi lỗi luật. Thêm `--candidates` để chạy bước đối chiếu và ghi hàng đợi xem ảnh. Sau khi cả nhóm xem ảnh, gộp kết quả:

```sh
python3 scripts/merge_review.py --rules runs/r3007/rules.json --review runs/r3007/review_log.csv --out runs/r3007/errors.json
```

## Dữ liệu ghép cho `maskchecks`

Mẫu một ảnh giả lập có segment phủ hai box.

```python
{
    "demo_001": {
        "image": "demo_001", "file_name": "demo_001.jpg",
        "width": 200, "height": 100, "mask_path": Path("/.../delivery/masks/demo_001.png"),
        "boxes": [
            {"index": 0, "class_name": "person", "bbox": (20, 10, 70, 90)},
            {"index": 1, "class_name": "person", "bbox": (80, 12, 132, 90)},
        ],
        "segments": [{
            "id": 70001, "class_name": "person", "bbox": (20, 10, 132, 90),
            "area": 5000,
            "overlaps": [
                {"box_index": 0, "bbox_iou": 0.446, "intersection_pixels": 2400,
                 "segment_coverage": 0.48, "box_coverage": 0.60},
                {"box_index": 1, "bbox_iou": 0.453, "intersection_pixels": 2500,
                 "segment_coverage": 0.50, "box_coverage": 0.616},
            ],
        }],
    },
}
```

- Khoá ảnh và `image` là tên bỏ đuôi theo manifest. `bbox` luôn là `(x_min, y_min, x_max, y_max)` theo pixel, gốc ở góc trên trái. `box_index` tra thẳng vào `boxes`; giữ mọi cặp giao bbox, kể cả cặp khác lớp và cặp có 0 pixel giao.
- `segments` gồm các thing có tên trong `classes.txt`, bỏ crowd. `area` đếm trên PNG. `segment_coverage` chia cho tổng pixel segment, `box_coverage` chia cho số tâm pixel trong box.
- Nếu cần đọc mask thô, dùng `scripts/pngutil.py`: `w, h, rgb = read_rgb(mask_path)`, rồi `segment_id(rgb, 3 * (y * w + x))` ở pixel `(x, y)`. Cách đọc này không cần Pillow.
- Kết quả `find_candidates` trả về list các dict có `image` và `type` như `validator/README.md`.

Box có `class_name=None` khi ID YOLO không có trong `classes.txt`. Mọi hộp
được cắt theo giới hạn ảnh. Ngoài các cặp giao bbox, `overlaps` giữ cả cặp có
pixel giao khi bbox trong JSON khác biên thật của mask.

`labelmatch.find_candidates(matches)` có thể trả về đầu ra sau trên dữ liệu giả lập.

```json
{
  "candidates": [
    {
      "type": "class_disagreement", "image": "demo_002",
      "segment_id": 70001, "segment_class": "person", "segment_bbox": [20, 10, 70, 90],
      "segment_area": 4000, "box_index": 0, "box_class": "bicycle",
      "box_bbox": [20, 10, 70, 90], "bbox_iou": 1.0,
      "intersection_pixels": 4000, "segment_coverage": 1.0, "box_coverage": 1.0
    },
    {
      "type": "missing_box", "image": "demo_003", "segment_id": 70002,
      "segment_class": "person", "segment_bbox": [80, 12, 132, 90], "segment_area": 4056
    }
  ]
}
```
