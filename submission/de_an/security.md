# Bảo mật khi bàn giao đề 04

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

Ảnh img_0099 có khuôn mặt người đứng phía sau nhìn rõ. Nếu guideline yêu cầu làm mờ, đặt lô ở trạng thái Hold, báo người phụ trách dữ liệu và reviewer theo jobs.csv. Ghi mã ảnh vào ticket nội bộ, giữ v1 để đối chiếu và chỉ bàn giao bản đã xử lý sau khi kiểm lại nội dung và SHA-256.
