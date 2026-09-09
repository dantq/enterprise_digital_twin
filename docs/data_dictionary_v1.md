# Enterprise Digital Twin
# Data Dictionary V1

## 1. Design Principles

The enterprise digital twin must represent:

- realistic business entities
- transactional data
- temporal behavior
- dependencies between business domains
- normal business behavior
- abnormal business events
- hidden ground truth

Data must not be generated as independent random variables.

---

# 2. Master Data

## 2.1 Customer

Table: customers

| Column | Type | Description |
|---|---|---|
| customer_id | UUID | Unique customer identifier |
| customer_segment | VARCHAR | New / Regular / VIP / At-Risk / Churned |
| acquisition_channel | VARCHAR | Marketing acquisition source |
| registration_date | DATE | Customer registration date |
| region | VARCHAR | Customer region |
| age_group | VARCHAR | Customer age group |
| status | VARCHAR | Active / Inactive / Churned |

---

## 2.2 Product

Table: products

| Column | Type | Description |
|---|---|---|
| product_id | UUID | Unique product identifier |
| category_id | UUID | Product category |
| product_name | VARCHAR | Product name |
| unit_price | NUMERIC | Selling price |
| unit_cost | NUMERIC | Cost |
| margin_rate | NUMERIC | Gross margin rate |
| demand_class | VARCHAR | High / Medium / Low |
| launch_date | DATE | Product launch date |
| status | VARCHAR | Active / Discontinued |

---

## 2.3 Supplier

Table: suppliers

| Column | Type | Description |
|---|---|---|
| supplier_id | UUID | Unique supplier identifier |
| supplier_name | VARCHAR | Supplier name |
| reliability_score | NUMERIC | Historical reliability |
| average_lead_time_days | NUMERIC | Expected lead time |
| region | VARCHAR | Supplier region |
| status | VARCHAR | Active / Suspended |

---

## 2.4 Warehouse

Table: warehouses

| Column | Type | Description |
|---|---|---|
| warehouse_id | UUID | Warehouse identifier |
| warehouse_name | VARCHAR | Warehouse name |
| region | VARCHAR | Warehouse region |
| capacity | INTEGER | Storage capacity |
| daily_processing_capacity | INTEGER | Daily processing capacity |
| status | VARCHAR | Active / Inactive |

---

# 3. Sales Domain

## 3.1 Orders

Table: orders

| Column | Type | Description |
|---|---|---|
| order_id | UUID | Order identifier |
| customer_id | UUID | Customer |
| order_timestamp | TIMESTAMP | Order time |
| channel | VARCHAR | Website / App / Marketplace / Store |
| warehouse_id | UUID | Fulfillment warehouse |
| order_status | VARCHAR | Order status |
| subtotal | NUMERIC | Product subtotal |
| discount_amount | NUMERIC | Discount |
| shipping_fee | NUMERIC | Shipping fee |
| total_amount | NUMERIC | Final order amount |

Business rule:

total_amount =
subtotal - discount_amount + shipping_fee

---

## 3.2 Order Items

Table: order_items

| Column | Type | Description |
|---|---|---|
| order_item_id | UUID | Item identifier |
| order_id | UUID | Order |
| product_id | UUID | Product |
| quantity | INTEGER | Quantity |
| unit_price | NUMERIC | Selling price |
| discount_amount | NUMERIC | Discount |
| item_total | NUMERIC | Item revenue |

Business rule:

item_total =
quantity × unit_price - discount_amount

---

# 4. Payment Domain

## 4.1 Payments

Table: payments

| Column | Type | Description |
|---|---|---|
| payment_id | UUID | Payment identifier |
| order_id | UUID | Related order |
| payment_timestamp | TIMESTAMP | Payment time |
| payment_method | VARCHAR | Payment method |
| payment_status | VARCHAR | Success / Failed / Pending |
| amount | NUMERIC | Payment amount |
| failure_reason | VARCHAR | Failure reason if applicable |

---

# 5. Inventory Domain

## 5.1 Inventory Snapshot

Table: inventory_snapshots

| Column | Type | Description |
|---|---|---|
| snapshot_id | UUID | Snapshot identifier |
| timestamp | TIMESTAMP | Observation time |
| warehouse_id | UUID | Warehouse |
| product_id | UUID | Product |
| stock_on_hand | INTEGER | Physical stock |
| stock_reserved | INTEGER | Reserved stock |
| available_stock | INTEGER | Available stock |

Business rule:

available_stock =
stock_on_hand - stock_reserved

---

## 5.2 Inventory Movements

Table: inventory_movements

| Column | Type | Description |
|---|---|---|
| movement_id | UUID | Movement identifier |
| timestamp | TIMESTAMP | Movement time |
| warehouse_id | UUID | Warehouse |
| product_id | UUID | Product |
| movement_type | VARCHAR | Sale / Receive / Return / Damage / Transfer |
| quantity | INTEGER | Quantity |
| reference_id | UUID | Related business transaction |

---

# 6. Procurement Domain

## 6.1 Purchase Orders

Table: purchase_orders

| Column | Type | Description |
|---|---|---|
| po_id | UUID | Purchase order |
| supplier_id | UUID | Supplier |
| warehouse_id | UUID | Destination warehouse |
| created_at | TIMESTAMP | Creation time |
| expected_delivery_date | DATE | Expected delivery |
| actual_delivery_date | DATE | Actual delivery |
| status | VARCHAR | Open / Received / Delayed / Cancelled |

