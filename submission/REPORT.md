# Báo cáo nhóm ABCDE

## 1. Số liệu luyện tập
- Seed `3007`, điểm tự đo đã làm tròn: F1 lỗi luật ≈ **0,9**, lỗi gán nhãn ≈ **0,7**, tổng ≈ **0,8**. Truy vết có F1 ≈ **1,0** cho cả ba mục.
- Bản nộp có **16 lỗi** gồm 9 lỗi luật và 7 lỗi nhãn. Seed phụ `3008` báo 10 lỗi luật. Lô sạch báo 0 lỗi luật.
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
Trên seed `3007`, validator sinh 54 ứng viên nhưng review chỉ xác nhận 7 lỗi nhãn khác nhau. Log có 52 dòng vì hai dòng mỗi dòng mô tả hai ứng viên. Lô sạch vẫn có 10 ứng viên gộp instance. Nếu nộp mọi ứng viên, các ca box chồng do vật đứng sát nhau hoặc bị che sẽ tạo thêm false positive, làm giảm precision và kéo F1 xuống khi recall giữ nguyên.

## 3. Quyết định và lineage
V1 có **16/250 đơn vị lỗi (6,4%)**, tính mỗi ảnh hoặc cảnh bị rò split một lần. Tỷ lệ vượt ngưỡng 2%, nên lineage ghi **HOLD** cho `lab250_68efac8c866e`. Truy vấn impact báo `R-021: affected=True action=review_or_retrain` vì run này đã train từ v1. Khi tạo v2, nhóm chuyển 5 ảnh sang rework, giữ 245 cặp ảnh–nhãn với 1.675 box. Bộ kiểm tra bàn giao đạt **17 PASS, 0 FAIL**.

## 4. Hash chứng minh gì, không chứng minh gì?
SHA-256 dùng để đối chiếu byte của file với bản ghi manifest hoặc đối chiếu gói ZIP với checksum đã công bố. Chất lượng nhãn, độ đầy đủ của box và việc tuân thủ guideline vẫn cần kiểm tra riêng. Nhóm đã mở kiểm hai ảnh sai hash, thấy ảnh hiển thị bình thường, rồi ghi SHA-256 theo nội dung thực tế trong manifest v2.

## 5. Truy vết
Ticket nêu lớp `bottle` ở `scene_197` và `scene_309`. Nhóm lọc các ảnh có box `bottle` từ job dùng v1.2. Hai ảnh trong cảnh nêu ở ticket vào `tier_a`, bốn ảnh từ cảnh khác vào `tier_b`. `notify` gồm A02, A04, A05, Q01 và Q03. Nhóm lấy phiên bản guideline từ `jobs.csv` vì đây là hướng dẫn của job và trường guideline trên từng ảnh có thể là dữ liệu bị gài lỗi.

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
Lần dựng đầu, H9 thất bại vì script thống kê dùng cả chuỗi `0 person` làm tên lớp. Nhóm cập nhật `release_csv.py` để đọc mã và tên lớp đúng định dạng. Tạo lại hai bảng từ bộ ảnh và nhãn v2 cho kết quả khớp từng byte với bản bàn giao.

Bản seed `3007` dùng để bàn giao được dựng lại từ cùng seed và xác minh đúng release ID vì một bản cục bộ trước đó có JPEG thay đổi sau khi tạo lô. Bản bàn giao giữ nguyên dữ liệu v1 đã dựng lại. Các ghi chú của Vinh bị lỗi mã hóa được phục hồi theo ngữ cảnh. Mười kết luận và các mã ảnh, box, segment được giữ nguyên.
