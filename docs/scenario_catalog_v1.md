# Enterprise Digital Twin
# Danh mục kịch bản sự cố V1

## 1. Mục đích

Danh mục này định nghĩa các sự cố kinh doanh ẩn sẽ được đưa vào
Doanh nghiệp số (Enterprise Digital Twin).

AI Analyst chỉ được quan sát dữ liệu và các dấu hiệu mà một doanh nghiệp
thực tế có thể quan sát được.

AI không được trực tiếp nhìn thấy:

- nguyên nhân gốc
- mã kịch bản
- chuỗi nhân quả chuẩn
- tham số can thiệp
- Ground Truth

Các thông tin trên chỉ được sử dụng bởi hệ thống đánh giá.

---

# 2. Nguyên tắc thiết kế sự cố

Mỗi sự cố phải thỏa mãn:

1. Có nguyên nhân gốc rõ ràng.
2. Nguyên nhân gốc không được xuất hiện trực tiếp trong dữ liệu quan sát.
3. Nguyên nhân phải tạo ra các tác động thông qua chuỗi nghiệp vụ.
4. Các tác động phải xuất hiện theo thời gian.
5. Có đủ bằng chứng để AI điều tra.
6. Có thể tồn tại các nguyên nhân cạnh tranh.
7. Có Ground Truth để đánh giá.
8. Có thể tạo nhiều mức độ nghiêm trọng.
9. Có thể thay đổi thời điểm xảy ra.
10. Có thể tác động lên các thực thể khác nhau.

---

# S001 — Gián đoạn nhà cung cấp

## Mô tả

Một nhà cung cấp gặp vấn đề khiến thời gian cung ứng tăng lên
hoặc đơn hàng mua bị giao trễ.

## Nguyên nhân gốc

Gián đoạn nhà cung cấp.

## Dấu hiệu có thể quan sát

- Thời gian giao hàng của Purchase Order tăng.
- Purchase Order bị trễ.
- Lượng hàng nhập kho giảm.
- Tồn kho giảm.
- Tỷ lệ hết hàng tăng.
- Đơn hàng bị hủy tăng.
- Doanh thu giảm.

## Chuỗi nhân quả chuẩn

Gián đoạn nhà cung cấp
→ Purchase Order bị trễ
→ Nhập kho bị trễ
→ Tồn kho giảm
→ Hết hàng
→ Đơn hàng bị hủy
→ Doanh thu giảm

## Ground Truth

Nguyên nhân gốc:

Gián đoạn nhà cung cấp.

---

# S002 — Gián đoạn vận chuyển

## Mô tả

Một đơn vị vận chuyển gặp vấn đề làm tăng thời gian giao hàng.

## Nguyên nhân gốc

Gián đoạn logistics / carrier.

## Dấu hiệu có thể quan sát

- Thời gian giao hàng tăng.
- Tỷ lệ giao hàng trễ tăng.
- Số lượng khiếu nại tăng.
- Đánh giá tiêu cực tăng.
- Điểm đánh giá sản phẩm/dịch vụ giảm.
- Khả năng khách hàng quay lại giảm.
- Churn tăng.

## Chuỗi nhân quả chuẩn

Gián đoạn vận chuyển
→ Giao hàng trễ
→ Khiếu nại tăng
→ Đánh giá tiêu cực tăng
→ Mức độ hài lòng giảm
→ Churn tăng

## Ground Truth

Nguyên nhân gốc:

Gián đoạn vận chuyển.

---

# S003 — Suy giảm hệ thống thanh toán

## Mô tả

Một hệ thống hoặc cổng thanh toán hoạt động không ổn định,
làm tăng tỷ lệ giao dịch thanh toán thất bại.

## Nguyên nhân gốc

Suy giảm hệ thống thanh toán.

## Dấu hiệu có thể quan sát

- Payment failure tăng.
- Tỷ lệ hoàn tất đơn hàng giảm.
- Số đơn hàng bị bỏ tăng.
- Doanh thu giảm.

## Chuỗi nhân quả chuẩn

Suy giảm hệ thống thanh toán
→ Thanh toán thất bại tăng
→ Đơn hàng không hoàn tất
→ Doanh thu giảm

## Ground Truth

Nguyên nhân gốc:

Suy giảm hệ thống thanh toán.

---

# S004 — Phân bổ marketing không hiệu quả

## Mô tả

Một chiến dịch marketing tiêu tốn nhiều ngân sách nhưng
không tạo ra hiệu quả tương ứng.

## Nguyên nhân gốc

Marketing inefficiency.

## Dấu hiệu có thể quan sát

