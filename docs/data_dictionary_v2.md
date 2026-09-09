# Enterprise Digital Twin — Data Dictionary V2

## 1. Phạm vi và quy ước

Đây là đặc tả dữ liệu logic cho mô phỏng, điều tra AI và benchmark Enterprise Digital Twin; không phải PostgreSQL schema và không chứa dữ liệu mẫu. Tên bảng/cột bằng English, mô tả bằng tiếng Việt.

- Entity và quan hệ dùng UUID. Thời điểm sự kiện là TIMESTAMPTZ, lưu UTC; DATE chỉ dùng khi không cần giờ.
- Tiền: NUMERIC(18,2); số lượng: NUMERIC(18,4); tỷ lệ/điểm: NUMERIC(8,4). Không dùng FLOAT cho tiền.
- FK phải tồn tại trước child. Event đã ghi là bất biến; correction dùng event/bút toán đảo. Không xóa record đã tham chiếu, dùng status.
- Các giá trị status/domain/event_type theo controlled vocabulary. created_at là lúc ghi nhận.

## 2. Master Data

### customers
Mục đích: hồ sơ khách hàng, phân khúc và truy nguyên mua hàng.

| Column | Type | Key | Description |
|---|---|---|---|
| customer_id | UUID | PK | Mã khách hàng |
| customer_segment | VARCHAR(30) |  | New, Regular, VIP, At-Risk, Churned |
| acquisition_channel | VARCHAR(50) |  | Kênh thu hút |
| registration_date | DATE |  | Ngày đăng ký |
| region | VARCHAR(100) |  | Khu vực |
| age_group | VARCHAR(30) |  | Nhóm tuổi |
| status | VARCHAR(20) |  | Active, Inactive, Blocked |
| created_at | TIMESTAMPTZ |  | Lúc tạo |

Rules: registration_date không sau created_at; chỉ Active tạo đơn mới.

### categories
Mục đích: cây danh mục sản phẩm.

| Column | Type | Key | Description |
|---|---|---|---|
| category_id | UUID | PK | Mã danh mục |
| category_name | VARCHAR(200) | UQ | Tên |
| parent_category_id | UUID | FK → categories.category_id, nullable | Danh mục cha |
| status | VARCHAR(20) |  | Active, Inactive |

Rules: không có vòng lặp cây.

### products
Mục đích: SKU, giá chuẩn và thuộc tính nhu cầu.

| Column | Type | Key | Description |
|---|---|---|---|
| product_id | UUID | PK | Mã SKU |
| category_id | UUID | FK → categories.category_id | Danh mục |
| product_name | VARCHAR(250) |  | Tên |
| unit_price | NUMERIC(18,2) |  | Giá niêm yết |
| unit_cost | NUMERIC(18,2) |  | Giá vốn |
| margin_rate | NUMERIC(8,4) |  | Biên chuẩn |
| demand_class | VARCHAR(20) |  | High, Medium, Low |
| demand_volatility | NUMERIC(8,4) |  | Biến động |
| launch_date | DATE |  | Ngày ra mắt |
| status | VARCHAR(20) |  | Active, Discontinued, Inactive |

Rules: giá/cost không âm; margin_rate=(unit_price-unit_cost)/unit_price khi price > 0.

### suppliers
Mục đích: nhà cung cấp và lead-time baseline.

| Column | Type | Key | Description |
|---|---|---|---|
| supplier_id | UUID | PK | Mã supplier |
| supplier_name | VARCHAR(250) | UQ | Tên |
| reliability_score | NUMERIC(8,4) |  | 0–1 |
| average_lead_time_days | NUMERIC(10,2) |  | Lead time |
| lead_time_std_days | NUMERIC(10,2) |  | Độ lệch |
| region | VARCHAR(100) |  | Khu vực |
| status | VARCHAR(20) |  | Active, Suspended, Inactive |

Rules: score trong [0,1], thời lượng không âm.

### supplier_products
Mục đích: quan hệ cung ứng supplier–product.

| Column | Type | Key | Description |
|---|---|---|---|
| supplier_product_id | UUID | PK | Mã quan hệ |
| supplier_id | UUID | FK → suppliers.supplier_id | Supplier |
| product_id | UUID | FK → products.product_id | Product |
| supplier_sku | VARCHAR(100) |  | SKU supplier |
| unit_cost | NUMERIC(18,2) |  | Giá mua |
| is_primary | BOOLEAN |  | Supplier ưu tiên |
| status | VARCHAR(20) |  | Active, Inactive |

