# Báo cáo nhóm <<XX>>

## 1. Số liệu luyện tập
- F1 theo seed (rule / cross_check / overall): <<seed: ... / ... / ...>>
- Lô sạch sau tích hợp: **10 ứng viên trên 8/50 ảnh**.
- Seed luyện tập `3007` sau tích hợp: **54 ứng viên trên 37/250 ảnh**.

### Kết quả chạy chung

Tích hợp `labelmatch.py` ở commit `06f2a9f` với `maskchecks.py` của Tiến ở
commit `ec4a82f`. Mỗi lô gọi `build_matches` một lần rồi truyền cùng dữ liệu
cho hai hàm `find_candidates`, theo thứ tự của `validator/validate.py`.

| Lô | Ảnh đọc | Bất đồng lớp | Thiếu box | Box lệch | Gộp instance | Tổng ứng viên | Ảnh có ứng viên |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sạch | 50 | 0 | 0 | 0 | 10 | 10 | 8 |
| `3007` | 250 | 4 | 1 | 4 | 45 | 54 | 37 |

Phiên bản `ec4a82f` bỏ qua cặp box–segment có giao pixel và IoU đều bằng 0.
So với `0470360`, seed `3007` giảm một ứng viên box lệch, còn số ảnh cần xem
giữ ở 37.

Với ca mô phỏng một segment phủ hai box, hai module giữ ID `70001` và hai
chỉ số box `[0, 1]`. `maskchecks.py` tạo một ứng viên `instance_merge`, với
1.200 pixel giao cho mỗi box.

Hai phép kiểm của Tiến xét segment từ 1.024 pixel. Box cùng lớp có độ phủ
tốt nhất dưới 75% là ứng viên lệch. Với ứng viên gộp, mỗi box phải phủ ít
nhất 25% pixel của cùng segment và có ít nhất 32 pixel giao. Segment phải
chiếm ít nhất 20% diện tích mỗi box, và IoU giữa hai box phải dưới 0,40.
Các điều kiện này yêu cầu bằng chứng trên cả hai box và giảm các cặp box
gần trùng. Giữ nguyên các điều kiện khác, tăng ngưỡng phủ
segment lên 30% rồi 40% cho lần lượt 8 và 7 ứng viên gộp trên lô sạch, và 38
và 25 trên `3007` (so với 10 và 45 ở 25%). Giữ mặc định 25% cho đợt review
vì siết ngưỡng chỉ giảm 2–3 ứng viên gộp trên lô sạch, đồng thời giảm
7–20 ứng viên gộp trên lô luyện tập. Số lượng này đo tải review. Nhóm
cần xem ảnh để biết ngưỡng ảnh hưởng thế nào đến lỗi thật.

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
