# Báo cáo nhóm <<XX>>

## 1. Số liệu luyện tập
- F1 theo seed (rule / cross_check / overall): <<seed: ... / ... / ...>>
- Tổng ứng viên của hai module trên lô sạch: chờ `maskchecks.py` của Tiến. Kết quả riêng của `labelmatch.py` đã đo bên dưới.
- Hàng đợi sau tích hợp trên seed luyện tập: <<... ảnh>>

### Đối chiếu lớp và box thiếu

Lô sạch `lab250_93435792165d` được tạo bằng
`python3 scripts/inject_release.py --seed 5 --no-faults --out runs/clean`.
Chạy `build_matches` và `labelmatch.find_candidates` trên đúng 50 ảnh của pool
`calib`. Dữ liệu ghép có 435 box YOLO, 436 segment thing không phải crowd
và 1.195 cặp box–segment. Ngưỡng mặc định cho **0 lệch lớp và 0 thiếu box**.
Trên seed luyện tập `3007` (`lab250_68efac8c866e`), module tạo **5 ứng viên
trên 5 ảnh**, gồm 4 bất đồng lớp và 1 box có thể thiếu. Đây là số dòng trong
hàng đợi máy sinh, trước khi thành viên mở ảnh và chọn kết luận.

| Cấu hình | Lệch lớp: IoU bbox / phủ segment | Thiếu box: diện tích mask tối thiểu | Box đủ khớp: IoU / phủ segment | Sạch: lệch lớp / thiếu box | 3007: lệch lớp / thiếu box |
|---|---|---|---|---|---|
| Thoáng | 0,40 / 65% | max(128 px, 0,25% ảnh) | 0,25 / 35% | 0 / 0 | 4 / 1 |
| Mặc định | 0,50 / 75% | max(256 px, 0,5% ảnh) | 0,20 / 25% | 0 / 0 | 4 / 1 |
| Chặt | 0,65 / 85% | max(512 px, 1% ảnh) | 0,15 / 18% | 0 / 0 | 4 / 1 |

Lệch lớp cần đủ cả hai ngưỡng và đây phải là cặp tốt nhất theo cả hai chiều.
IoU lọc cặp trùng vị trí yếu, còn tỷ lệ phủ kiểm lại pixel của vật trong box.
Với box thiếu, diện tích lấy từ PNG giúp giới hạn hàng đợi vào vật nhìn được.
Có pixel giao và đạt một trong hai ngưỡng ở cột “Box đủ khớp” thì giữ box đó
làm bằng chứng đã có nhãn, kể cả khi che khuất làm một trong hai chỉ số thấp.
Cả ba cấu hình cho cùng số ứng viên. Giữ mức giữa để dành chỗ cho sai khác tự
nhiên giữa hai bộ nhãn và vẫn cho người xem kiểm vật có kích thước vừa phải.
Thử nghiệm này đo khối lượng review theo ngưỡng, chưa có kết luận về recall.
Các lần chạy chỉ dùng `delivery/`.

## 2. Vì sao báo hết ứng viên làm F1 giảm?
<<Trả lời bằng số của nhóm.>>

## 3. Quyết định và lineage
<<QC v1 a/b, kết luận, vì sao R-021 phải xem lại hoặc train lại.>>

## 4. Hash chứng minh gì, không chứng minh gì?
<<>>

## 5. Truy vết
<<Tiêu chí tầng a/b, vì sao lấy guideline theo job.>>

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
<<>>