Rules: unique(supplier_id, product_id); tối đa một primary Active/product.

### warehouses
Mục đích: mạng kho và năng lực.

| Column | Type | Key | Description |
|---|---|---|---|
| warehouse_id | UUID | PK | Mã kho |
| warehouse_name | VARCHAR(200) | UQ | Tên |
| region | VARCHAR(100) |  | Khu vực |
| capacity | NUMERIC(18,4) |  | Sức chứa |
| daily_processing_capacity | NUMERIC(18,4) |  | Công suất/ngày |
| status | VARCHAR(20) |  | Active, Constrained, Inactive |

Rules: năng lực không âm.

### carriers
Mục đích: baseline đối tác giao vận.

| Column | Type | Key | Description |
|---|---|---|---|
| carrier_id | UUID | PK | Mã carrier |
| carrier_name | VARCHAR(200) | UQ | Tên |
| average_delivery_days | NUMERIC(10,2) |  | Thời gian giao |
| delivery_reliability | NUMERIC(8,4) |  | 0–1 |
| region | VARCHAR(100) |  | Khu vực |
| status | VARCHAR(20) |  | Active, Suspended, Inactive |

Rules: reliability trong [0,1].

### payment_methods
Mục đích: danh mục phương thức thanh toán.

| Column | Type | Key | Description |
|---|---|---|---|
| payment_method_id | UUID | PK | Mã phương thức |
| method_name | VARCHAR(100) | UQ | Tên |
| provider | VARCHAR(150) |  | Nhà cung cấp |
| failure_rate_baseline | NUMERIC(8,4) |  | 0–1 |
| status | VARCHAR(20) |  | Active, Inactive |

Rules: failure rate trong [0,1].

## 3. Transaction Data

### orders
Mục đích: tiêu đề đơn bán.

| Column | Type | Key | Description |
|---|---|---|---|
| order_id | UUID | PK | Mã đơn |
| customer_id | UUID | FK → customers.customer_id | Khách |
| warehouse_id | UUID | FK → warehouses.warehouse_id | Kho |
| order_timestamp | TIMESTAMPTZ |  | Lúc tạo |
| channel | VARCHAR(50) |  | Kênh |
| order_status | VARCHAR(30) |  | Pending, Paid, Fulfilled, Shipped, Delivered, Cancelled, Refunded |
| subtotal, discount_amount, shipping_fee, total_amount | NUMERIC(18,2) |  | Các tổng tiền |
| currency_code | CHAR(3) |  | ISO 4217 |

Rules: subtotal=SUM(order_items.item_total); total=subtotal-discount+shipping; trạng thái theo history.

### order_items
Mục đích: dòng hàng của đơn.

| Column | Type | Key | Description |
|---|---|---|---|
| order_item_id | UUID | PK | Mã dòng |
| order_id | UUID | FK → orders.order_id | Đơn |
| product_id | UUID | FK → products.product_id | Product |
| quantity | NUMERIC(18,4) |  | Số lượng |
| unit_price, discount_amount, item_total | NUMERIC(18,2) |  | Giá/giảm/tiền dòng |

Rules: unique(order_id, product_id); quantity > 0; item_total=quantity×unit_price-discount; giá là snapshot.

### order_status_history
Mục đích: nhật ký trạng thái đơn bất biến.

| Column | Type | Key | Description |
|---|---|---|---|
| order_status_history_id | UUID | PK | Mã event |
| order_id | UUID | FK → orders.order_id | Đơn |
| status | VARCHAR(30) |  | Trạng thái mới |
| status_timestamp | TIMESTAMPTZ |  | Lúc hiệu lực |
| actor_type | VARCHAR(30) |  | System, Customer, Staff, Carrier |
| reason_code | VARCHAR(100) |  | Lý do, nullable |

Rules: unique(order_id,status_timestamp); thời gian không lùi; orders.order_status là event cuối.

### payments
Mục đích: payment của đơn hàng.

