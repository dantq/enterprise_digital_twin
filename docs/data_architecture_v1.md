# Enterprise Digital Twin — Data Architecture V1

## 1. Mục tiêu

Data Architecture V1 định nghĩa kiến trúc dữ liệu logic và luồng dữ liệu cho hệ thống Enterprise Digital Twin.

Kiến trúc này là lớp trung gian giữa:

Business Blueprint
→ Data Dictionary
→ Scenario Catalog
→ Database Schema
→ Data Generator
→ Benchmark
→ AI Analyst.

Mục tiêu chính:

1. Mô phỏng hoạt động của một doanh nghiệp có nhiều domain.
2. Duy trì quan hệ giữa các entity.
3. Mô phỏng hoạt động theo thời gian.
4. Mô phỏng propagation giữa các domain.
5. Tạo các incident có nguyên nhân và hậu quả.
6. Tách operational observation khỏi causal ground truth.
7. Tạo benchmark để đánh giá AI Analyst.
8. Ngăn chặn data leakage.
9. Cho phép tái lập dataset bằng seed và version.
10. Cho phép mở rộng dữ liệu lên quy mô lớn.

---

# 2. Nguyên tắc kiến trúc

## 2.1 Source of truth

Operational data là nguồn quan sát chính của AI Analyst.

Ground Truth là nguồn sự thật dùng riêng cho:

- Simulator
- Curator
- Evaluator
- Benchmark

AI Analyst không được truy cập Ground Truth.

---

## 2.2 Entity-first architecture

Mọi dữ liệu phải có thể truy nguyên về entity chính.

Các entity chính:

- Customer
- Product
- Category
- Supplier
- Warehouse
- Carrier
- Payment Method
- Order
- Payment
- Purchase Order
- Shipment
- Campaign
- Inventory
- Financial Transaction
- Incident

---

## 2.3 Temporal-first architecture

Các hoạt động nghiệp vụ phải được mô hình hóa theo thời gian.

Event sử dụng:

`TIMESTAMPTZ`

và lưu theo:

`UTC`

Các bảng snapshot hoặc master data chỉ sử dụng `DATE` khi không cần độ chính xác theo thời gian.

Mọi event phải có thời điểm xảy ra.

---

## 2.4 Immutable event principle

Các event đã ghi nhận không được sửa tùy tiện.

Nếu cần correction:

- tạo event mới;
- tạo adjustment;
- tạo reversal;
- hoặc tạo correction event.

Không xóa record đã được entity khác tham chiếu.

---

## 2.5 Referential integrity

Child entity chỉ được sinh sau khi parent entity tồn tại.

Ví dụ:

Customer
→ Order
→ Order Item

Supplier
→ Purchase Order
→ Purchase Order Item

Order
→ Payment
→ Shipment

Không được tạo:

`order.customer_id`

trỏ tới Customer chưa tồn tại.

---

# 3. Kiến trúc các tầng dữ liệu

Enterprise Digital Twin được chia thành 7 tầng chính:

```text
Layer 1 — Master Data (Khách hàng, Sản phẩm, Kho, Nhà cung cấp,...)
        ↓
Layer 2 — Transaction Data (Đơn hàng, Bút toán thanh toán, PO, Lô hàng,...)
        ↓
Layer 3 — Operational Events / Domain State Histories (Nguồn sự kiện gốc: order/payment/shipment history, inventory movements)
        ↓
Layer 4 — Engagement & Finance (Tickets, Reviews, Customer Behavior, Marketing, Financial Transactions)
        ↓
Layer 5 — Incident Operational Metadata (Bảng nội bộ incidents + Safe Projection View ai_incident_observations)
        ↓
Layer 6 — Causal Ground Truth (Restricted DAG: Causal Nodes, Links, Causes, Evidence, Outcomes)
        ↓
Layer 7 — Benchmark & Evaluation (Benchmark Cases, Evaluation Targets, Scoring Engine)
```

## 3.1 Quyết định kiến trúc về Event Stream
- **Không tạo bảng sự kiện đơn khối (`enterprise_events`)** gây dư thừa dữ liệu.
- Các bảng lịch sử trạng thái nghiệp vụ theo từng miền (`order_status_history`, `payment_status_history`, `shipment_status_history`, `inventory_movements`) chính là **Single Source of Truth** của toàn bộ sự kiện.
- Bộ điều phối sự kiện (Simulation Event Coordinator) sẽ dẫn dắt dòng chảy nghiệp vụ dựa trên các mốc thời gian trong các bảng lịch sử này.

## 3.2 Lớp chiếu an toàn ngăn rò rỉ dữ liệu (AI-Safe Projection Layer)
- AI Analyst vận hành theo nguyên tắc **Default-Deny**.
- AI Analyst **bị cấm đọc trực tiếp bảng `incidents`** để tránh rò rỉ trường `scenario_id` (ngăn AI biết trước kịch bản sự cố).
- Thay vào đó, AI quan sát qua View an toàn `ai_incident_observations` (chỉ chứa các triệu chứng bề mặt có thể quan sát được).
- Toàn bộ tầng Causal Ground Truth (Layer 6) và Benchmark Targets (Layer 7) bị thu hồi toàn quyền đối với AI Analyst, đảm bảo tính khách quan tuyệt đối cho bài toán đánh giá năng lực AI.