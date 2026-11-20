# Báo cáo nhóm ABCDE

## 1. Kết quả trên seed 3007

- Validator luật ghi nhận 11 lỗi trên 250 ảnh (4,4%). F1 theo báo cáo đã lưu: luật 1,0; đối chiếu gán nhãn chưa có điểm vì chưa có review của thành viên; F1 tổng được ghi là 0,7. Các điểm F1 đã làm tròn và chỉ dùng để theo dõi validator, không dùng thay cho việc xem ảnh.
- Lần sinh candidates ban đầu có 60 ứng viên: 50 `instance_merge`, 5 `bbox_drift`, 4 `class_disagreement`, 1 `missing_box`. Theo yêu cầu review, đã loại riêng ứng viên `bbox_drift` của `000000009483`; `runs/r3007/candidates.json` hiện còn 59 ứng viên: 50 `instance_merge`, 4 `bbox_drift`, 4 `class_disagreement`, 1 `missing_box`. Ứng viên là đầu mối để xem ảnh, không mặc nhiên là lỗi.
- Lần calib 50 ảnh `--no-faults` đã ghi nhận 11 ứng viên `instance_merge` và không có `bbox_drift`, `class_disagreement` hay `missing_box`. Các ngưỡng thử: chỉ xét segment thing không crowd có diện tích từ 1.024 pixel; ghép lớp cần segment coverage ≥ 0,50, box coverage ≥ 0,10 và mask-box IoU ≥ 0,15; `bbox_drift` khi segment coverage < 0,75; `instance_merge` cần mỗi box giao ít nhất 32 pixel, chứa ≥ 0,25 diện tích segment và segment chiếm ≥ 0,20 diện tích mỗi box, đồng thời IoU giữa hai box < 0,40. Không đọc `_private`.

## 2. Vì sao báo hết ứng viên có thể làm F1 giảm?

Ứng viên sinh từ giao box-mask có thể là báo động giả: box của hai vật khác nhau vẫn có thể chồng nhau, hoặc mask có thể chạm vào box kế bên. Nếu báo tất cả là lỗi, số false positive tăng, precision giảm và F1 có thể giảm dù recall cao. Vì vậy phải xem ảnh, box và mask rồi ghi `confirmed` hoặc `rejected` kèm lý do cụ thể.

## 3. Quyết định và lineage

11 lỗi luật trên 250 ảnh tương đương 4,4%, vượt ngưỡng 2%; quyết định HOLD cho `lab250_95697c6d4612` đã được ghi trong `runs/lineage.jsonl`. Run `R-021` được huấn luyện từ release này nên bị ảnh hưởng (`affected=True`); cần review hoặc train lại theo kết quả xử lý dữ liệu.

`runs/r3007/errors.json` hiện có 11 lỗi luật. Codex đã xem 11 ứng viên thuộc 7 ảnh theo yêu cầu: có 2 gợi ý `confirmed` (ứng viên `class_disagreement` của `000000009483`, ứng viên `instance_merge` của `000000015254`) và 9 gợi ý `rejected`. Các kết quả cùng tên người xem được ghi trong `templates/review_log.csv`; đây là review hỗ trợ bằng AI, chưa phải xác nhận cuối của thành viên nhóm. Vì vậy chưa gộp lỗi semantic vào `errors.json`; `runs/r3007/review_log.csv` vẫn trống. Hai lỗi `wrong_hash` cần được mở ảnh kiểm tra trước khi quyết định cập nhật hash hay đưa ảnh vào rework.

## 4. Hash chứng minh điều gì?

SHA-256 giúp xác nhận bytes của file đang bàn giao khớp với digest trong manifest; thay đổi một byte làm digest thay đổi với xác suất áp đảo. Hash không chứng minh nội dung ảnh hoặc nhãn đúng, nguồn gốc hợp lệ, hay người gán đã theo guideline.

## 5. Truy vết ticket

Ticket hỏi về các `bottle` bị che hoặc ở mép ảnh trong `scene_197` và `scene_309`. `runs/r3007/trace.json` liệt kê 2 ảnh `tier_a` trong các scene được nêu, 4 ảnh `tier_b` ở scene khác thuộc các job dùng guideline v1.2, và các người cần thông báo: A02, A04, A05, Q01, Q03. Dùng guideline gắn với job trong `jobs.csv` vì đó là hướng dẫn người gán thực sự nhận được; metadata của ảnh có thể là phần sai cần phát hiện.

## 6. Lỗi đã phát hiện và trạng thái bàn giao

Trong PR #2, nhóm phát hiện ba lỗi triển khai: cặp box không có giao pixel hoặc giao bbox vẫn có thể bị xét `bbox_drift`; ảnh `wrong_hash` đã được review là hỏng vẫn có thể lọt vào v2; và đường dẫn v2 bên trong `delivery/` chưa bị chặn. Commit `ec4a82f` khôi phục các sửa đổi cho hai file `maskchecks.py` và `rework.py`. Các ca kiểm tra tập trung cho ba lỗi này đã qua.

Các kết quả trong `templates/review_log.csv` ghi rõ Codex là người xem hỗ trợ: 2 gợi ý `confirmed`, 9 gợi ý `rejected`. Thành viên trong nhóm cần tự xem lại và ghi kết luận cuối vào `runs/r3007/review_log.csv` trước khi gộp lỗi semantic. Chưa tạo v2 hoặc `rework_queue.csv`: còn chờ review cuối của nhóm, `errors.json` cuối và kết quả kiểm ảnh sai hash. Vì vậy gói bàn giao chưa hoàn tất và chưa thể phát hành.