| Column | Type | Key | Description |
|---|---|---|---|
| payment_id | UUID | PK | Mã payment |
| order_id | UUID | FK → orders.order_id | Đơn |
| payment_method_id | UUID | FK → payment_methods.payment_method_id | Phương thức |
| payment_timestamp | TIMESTAMPTZ |  | Lúc khởi tạo |
| amount | NUMERIC(18,2) |  | Giá trị |
| currency_code | CHAR(3) |  | ISO 4217 |
| payment_status | VARCHAR(30) |  | Initiated, Authorized, Captured, Failed, Refunded |
| provider_transaction_ref | VARCHAR(150) | UQ | Tham chiếu provider |

Rules: amount > 0; Captured trừ Refunded không vượt order total.

### payment_status_history
Mục đích: lịch sử payment bất biến.

| Column | Type | Key | Description |
|---|---|---|---|
| payment_status_history_id | UUID | PK | Mã event |
| payment_id | UUID | FK → payments.payment_id | Payment |
| status | VARCHAR(30) |  | Trạng thái mới |
| status_timestamp | TIMESTAMPTZ |  | Lúc hiệu lực |
| failure_code | VARCHAR(100) |  | Mã lỗi, nullable |

Rules: thời gian không lùi; payment_status phản ánh event cuối.

### inventory_snapshots
Mục đích: tồn kho đã quan sát tại thời điểm chốt.

| Column | Type | Key | Description |
|---|---|---|---|
| inventory_snapshot_id | UUID | PK | Mã snapshot |
| warehouse_id | UUID | FK → warehouses.warehouse_id | Kho |
| product_id | UUID | FK → products.product_id | Product |
| snapshot_timestamp | TIMESTAMPTZ |  | Lúc chốt |
| on_hand_quantity, reserved_quantity, available_quantity, reorder_point | NUMERIC(18,4) |  | Các lượng tồn |

Rules: unique(warehouse_id,product_id,snapshot_timestamp); available=on_hand-reserved; không âm.

### inventory_movements
Mục đích: ledger biến động tồn truy nguyên PO/đơn.

| Column | Type | Key | Description |
|---|---|---|---|
| inventory_movement_id | UUID | PK | Mã movement |
| warehouse_id | UUID | FK → warehouses.warehouse_id | Kho |
| product_id | UUID | FK → products.product_id | Product |
| movement_timestamp | TIMESTAMPTZ |  | Lúc hiệu lực |
| movement_type | VARCHAR(30) |  | Receipt, Reservation, Release, Pick, Adjustment, Return |
| quantity_delta | NUMERIC(18,4) |  | Lượng có dấu |
| reference_entity_type | VARCHAR(50) |  | PurchaseOrder, Order, Shipment, Adjustment |
| reference_entity_id | UUID | Polymorphic FK | Entity nguồn |
| reason_code | VARCHAR(100) |  | Lý do |

Rules: reference phải tồn tại theo type; dấu phù hợp movement type; không âm nếu policy yêu cầu.

### purchase_orders
Mục đích: tiêu đề PO nhập hàng.

| Column | Type | Key | Description |
|---|---|---|---|
| purchase_order_id | UUID | PK | Mã PO |
| supplier_id | UUID | FK → suppliers.supplier_id | Supplier |
| warehouse_id | UUID | FK → warehouses.warehouse_id | Kho nhận |
| order_timestamp, expected_delivery_timestamp, received_timestamp | TIMESTAMPTZ |  | Các mốc PO |
| po_status | VARCHAR(30) |  | Draft, Ordered, PartiallyReceived, Received, Cancelled |
| total_amount | NUMERIC(18,2) |  | Tổng PO |
| currency_code | CHAR(3) |  | ISO 4217 |

Rules: expected/received không trước order; total là tổng item; receipt sau PO.

### purchase_order_items
Mục đích: dòng hàng của PO.

| Column | Type | Key | Description |
|---|---|---|---|
| purchase_order_item_id | UUID | PK | Mã dòng |
| purchase_order_id | UUID | FK → purchase_orders.purchase_order_id | PO |
| product_id | UUID | FK → products.product_id | Product |
| ordered_quantity, received_quantity | NUMERIC(18,4) |  | Lượng đặt/nhận |
| unit_cost, item_total | NUMERIC(18,2) |  | Giá/tiền dòng |

