# Bảo mật khi bàn giao lô r3007

## 1. Hết giờ và muốn mang lô về làm tiếp

Lưu tiến độ trong CVAT và bàn giao job đang dở cho trưởng nhóm. Khi cần làm
ngoài giờ, xin phương án truy cập từ xa qua thiết bị và tài khoản được phê duyệt,
hoặc tiếp tục vào ca sau. Không sao chép lô ra USB hay gửi qua email cá nhân vì
các bản sao sẽ nằm ngoài quyền truy cập và nhật ký của dự án. Nếu cần người khác
làm tiếp, trưởng nhóm phân lại job trong CVAT để ghi đúng người thực hiện.

## 2. Năm việc được làm hay không

| Việc | Quyết định và lý do |
|---|---|
| Mở job được giao trên máy công ty | Được. Dùng tài khoản cá nhân được cấp quyền và chỉ mở job thuộc phạm vi công việc. |
| Chụp màn hình gửi người quen | Không. Ảnh chụp có thể lộ khuôn mặt, nhãn và thông tin job. Trao đổi về lỗi qua kênh nội bộ được phép. |
| Chép lô ra USB | Không. Việc sao chép đưa ảnh, nhãn và manifest ra ngoài môi trường được kiểm soát. |
| Dán nhãn thật lên chatbot | Không. Nhãn có thể tiết lộ nội dung dự án và đi kèm tên ảnh hoặc thông tin nhận dạng. Dùng ví dụ giả lập khi hỏi về định dạng. |
| Đưa tài khoản CVAT cho đồng nghiệp | Không. Chia sẻ tài khoản làm mất khả năng truy vết ai đã xem hoặc sửa nhãn. Người nhận job dùng tài khoản được cấp riêng. |

## 3. Khuôn mặt rõ trong lô

Trong lô `r3007`, ảnh `000000025386.jpg` thuộc job `J10`, reviewer `Q01`.
Hai người ngồi cạnh cửa sổ toa tàu có khuôn mặt nhìn rõ.

Nếu guideline yêu cầu làm mờ và phát hiện mặt người còn rõ, đặt lô ở trạng thái
**Hold**. Ghi mã ảnh và job vào ticket nội bộ. Báo trưởng nhóm, người được giao
phụ trách dữ liệu hoặc quyền riêng tư, và reviewer của job để xác nhận phạm vi xử
lý. Giữ nguyên v1 để bảo toàn hash và bằng chứng bàn giao. Sau khi được duyệt,
người có thẩm quyền tạo v2, cập nhật manifest và SHA-256 rồi kiểm lại trước khi
đề xuất phát hành.