- Chi phí marketing tăng.
- Impressions tăng.
- Clicks tăng.
- Traffic tăng.
- Conversion rate giảm.
- CAC tăng.
- Doanh thu không tăng tương ứng.
- Profit giảm.

## Chuỗi nhân quả chuẩn

Marketing không hiệu quả
→ Chi phí tăng
→ Traffic tăng
→ Conversion giảm
→ CAC tăng
→ Lợi nhuận giảm

## Ground Truth

Nguyên nhân gốc:

Marketing inefficiency.

---

# S005 — Suy giảm chất lượng sản phẩm

## Mô tả

Chất lượng của một hoặc một nhóm sản phẩm giảm,
dẫn đến nhiều khách hàng trả hàng và khiếu nại.

## Nguyên nhân gốc

Suy giảm chất lượng sản phẩm.

## Dấu hiệu có thể quan sát

- Return rate tăng.
- Khiếu nại tăng.
- Rating giảm.
- Negative sentiment tăng.
- Chi phí xử lý hoàn trả tăng.
- Customer retention giảm.
- Churn tăng.

## Chuỗi nhân quả chuẩn

Chất lượng sản phẩm giảm
→ Returns tăng
→ Khiếu nại tăng
→ Rating giảm
→ Retention giảm
→ Churn tăng

## Ground Truth

Nguyên nhân gốc:

Suy giảm chất lượng sản phẩm.

---

# 3. Yêu cầu về Ground Truth

Mỗi incident phải có:

- incident_id
- scenario_id
- start_time
- end_time
- root_cause
- causal_chain
- affected_entities
- expected_effects
- intervention_parameters
- severity

Ground Truth được lưu riêng với dữ liệu mà AI Analyst có quyền truy cập.

AI Analyst không được truy cập bảng Ground Truth.

---

# 4. Mức độ nghiêm trọng

Mỗi scenario có thể có ba mức:

## LOW

Tác động nhỏ và khó nhận biết.

## MEDIUM

Tác động rõ ràng trên một hoặc nhiều domain.

## HIGH

Tác động lớn và lan truyền qua nhiều domain.

Ví dụ:

LOW
→ inventory giảm nhẹ

MEDIUM
→ stockout tăng rõ rệt

HIGH
→ stockout
→ cancellation
→ revenue loss
→ customer churn

---

# 5. Thời gian tác động

Sự cố không nhất thiết tạo ra tác động ngay lập tức.

Ví dụ:

T0:
Gián đoạn nhà cung cấp

T1:
Purchase Order delay

T2:
Receiving delay

T3:
Inventory shortage

T4:
Stockout

T5:
Order cancellation

T6:
Revenue impact

Điều này rất quan trọng đối với bài toán
Root Cause Analysis theo thời gian.

---

# 6. Hidden Variables

Hệ thống sinh dữ liệu có thể sử dụng các biến ẩn:

- supplier_disruption_level
- carrier_disruption_level
- payment_degradation_level
- marketing_efficiency_factor
- product_quality_factor

Các biến này KHÔNG được đưa trực tiếp vào AI Analyst.

Chúng chỉ được sử dụng để sinh dữ liệu và tạo Ground Truth.

---

# 7. Nguyên tắc chống Data Leakage

Không được đưa trực tiếp các trường sau vào lớp dữ liệu quan sát:

- root_cause
- scenario_id
- intervention_type
- intervention_parameters
- causal_chain
- ground_truth_effect
- hidden_variables

AI phải suy luận nguyên nhân từ các dấu hiệu quan sát được.

---

# 8. Yêu cầu đánh giá

Hệ thống đánh giá phải đo ít nhất:

## 8.1 Root Cause Accuracy

AI có xác định đúng nguyên nhân gốc hay không?

## 8.2 Causal Path Accuracy

AI có xác định đúng chuỗi nhân quả hay không?

## 8.3 Evidence Precision

Các bằng chứng AI đưa ra có thực sự liên quan không?

## 8.4 Evidence Recall

AI có bỏ sót bằng chứng quan trọng không?

## 8.5 Forecast Accuracy

AI có dự báo đúng hậu quả hay không?

## 8.6 Recommendation Quality

Hành động đề xuất có giải quyết đúng nguyên nhân không?

---

# 9. Yêu cầu mở rộng trong tương lai

Scenario Engine V2 phải hỗ trợ:

- nhiều sự cố xảy ra đồng thời
- sự cố kéo dài nhiều ngày
- sự cố có cường độ thay đổi
- sự cố xảy ra ở nhiều entity
- nhiều nguyên nhân có biểu hiện tương tự
- nhiễu dữ liệu
- missing data
- delayed data
- measurement error

Mục tiêu là ngăn AI giải quyết bài toán chỉ bằng
một vài dấu hiệu đơn giản.