Rules: unique(purchase_order_id,product_id); 0≤received≤ordered; item_total=ordered×cost.

### shipments
Mục đích: lô giao outbound.

| Column | Type | Key | Description |
|---|---|---|---|
| shipment_id | UUID | PK | Mã shipment |
| order_id | UUID | FK → orders.order_id | Đơn |
| warehouse_id | UUID | FK → warehouses.warehouse_id | Kho xuất |
| carrier_id | UUID | FK → carriers.carrier_id | Carrier |
| shipment_timestamp, estimated_delivery_timestamp, delivered_timestamp | TIMESTAMPTZ |  | Mốc giao |
| shipment_status | VARCHAR(30) |  | Created, PickedUp, InTransit, Delivered, Failed, Returned |
| tracking_number | VARCHAR(150) | UQ | Tracking |

Rules: shipment sau order; delivered không trước shipment; chỉ Paid/Fulfilled được bàn giao.

### shipment_status_history
Mục đích: nhật ký giao vận bất biến.

| Column | Type | Key | Description |
|---|---|---|---|
| shipment_status_history_id | UUID | PK | Mã event |
| shipment_id | UUID | FK → shipments.shipment_id | Shipment |
| status | VARCHAR(30) |  | Trạng thái |
| status_timestamp | TIMESTAMPTZ |  | Lúc hiệu lực |
| location_region, exception_code | VARCHAR(100) |  | Vùng quét/ngoại lệ, nullable |

Rules: thời gian không lùi; shipment_status là event cuối.

## 4. Business / Operational Events và Marketing

### customer_tickets
Mục đích: ticket hỗ trợ/khiếu nại quan sát.

| Column | Type | Key | Description |
|---|---|---|---|
| ticket_id | UUID | PK | Mã ticket |
| customer_id | UUID | FK → customers.customer_id | Khách |
| order_id | UUID | FK → orders.order_id, nullable | Đơn |
| created_at, resolved_at | TIMESTAMPTZ |  | Mốc ticket |
| category | VARCHAR(50) |  | Delivery, Payment, ProductQuality, Refund, Order, Other |
| priority, status | VARCHAR(20) |  | Low–Critical; Open–Closed |
| resolution_time_hours, satisfaction_score | NUMERIC |  | Chỉ số, nullable |

Rules: order phải thuộc customer; resolved không trước created.

### reviews
Mục đích: đánh giá theo đơn và product.

| Column | Type | Key | Description |
|---|---|---|---|
| review_id | UUID | PK | Mã review |
| customer_id | UUID | FK → customers.customer_id | Khách |
| order_id | UUID | FK → orders.order_id | Đơn |
| product_id | UUID | FK → products.product_id | Product |
| created_at | TIMESTAMPTZ |  | Lúc review |
| rating | INTEGER |  | 1–5 |
| sentiment_score | NUMERIC(5,4) |  | -1 đến 1 |
| review_category | VARCHAR(50) |  | Chủ đề |

Rules: unique(customer_id,order_id,product_id); product phải thuộc order; review sau order.

### customer_behavior_events
Mục đích: clickstream/hành vi chuẩn hóa.

| Column | Type | Key | Description |
|---|---|---|---|
| behavior_event_id | UUID | PK | Mã event |
| customer_id | UUID | FK → customers.customer_id, nullable | Khách |
| session_id | UUID |  | Phiên |
| product_id | UUID | FK → products.product_id, nullable | Product |
| campaign_id | UUID | FK → marketing_campaigns.campaign_id, nullable | Campaign |
| event_timestamp | TIMESTAMPTZ |  | Lúc xảy ra |
| event_type | VARCHAR(50) |  | PageView, ProductView, AddToCart, Checkout, Purchase, Search |
| channel | VARCHAR(50) |  | Kênh |
| event_value | NUMERIC(18,4) |  | Metric, nullable |

Rules: event trong session không lùi; Purchase truy vết order qua correlation metadata, không chứa truth.

### marketing_campaigns
Mục đích: định nghĩa campaign.