---

## 6.2 Purchase Order Items

Table: purchase_order_items

| Column | Type | Description |
|---|---|---|
| po_item_id | UUID | Item identifier |
| po_id | UUID | Purchase order |
| product_id | UUID | Product |
| quantity | INTEGER | Ordered quantity |
| unit_cost | NUMERIC | Purchase cost |

---

# 7. Logistics Domain

## 7.1 Shipments

Table: shipments

| Column | Type | Description |
|---|---|---|
| shipment_id | UUID | Shipment identifier |
| order_id | UUID | Order |
| carrier_id | UUID | Carrier |
| warehouse_id | UUID | Origin warehouse |
| created_at | TIMESTAMP | Shipment creation |
| promised_delivery_date | DATE | Promised date |
| actual_delivery_date | DATE | Actual delivery |
| shipment_status | VARCHAR | Processing / Shipped / Delivered / Delayed |

---

# 8. Customer Service Domain

## 8.1 Customer Tickets

Table: customer_tickets

| Column | Type | Description |
|---|---|---|
| ticket_id | UUID | Ticket identifier |
| customer_id | UUID | Customer |
| order_id | UUID | Related order |
| created_at | TIMESTAMP | Ticket time |
| category | VARCHAR | Complaint / Question / Return / Delivery |
| priority | VARCHAR | Low / Medium / High |
| resolution_time_hours | NUMERIC | Resolution time |
| status | VARCHAR | Open / Resolved |

---

## 8.2 Reviews

Table: reviews

| Column | Type | Description |
|---|---|---|
| review_id | UUID | Review identifier |
| customer_id | UUID | Customer |
| product_id | UUID | Product |
| order_id | UUID | Related order |
| created_at | TIMESTAMP | Review time |
| rating | INTEGER | 1–5 rating |
| sentiment | VARCHAR | Positive / Neutral / Negative |

---

# 9. Marketing Domain

## 9.1 Campaigns

Table: marketing_campaigns

| Column | Type | Description |
|---|---|---|
| campaign_id | UUID | Campaign identifier |
| campaign_name | VARCHAR | Campaign name |
| channel | VARCHAR | Marketing channel |
| start_date | DATE | Start date |
| end_date | DATE | End date |
| budget | NUMERIC | Campaign budget |
| target_segment | VARCHAR | Target customer segment |

---

## 9.2 Marketing Performance

Table: marketing_daily_metrics

| Column | Type | Description |
|---|---|---|
| metric_date | DATE | Date |
| campaign_id | UUID | Campaign |
| impressions | INTEGER | Impressions |
| clicks | INTEGER | Clicks |
| conversions | INTEGER | Conversions |
| spend | NUMERIC | Advertising spend |
| attributed_revenue | NUMERIC | Attributed revenue |

---

# 10. Finance Domain

## 10.1 Financial Transactions

Table: financial_transactions

| Column | Type | Description |
|---|---|---|
| transaction_id | UUID | Transaction identifier |
| timestamp | TIMESTAMP | Transaction time |
| transaction_type | VARCHAR | Revenue / Cost / Refund / Marketing |
| reference_id | UUID | Related transaction |
| amount | NUMERIC | Amount |
| account | VARCHAR | Financial account |

---

# 11. Enterprise Events

Table: enterprise_events

This table records observable business events.

| Column | Type | Description |
|---|---|---|
| event_id | UUID | Event identifier |
| timestamp | TIMESTAMP | Event time |
| event_type | VARCHAR | Business event |
| domain | VARCHAR | Affected domain |
| severity | VARCHAR | Low / Medium / High |
| entity_type | VARCHAR | Affected entity |
| entity_id | UUID | Affected entity |

Important:

The event table must NOT explicitly reveal hidden root causes to the AI.

---

# 12. Hidden Ground Truth

Ground truth is stored separately from observable enterprise data.

Table:

ground_truth_incidents

| Column | Type | Description |
|---|---|---|
| incident_id | UUID | Incident identifier |
| scenario_id | VARCHAR | Scenario |
| start_time | TIMESTAMP | Start |
| end_time | TIMESTAMP | End |
| root_cause | VARCHAR | True root cause |
| causal_chain | JSONB | True causal chain |
| affected_entities | JSONB | Affected entities |
| expected_effects | JSONB | Expected consequences |

This table must never be included in the AI Analyst observation layer.

---

# 13. Data Visibility Layers

## AI Observable

- customers
- products
- orders
- payments
- inventory
- procurement
- logistics
- marketing
- customer service
- finance
- observable events

## AI Hidden

- root cause
- causal graph ground truth
- scenario ID
- incident generation parameters
- hidden intervention variables
- expected causal chain

---

# 14. Core Causal Relationships

Customer
→ Order
→ Payment
→ Fulfillment
→ Shipment
→ Delivery
→ Customer feedback

Supplier
→ Purchase Order
→ Receiving
→ Inventory
→ Stockout
→ Order cancellation
→ Revenue

Marketing
→ Traffic
→ Orders
→ Revenue

Product quality
→ Returns
→ Complaints
→ Rating
→ Customer retention

Payment system
→ Payment failures
→ Order completion
→ Revenue

Logistics
→ Delivery delay
→ Complaints
→ Customer satisfaction
→ Churn