| Column | Type | Key | Description |
|---|---|---|---|
| campaign_id | UUID | PK | Mã campaign |
| campaign_name | VARCHAR(250) | UQ | Tên |
| channel | VARCHAR(50) |  | Kênh |
| start_time, end_time | TIMESTAMPTZ |  | Khoảng chạy |
| budget_amount | NUMERIC(18,2) |  | Ngân sách |
| currency_code | CHAR(3) |  | ISO 4217 |
| status | VARCHAR(20) |  | Draft, Active, Paused, Completed |

Rules: end không trước start; budget không âm.

### marketing_events
Mục đích: hiệu suất campaign quan sát được.

| Column | Type | Key | Description |
|---|---|---|---|
| marketing_event_id | UUID | PK | Mã event |
| campaign_id | UUID | FK → marketing_campaigns.campaign_id | Campaign |
| event_timestamp | TIMESTAMPTZ |  | Lúc xảy ra |
| event_type | VARCHAR(50) |  | Impression, Click, Conversion, Spend, AudienceUpdate |
| customer_id | UUID | FK → customers.customer_id, nullable | Khách |
| order_id | UUID | FK → orders.order_id, nullable | Đơn |
| metric_value | NUMERIC(18,4) |  | Metric |
| cost_amount | NUMERIC(18,2) |  | Chi phí, nullable |

Rules: event trong campaign trừ late-arrival có reason ingest; cost không âm.

## 5. Finance

### financial_transactions
Mục đích: ledger tài chính quan sát được, nối vận hành với tài chính.

| Column | Type | Key | Description |
|---|---|---|---|
| financial_transaction_id | UUID | PK | Mã bút toán |
| transaction_timestamp | TIMESTAMPTZ |  | Lúc hiệu lực |
| transaction_type | VARCHAR(50) |  | Revenue, COGS, ShippingCost, Refund, MarketingSpend, InventoryAdjustment |
| amount | NUMERIC(18,2) |  | Có dấu accounting |
| currency_code | CHAR(3) |  | ISO 4217 |
| order_id | UUID | FK → orders.order_id, nullable | Đơn liên quan |
| payment_id | UUID | FK → payments.payment_id, nullable | Payment liên quan |
| purchase_order_id | UUID | FK → purchase_orders.purchase_order_id, nullable | PO liên quan |
| shipment_id | UUID | FK → shipments.shipment_id, nullable | Shipment liên quan |
| campaign_id | UUID | FK → marketing_campaigns.campaign_id, nullable | Campaign liên quan |
| reference_code | VARCHAR(150) | UQ | Mã nguồn |

Rules: ít nhất một entity hoặc reference hợp lệ; Revenue sau Captured payment, Refund sau payment/order; không mang truth label.

## 6. Incident operational metadata

### incidents (Bảng nội bộ — Internal Table)
Mục đích: Lưu trữ toàn bộ thông tin sự cố, phục vụ Simulator và Evaluator liên kết với Scenario Catalog. **Bảng này cấm AI Analyst truy cập trực tiếp để tránh rò rỉ `scenario_id`**.

| Column | Type | Key | Description |
|---|---|---|---|
| incident_id | UUID | PK | Mã incident |
| scenario_id | VARCHAR(100) |  | Mã scenario (Ground Truth trigger ID, cấm AI đọc) |
| detected_at, start_time, end_time | TIMESTAMPTZ |  | Mốc phát hiện/quan sát |
| severity | VARCHAR(20) |  | Low, Medium, High, Critical |
| affected_domain | VARCHAR(50) |  | Domain tín hiệu ban đầu |
| status | VARCHAR(20) |  | Open, Investigating, Mitigated, Closed |
| summary | VARCHAR(1000) |  | Mô tả hiện tượng bề mặt trung tính |

Rules: detected không trước start; end không trước start; cấm root_cause_type, decisive evidence, causal truth và outcome. AI Analyst bị thu hồi quyền SELECT trên bảng này.

### ai_incident_observations (Safe Projection View)
Mục đích: Cung cấp tín hiệu sự cố bề mặt cho AI Analyst, che giấu hoàn toàn `scenario_id` và các thông tin gây thiên kiến/rò rỉ.

| Column | Type | Key | Description |
|---|---|---|---|
| incident_id | UUID | Ref | Mã incident để AI trace dữ liệu liên quan |
| detected_at | TIMESTAMPTZ |  | Thời điểm phát hiện sự cố |
| start_time, end_time | TIMESTAMPTZ |  | Khoảng thời gian hiệu lực |
| severity | VARCHAR(20) |  | Mức độ nghiêm trọng quan sát được |
| affected_domain | VARCHAR(50) |  | Miền nghiệp vụ xuất hiện triệu chứng |
| status | VARCHAR(20) |  | Trạng thái xử lý |
| surface_symptoms | VARCHAR(1000) |  | Triệu chứng bề mặt (chiếu từ summary trung tính) |

Rules: Chiếu (SELECT) từ `incidents`; không bao gồm `scenario_id`; chỉ cấp quyền SELECT cho `edt_ai_analyst`.

### incident_entities
Mục đích: entity trong phạm vi ảnh hưởng quan sát.

| Column | Type | Key | Description |
|---|---|---|---|
| incident_entity_id | UUID | PK | Mã liên kết |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| entity_type | VARCHAR(50) |  | Customer, Product, Supplier, Warehouse, Order, PurchaseOrder, Shipment, Payment, Campaign |
| entity_id | UUID | Polymorphic FK | ID theo entity_type |
| observed_at | TIMESTAMPTZ |  | Lúc phát hiện |
| impact_type | VARCHAR(100) |  | Triệu chứng |
| impact_severity | NUMERIC(8,4) |  | 0–1 |

Rules: unique(incident_id,entity_type,entity_id,observed_at); validate entity registry; không gắn causal label.

## 7. Causal Ground Truth — restricted

Các bảng này chỉ cho curator/evaluator, không được vào dataset, view, prompt, retrieval, embedding hay dashboard của AI Analyst.

### causal_nodes
Mục đích: node đồ thị nhân quả thật.

| Column | Type | Key | Description |
|---|---|---|---|
| node_id | UUID | PK | Mã node |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| node_type | VARCHAR(50) |  | RootCause, Mechanism, OperationalImpact, BusinessImpact, Outcome |
| domain | VARCHAR(50) |  | Supply, Inventory, Fulfillment, Delivery, Payment, Customer, Marketing, Finance |
| entity_type, entity_id | VARCHAR(50), UUID | Polymorphic FK, nullable | Entity liên quan |
| valid_from, valid_to | TIMESTAMPTZ |  | Hiệu lực truth |
| truth_label | VARCHAR(250) | Restricted | Nhãn truth |
| truth_description | TEXT | Restricted | Diễn giải |

Rules: valid_to không trước valid_from; case đóng có RootCause và Outcome.

### causal_links
Mục đích: cạnh có hướng causal truth.

| Column | Type | Key | Description |
|---|---|---|---|
| causal_link_id | UUID | PK | Mã cạnh |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| cause_node_id | UUID | FK → causal_nodes.node_id | Node nguyên nhân |
| effect_node_id | UUID | FK → causal_nodes.node_id | Node hệ quả |
| relationship_type | VARCHAR(50) |  | Causes, Amplifies, Mitigates, CorrelatesWith |
| lag_minutes | NUMERIC(12,2) |  | Độ trễ |
| confidence | NUMERIC(8,4) |  | 0–1 |

Rules: cause_node_id ≠ effect_node_id; unique(incident_id,cause_node_id,effect_node_id,relationship_type); hai node cùng incident; graph Causes là DAG; effect không trước cause+lag.

### incident_causes
Mục đích: root cause chính/phụ được xác nhận.

| Column | Type | Key | Description |
|---|---|---|---|
| incident_cause_id | UUID | PK | Mã gán |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| node_id | UUID | FK → causal_nodes.node_id | Node RootCause |
| cause_rank | INTEGER |  | 1 là primary |
| is_primary | BOOLEAN |  | Cờ primary |
| confirmed_at | TIMESTAMPTZ |  | Lúc xác nhận |

Rules: node cùng incident và node_type RootCause; unique(incident_id,cause_rank); đúng một primary khi đóng.

### incident_evidence
Mục đích: decisive evidence curator xác nhận.

| Column | Type | Key | Description |
|---|---|---|---|
| incident_evidence_id | UUID | PK | Mã evidence |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| node_id | UUID | FK → causal_nodes.node_id | Node chứng minh |
| evidence_type | VARCHAR(50) |  | Log, Metric, Record, ExpertAssessment |
| source_table, source_record_id | VARCHAR(100), UUID |  | Nguồn, record nullable |
| evidence_timestamp | TIMESTAMPTZ |  | Lúc evidence |
| evidence_summary | TEXT | Restricted | Diễn giải decisive evidence |
| is_decisive | BOOLEAN | Restricted | Cờ decisive |

Rules: node cùng incident; record nguồn operational phải tồn tại; luôn restricted.

### incident_outcomes
Mục đích: hậu quả thật chốt cuối kỳ.

| Column | Type | Key | Description |
|---|---|---|---|
| incident_outcome_id | UUID | PK | Mã outcome |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| node_id | UUID | FK → causal_nodes.node_id | Node Outcome |
| outcome_type | VARCHAR(100) |  | RevenueLoss, SLADegradation, ChurnRisk, Stockout, Delay, RefundIncrease |
| measured_at | TIMESTAMPTZ |  | Lúc chốt |
| metric_name, metric_value | VARCHAR(100), NUMERIC(18,4) |  | Metric |
| financial_impact | NUMERIC(18,2) |  | Tác động tiền, nullable |
| currency_code | CHAR(3) |  | ISO 4217, nullable |

Rules: node Outcome cùng incident; measured sau incident start; restricted.

## 8. Benchmark / Evaluation — restricted

### benchmark_cases
Mục đích: benchmark case và cửa sổ quan sát.

| Column | Type | Key | Description |
|---|---|---|---|
| benchmark_case_id | UUID | PK | Mã case |
| incident_id | UUID | FK → incidents.incident_id | Incident |
| case_name | VARCHAR(250) | UQ | Tên case |
| split | VARCHAR(20) |  | Train, Validation, Test |
| observation_start_time, observation_cutoff_time | TIMESTAMPTZ |  | Cửa sổ AI thấy |
| created_at | TIMESTAMPTZ |  | Lúc tạo |
| status | VARCHAR(20) |  | Draft, Active, Retired |

Rules: start ≤ cutoff; Test không dùng tune; freeze version/cutoff trước đánh giá.

### benchmark_observations
Mục đích: registry record operational được cấp cho case.

| Column | Type | Key | Description |
|---|---|---|---|
| benchmark_observation_id | UUID | PK | Mã observation |
| benchmark_case_id | UUID | FK → benchmark_cases.benchmark_case_id | Case |
| source_table | VARCHAR(100) |  | Bảng operational allowlist |
| source_record_id | UUID |  | Record nguồn |
| observed_at | TIMESTAMPTZ |  | Event time |
| observation_role | VARCHAR(30) |  | Signal, Context, Correlation |

Rules: unique(benchmark_case_id,source_table,source_record_id); trong window và không sau cutoff; cấm restricted source.

### evaluation_targets
Mục đích: nhãn/rubric chấm AI, không cấp AI Analyst.

| Column | Type | Key | Description |
|---|---|---|---|
| evaluation_target_id | UUID | PK | Mã target |
| benchmark_case_id | UUID | FK → benchmark_cases.benchmark_case_id | Case |
| target_type | VARCHAR(50) |  | RootCause, CausalPath, AffectedEntity, RecommendedAction, Outcome |
| target_value | JSONB | Restricted | Nhãn/rubric |
| causal_node_id | UUID | FK → causal_nodes.node_id, nullable | Node truth |
| scoring_weight | NUMERIC(8,4) |  | Trọng số |
| created_at | TIMESTAMPTZ |  | Lúc tạo |

Rules: node thuộc incident của case; weight không âm; không materialize target vào AI context.

## 9. Data Access Boundary

| Role | Được truy cập | Cấm truy cập |
|---|---|---|
| AI Analyst | Master, Transaction, Business/Operational, Marketing, Finance; `ai_incident_observations` (View an toàn), `incident_entities`; allowlisted benchmark observations trước cutoff | `incidents` (bảng trực tiếp do chứa scenario_id), causal_nodes, causal_links, incident_causes, incident_evidence, incident_outcomes, benchmark_cases, evaluation_targets và metadata truth |
| Simulator | Toàn bộ theo quyền kỹ thuật | Không cấp trực tiếp AI runtime |
| Evaluator | Truth, benchmark, output AI | Không đưa truth/target vào prompt/retrieval |
| Curator/admin | Toàn bộ có audit | Không tạo view trộn truth và observation cho AI |

Enforce bằng schema/database hoặc service account tách biệt; AI chỉ gọi read-only allowlisted view/API, ACL/RLS deny-by-default; log query/export. Scan prompt, embedding, cache, dashboard và incidents.summary để không lộ root cause, decisive evidence, outcome, target.

## 10. Infrastructure & Governance Data

### entity_registry
Mục đích: Danh mục kiểm soát các loại entity (polymorphic controlled vocabulary) để kiểm tra tính hợp lệ của tham chiếu đa hình.

| Column | Type | Key | Description |
|---|---|---|---|
| entity_type | VARCHAR(50) | PK | Tên loại entity (Customer, Product, Supplier, Warehouse, Order, PurchaseOrder, Shipment, Payment, Campaign) |
| description | VARCHAR(250) |  | Mô tả thực thể |
| is_operational | BOOLEAN |  | Cờ đánh dấu entity thuộc tầng vận hành |
| is_ai_visible | BOOLEAN |  | Cờ đánh dấu entity AI được phép quan sát |
| created_at | TIMESTAMPTZ |  | Thời điểm tạo |

Rules: Khóa chính cố định; dùng bởi hàm `validate_entity_reference()`.

### audit_log
Mục đích: Lưu vết kiểm toán bảo mật và các thao tác nhạy cảm trên hệ thống Enterprise Digital Twin.

| Column | Type | Key | Description |
|---|---|---|---|
| audit_log_id | UUID | PK | Mã log |
| event_timestamp | TIMESTAMPTZ |  | Thời điểm ghi nhận sự kiện |
| actor_role | VARCHAR(100) |  | Vai trò thực hiện (edt_ai_analyst, edt_simulator,...) |
| action_type | VARCHAR(50) |  | Loại hành vi (QUERY, ACCESS_DENIED, INJECT_INCIDENT,...) |
| object_type | VARCHAR(100) |  | Đối tượng bị tác động |
| object_id | UUID |  | ID của đối tượng |
| success | BOOLEAN |  | Kết quả thực thi |
| metadata | JSONB |  | Chi tiết bổ sung (không lưu nội dung nhạy cảm) |

Rules: Chỉ ghi (Append-only); không lưu câu lệnh SQL đầy đủ chứa chân lý ngầm.

## 11. Integrity, propagation, indexing và checklist audit

- Enforce FK trước child ingest. Polymorphic entity_type/entity_id và reference_entity_type/reference_entity_id phải validate allowlist + entity registry; dữ liệu sai vào quarantine.
- Chuỗi propagation truy nguyên bằng khóa và thời gian: supplier → purchase_orders → inventory_movements/inventory_snapshots → orders → shipments → tickets/reviews → financial_transactions. Marketing/behavior nối campaign/customer/order khi biết. incident_entities là observed scope, causal graph là truth xác nhận.
- Child không trước parent; history/session không lùi; link/node cùng incident; outcome chốt sau observation cutoff. Late arrival không backfill case đã freeze, phát hành version mới.
- Index mọi FK; composite index: (customer_id,order_timestamp), (warehouse_id,product_id,snapshot_timestamp DESC), (warehouse_id,product_id,movement_timestamp), (order_id,status_timestamp), (payment_id,status_timestamp), (shipment_id,status_timestamp), (incident_id,observed_at), (benchmark_case_id,observed_at). Partition tháng cho event lớn; graph restricted index theo incident/node.

Checklist:

- [ ] PK UUID duy nhất; FK tồn tại, đúng parent/kiểu.
- [ ] cause_node_id và effect_node_id đều FK tới causal_nodes.node_id và cùng incident với causal link.
- [ ] Không có bảng/cột reference không tồn tại; causes/evidence/outcomes/targets cùng incident/case/node phù hợp.
- [ ] Tất cả tiền là NUMERIC có currency khi cần; total và ledger/history/time nhất quán.
- [ ] Polymorphic entity đã validate; causal DAG hợp lệ, RootCause/Outcome đầy đủ.
- [ ] AI leakage scan qua views, exports, embeddings, logs, prompts không có truth, decisive evidence, outcomes hay evaluation targets.
- [ ] Dataset version, cutoff, vocabulary, simulator seed, allowlist manifest đã freeze.
