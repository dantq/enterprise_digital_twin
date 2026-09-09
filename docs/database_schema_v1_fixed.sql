-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 1: Master Data
-- ============================================================

-- ------------------------------------------------------------
-- 0. Extensions
-- ------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================
-- 1. CUSTOMERS
-- ============================================================

CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    customer_segment VARCHAR(30) NOT NULL,
    acquisition_channel VARCHAR(50) NOT NULL,
    registration_date DATE NOT NULL,
    region VARCHAR(100) NOT NULL,
    age_group VARCHAR(30),
    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_customers_segment
        CHECK (
            customer_segment IN (
                'New',
                'Regular',
                'VIP',
                'At-Risk',
                'Churned'
            )
        ),

    CONSTRAINT chk_customers_status
        CHECK (
            status IN (
                'Active',
                'Inactive',
                'Blocked'
            )
        ),

    CONSTRAINT chk_customers_registration_date
        CHECK (
            registration_date <= created_at::DATE
        )
);


-- ============================================================
-- 2. CATEGORIES
-- ============================================================

CREATE TABLE categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    category_name VARCHAR(200) NOT NULL,
    parent_category_id UUID NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT uq_categories_name
        UNIQUE (category_name),

    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_category_id)
        REFERENCES categories(category_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_categories_status
        CHECK (
            status IN (
                'Active',
                'Inactive'
            )
        ),

    CONSTRAINT chk_categories_not_self_parent
        CHECK (
            parent_category_id IS NULL
            OR parent_category_id <> category_id
        )
);


-- ============================================================
-- 3. PRODUCTS
-- ============================================================

CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    category_id UUID NOT NULL,

    product_name VARCHAR(250) NOT NULL,

    unit_price NUMERIC(18,2) NOT NULL,
    unit_cost NUMERIC(18,2) NOT NULL,

    margin_rate NUMERIC(8,4) NOT NULL,

    demand_class VARCHAR(20) NOT NULL,
    demand_volatility NUMERIC(8,4) NOT NULL DEFAULT 0,

    launch_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_products_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_products_cost
        CHECK (unit_cost >= 0),

    CONSTRAINT chk_products_margin
        CHECK (
            margin_rate >= 0
            AND margin_rate <= 1
        ),

    CONSTRAINT chk_products_demand_class
        CHECK (
            demand_class IN (
                'High',
                'Medium',
                'Low'
            )
        ),

    CONSTRAINT chk_products_volatility
        CHECK (
            demand_volatility >= 0
        ),

    CONSTRAINT chk_products_status
        CHECK (
            status IN (
                'Active',
                'Discontinued',
                'Inactive'
            )
        ),

    CONSTRAINT chk_products_price_cost
        CHECK (
            unit_price >= unit_cost
        ),

    CONSTRAINT chk_products_margin_formula
        CHECK (
            (
                unit_price = 0
                AND margin_rate = 0
            )
            OR
            (
                unit_price > 0
                AND margin_rate =
                    ROUND(
                        (unit_price - unit_cost)
                        / unit_price,
                        4
                    )
            )
        )
);


-- ============================================================
-- 4. SUPPLIERS
-- ============================================================

CREATE TABLE suppliers (
    supplier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    supplier_name VARCHAR(250) NOT NULL,

    reliability_score NUMERIC(8,4) NOT NULL,

    average_lead_time_days NUMERIC(10,2) NOT NULL,
    lead_time_std_days NUMERIC(10,2) NOT NULL DEFAULT 0,

    region VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT uq_suppliers_name
        UNIQUE (supplier_name),

    CONSTRAINT chk_suppliers_reliability
        CHECK (
            reliability_score >= 0
            AND reliability_score <= 1
        ),

    CONSTRAINT chk_suppliers_lead_time
        CHECK (
            average_lead_time_days >= 0
        ),

    CONSTRAINT chk_suppliers_lead_time_std
        CHECK (
            lead_time_std_days >= 0
        ),

    CONSTRAINT chk_suppliers_status
        CHECK (
            status IN (
                'Active',
                'Suspended',
                'Inactive'
            )
        )
);


-- ============================================================
-- 5. SUPPLIER PRODUCTS
-- ============================================================

CREATE TABLE supplier_products (
    supplier_product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    supplier_id UUID NOT NULL,
    product_id UUID NOT NULL,

    supplier_sku VARCHAR(100),

    unit_cost NUMERIC(18,2) NOT NULL,

    is_primary BOOLEAN NOT NULL DEFAULT FALSE,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT fk_supplier_products_supplier
        FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_supplier_products_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_supplier_products_pair
        UNIQUE (supplier_id, product_id),

    CONSTRAINT chk_supplier_products_cost
        CHECK (
            unit_cost >= 0
        ),

    CONSTRAINT chk_supplier_products_status
        CHECK (
            status IN (
                'Active',
                'Inactive'
            )
        )
);


-- ============================================================
-- 6. WAREHOUSES
-- ============================================================

CREATE TABLE warehouses (
    warehouse_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    warehouse_name VARCHAR(200) NOT NULL,

    region VARCHAR(100) NOT NULL,

    capacity NUMERIC(18,4) NOT NULL,
    daily_processing_capacity NUMERIC(18,4) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT uq_warehouses_name
        UNIQUE (warehouse_name),

    CONSTRAINT chk_warehouses_capacity
        CHECK (
            capacity >= 0
        ),

    CONSTRAINT chk_warehouses_processing_capacity
        CHECK (
            daily_processing_capacity >= 0
        ),

    CONSTRAINT chk_warehouses_status
        CHECK (
            status IN (
                'Active',
                'Constrained',
                'Inactive'
            )
        )
);


-- ============================================================
-- 7. CARRIERS
-- ============================================================

CREATE TABLE carriers (
    carrier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    carrier_name VARCHAR(200) NOT NULL,

    average_delivery_days NUMERIC(10,2) NOT NULL,

    delivery_reliability NUMERIC(8,4) NOT NULL,

    region VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT uq_carriers_name
        UNIQUE (carrier_name),

    CONSTRAINT chk_carriers_delivery_days
        CHECK (
            average_delivery_days >= 0
        ),

    CONSTRAINT chk_carriers_reliability
        CHECK (
            delivery_reliability >= 0
            AND delivery_reliability <= 1
        ),

    CONSTRAINT chk_carriers_status
        CHECK (
            status IN (
                'Active',
                'Suspended',
                'Inactive'
            )
        )
);


-- ============================================================
-- 8. PAYMENT METHODS
-- ============================================================

CREATE TABLE payment_methods (
    payment_method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    method_name VARCHAR(100) NOT NULL,

    provider VARCHAR(150) NOT NULL,

    failure_rate_baseline NUMERIC(8,4) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT uq_payment_methods_name
        UNIQUE (method_name),

    CONSTRAINT chk_payment_methods_failure_rate
        CHECK (
            failure_rate_baseline >= 0
            AND failure_rate_baseline <= 1
        ),

    CONSTRAINT chk_payment_methods_status
        CHECK (
            status IN (
                'Active',
                'Inactive'
            )
        )
);


-- ============================================================
-- 9. INDEXES — MASTER DATA
-- ============================================================

CREATE INDEX idx_products_category
    ON products(category_id);

CREATE INDEX idx_supplier_products_supplier
    ON supplier_products(supplier_id);

CREATE INDEX idx_supplier_products_product
    ON supplier_products(product_id);

CREATE UNIQUE INDEX uq_supplier_products_one_primary_active
    ON supplier_products(product_id)
    WHERE is_primary = TRUE
      AND status = 'Active';

CREATE INDEX idx_categories_parent
    ON categories(parent_category_id);


-- ============================================================
-- END OF MASTER DATA SCHEMA
-- ============================================================

-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 2: Transaction Data
-- ============================================================


-- ============================================================
-- 10. ORDERS
-- ============================================================

CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    customer_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,

    order_timestamp TIMESTAMPTZ NOT NULL,

    channel VARCHAR(50) NOT NULL,

    order_status VARCHAR(30) NOT NULL DEFAULT 'Pending',

    subtotal NUMERIC(18,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    shipping_fee NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(18,2) NOT NULL DEFAULT 0,

    currency_code CHAR(3) NOT NULL DEFAULT 'VND',

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_orders_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_orders_status
        CHECK (
            order_status IN (
                'Pending',
                'Paid',
                'Fulfilled',
                'Shipped',
                'Delivered',
                'Cancelled',
                'Refunded'
            )
        ),

    CONSTRAINT chk_orders_subtotal
        CHECK (subtotal >= 0),

    CONSTRAINT chk_orders_discount
        CHECK (
            discount_amount >= 0
            AND discount_amount <= subtotal
        ),

    CONSTRAINT chk_orders_shipping_fee
        CHECK (shipping_fee >= 0),

    CONSTRAINT chk_orders_total
        CHECK (
            total_amount =
            subtotal - discount_amount + shipping_fee
        ),

    CONSTRAINT chk_orders_currency
        CHECK (currency_code ~ '^[A-Z]{3}$')
);


-- ============================================================
-- 11. ORDER ITEMS
-- ============================================================

CREATE TABLE order_items (
    order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,
    product_id UUID NOT NULL,

    quantity NUMERIC(18,4) NOT NULL,

    unit_price NUMERIC(18,2) NOT NULL,
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    item_total NUMERIC(18,2) NOT NULL,

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_order_items_product
        UNIQUE (order_id, product_id),

    CONSTRAINT chk_order_items_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_order_items_unit_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_order_items_discount
        CHECK (
            discount_amount >= 0
            AND discount_amount <=
                quantity * unit_price
        ),

    CONSTRAINT chk_order_items_total
        CHECK (
            item_total =
            ROUND(
                quantity * unit_price
                - discount_amount,
                2
            )
        )
);


-- ============================================================
-- 12. ORDER STATUS HISTORY
-- ============================================================

CREATE TABLE order_status_history (
    order_status_history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    status VARCHAR(30) NOT NULL,

    status_timestamp TIMESTAMPTZ NOT NULL,

    actor_type VARCHAR(30) NOT NULL,

    reason_code VARCHAR(100),

    CONSTRAINT fk_order_status_history_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_order_status_history_status
        CHECK (
            status IN (
                'Pending',
                'Paid',
                'Fulfilled',
                'Shipped',
                'Delivered',
                'Cancelled',
                'Refunded'
            )
        ),

    CONSTRAINT chk_order_status_history_actor
        CHECK (
            actor_type IN (
                'System',
                'Customer',
                'Staff',
                'Carrier'
            )
        ),

    CONSTRAINT uq_order_status_history_timestamp
        UNIQUE (
            order_id,
            status_timestamp
        )
);


-- ============================================================
-- 13. PAYMENTS
-- ============================================================

CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    payment_method_id UUID NOT NULL,

    payment_timestamp TIMESTAMPTZ NOT NULL,

    amount NUMERIC(18,2) NOT NULL,

    currency_code CHAR(3) NOT NULL DEFAULT 'VND',

    payment_status VARCHAR(30) NOT NULL DEFAULT 'Initiated',

    provider_transaction_ref VARCHAR(150) NOT NULL,

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_payments_method
        FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(payment_method_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_payments_provider_reference
        UNIQUE (provider_transaction_ref),

    CONSTRAINT chk_payments_amount
        CHECK (amount > 0),

    CONSTRAINT chk_payments_status
        CHECK (
            payment_status IN (
                'Initiated',
                'Authorized',
                'Captured',
                'Failed',
                'Refunded'
            )
        ),

    CONSTRAINT chk_payments_currency
        CHECK (currency_code ~ '^[A-Z]{3}$')
);


-- ============================================================
-- 14. PAYMENT STATUS HISTORY
-- ============================================================

CREATE TABLE payment_status_history (
    payment_status_history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    payment_id UUID NOT NULL,

    status VARCHAR(30) NOT NULL,

    status_timestamp TIMESTAMPTZ NOT NULL,

    failure_code VARCHAR(100),

    CONSTRAINT fk_payment_status_history_payment
        FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_payment_status_history_status
        CHECK (
            status IN (
                'Initiated',
                'Authorized',
                'Captured',
                'Failed',
                'Refunded'
            )
        ),

    CONSTRAINT uq_payment_status_history_timestamp
        UNIQUE (
            payment_id,
            status_timestamp
        )
);


-- ============================================================
-- 15. INVENTORY SNAPSHOTS
-- ============================================================

CREATE TABLE inventory_snapshots (
    inventory_snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    warehouse_id UUID NOT NULL,
    product_id UUID NOT NULL,

    snapshot_timestamp TIMESTAMPTZ NOT NULL,

    on_hand_quantity NUMERIC(18,4) NOT NULL,
    reserved_quantity NUMERIC(18,4) NOT NULL DEFAULT 0,
    available_quantity NUMERIC(18,4) NOT NULL,
    reorder_point NUMERIC(18,4) NOT NULL DEFAULT 0,

    CONSTRAINT fk_inventory_snapshots_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_inventory_snapshots_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_inventory_snapshots_point
        UNIQUE (
            warehouse_id,
            product_id,
            snapshot_timestamp
        ),

    CONSTRAINT chk_inventory_snapshots_on_hand
        CHECK (on_hand_quantity >= 0),

    CONSTRAINT chk_inventory_snapshots_reserved
        CHECK (
            reserved_quantity >= 0
            AND reserved_quantity <= on_hand_quantity
        ),

    CONSTRAINT chk_inventory_snapshots_available
        CHECK (
            available_quantity =
            on_hand_quantity - reserved_quantity
        ),

    CONSTRAINT chk_inventory_snapshots_reorder
        CHECK (reorder_point >= 0)
);


-- ============================================================
-- 16. INVENTORY MOVEMENTS
-- ============================================================

CREATE TABLE inventory_movements (
    inventory_movement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    warehouse_id UUID NOT NULL,
    product_id UUID NOT NULL,

    movement_timestamp TIMESTAMPTZ NOT NULL,

    movement_type VARCHAR(30) NOT NULL,

    quantity_delta NUMERIC(18,4) NOT NULL,

    reference_entity_type VARCHAR(50),
    reference_entity_id UUID,

    reason_code VARCHAR(100),

    CONSTRAINT fk_inventory_movements_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_inventory_movements_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_inventory_movements_type
        CHECK (
            movement_type IN (
                'Receipt',
                'Reservation',
                'Release',
                'Pick',
                'Adjustment',
                'Return'
            )
        ),

    CONSTRAINT chk_inventory_movements_reference
        CHECK (
            (
                reference_entity_type IS NULL
                AND reference_entity_id IS NULL
            )
            OR
            (
                reference_entity_type IS NOT NULL
                AND reference_entity_id IS NOT NULL
            )
        )
);


-- ============================================================
-- 17. PURCHASE ORDERS
-- ============================================================

CREATE TABLE purchase_orders (
    purchase_order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    supplier_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,

    order_timestamp TIMESTAMPTZ NOT NULL,

    expected_delivery_timestamp TIMESTAMPTZ,

    received_timestamp TIMESTAMPTZ,

    po_status VARCHAR(30) NOT NULL DEFAULT 'Draft',

    total_amount NUMERIC(18,2) NOT NULL DEFAULT 0,

    currency_code CHAR(3) NOT NULL DEFAULT 'VND',

    CONSTRAINT fk_purchase_orders_supplier
        FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_purchase_orders_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_purchase_orders_status
        CHECK (
            po_status IN (
                'Draft',
                'Ordered',
                'PartiallyReceived',
                'Received',
                'Cancelled'
            )
        ),

    CONSTRAINT chk_purchase_orders_total
        CHECK (total_amount >= 0),

    CONSTRAINT chk_purchase_orders_expected_delivery
        CHECK (
            expected_delivery_timestamp IS NULL
            OR expected_delivery_timestamp >= order_timestamp
        ),

    CONSTRAINT chk_purchase_orders_received
        CHECK (
            received_timestamp IS NULL
            OR received_timestamp >= order_timestamp
        ),

    CONSTRAINT chk_purchase_orders_currency
        CHECK (currency_code ~ '^[A-Z]{3}$')
);


-- ============================================================
-- 18. PURCHASE ORDER ITEMS
-- ============================================================

CREATE TABLE purchase_order_items (
    purchase_order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    purchase_order_id UUID NOT NULL,
    product_id UUID NOT NULL,

    ordered_quantity NUMERIC(18,4) NOT NULL,
    received_quantity NUMERIC(18,4) NOT NULL DEFAULT 0,

    unit_cost NUMERIC(18,2) NOT NULL,
    item_total NUMERIC(18,2) NOT NULL,

    CONSTRAINT fk_purchase_order_items_order
        FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_purchase_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_purchase_order_items_product
        UNIQUE (
            purchase_order_id,
            product_id
        ),

    CONSTRAINT chk_purchase_order_items_ordered
        CHECK (ordered_quantity > 0),

    CONSTRAINT chk_purchase_order_items_received
        CHECK (
            received_quantity >= 0
            AND received_quantity <= ordered_quantity
        ),

    CONSTRAINT chk_purchase_order_items_cost
        CHECK (unit_cost >= 0),

    CONSTRAINT chk_purchase_order_items_total
        CHECK (
            item_total =
            ROUND(
                ordered_quantity * unit_cost,
                2
            )
        )
);


-- ============================================================
-- 19. SHIPMENTS
-- ============================================================

CREATE TABLE shipments (
    shipment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    carrier_id UUID NOT NULL,

    shipment_timestamp TIMESTAMPTZ NOT NULL,

    estimated_delivery_timestamp TIMESTAMPTZ,

    delivered_timestamp TIMESTAMPTZ,

    shipment_status VARCHAR(30) NOT NULL DEFAULT 'Created',

    tracking_number VARCHAR(150) NOT NULL,

    CONSTRAINT fk_shipments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_shipments_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_shipments_carrier
        FOREIGN KEY (carrier_id)
        REFERENCES carriers(carrier_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_shipments_tracking
        UNIQUE (tracking_number),

    CONSTRAINT chk_shipments_status
        CHECK (
            shipment_status IN (
                'Created',
                'PickedUp',
                'InTransit',
                'Delivered',
                'Failed',
                'Returned'
            )
        ),

    CONSTRAINT chk_shipments_estimated_delivery
        CHECK (
            estimated_delivery_timestamp IS NULL
            OR estimated_delivery_timestamp >= shipment_timestamp
        ),

    CONSTRAINT chk_shipments_delivered
        CHECK (
            delivered_timestamp IS NULL
            OR delivered_timestamp >= shipment_timestamp
        )
);


-- ============================================================
-- 20. SHIPMENT STATUS HISTORY
-- ============================================================

CREATE TABLE shipment_status_history (
    shipment_status_history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    shipment_id UUID NOT NULL,

    status VARCHAR(30) NOT NULL,

    status_timestamp TIMESTAMPTZ NOT NULL,

    location_region VARCHAR(100),

    exception_code VARCHAR(100),

    CONSTRAINT fk_shipment_status_history_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_shipment_status_history_status
        CHECK (
            status IN (
                'Created',
                'PickedUp',
                'InTransit',
                'Delivered',
                'Failed',
                'Returned'
            )
        ),

    CONSTRAINT uq_shipment_status_history_timestamp
        UNIQUE (
            shipment_id,
            status_timestamp
        )
);


-- ============================================================
-- 21. INDEXES — TRANSACTION DATA
-- ============================================================

CREATE INDEX idx_orders_customer_timestamp
ON orders (
    customer_id,
    order_timestamp
);

CREATE INDEX idx_orders_warehouse_timestamp
ON orders (
    warehouse_id,
    order_timestamp
);

CREATE INDEX idx_order_items_product
ON order_items (
    product_id
);

CREATE INDEX idx_order_status_history_order_timestamp
ON order_status_history (
    order_id,
    status_timestamp
);

CREATE INDEX idx_payments_order_timestamp
ON payments (
    order_id,
    payment_timestamp
);

CREATE INDEX idx_payment_status_history_payment_timestamp
ON payment_status_history (
    payment_id,
    status_timestamp
);

CREATE INDEX idx_inventory_snapshots_product_time
ON inventory_snapshots (
    warehouse_id,
    product_id,
    snapshot_timestamp DESC
);

CREATE INDEX idx_inventory_movements_product_time
ON inventory_movements (
    warehouse_id,
    product_id,
    movement_timestamp
);

CREATE INDEX idx_purchase_orders_supplier_timestamp
ON purchase_orders (
    supplier_id,
    order_timestamp
);

CREATE INDEX idx_purchase_orders_warehouse_timestamp
ON purchase_orders (
    warehouse_id,
    order_timestamp
);

CREATE INDEX idx_purchase_order_items_product
ON purchase_order_items (
    product_id
);

CREATE INDEX idx_shipments_order_timestamp
ON shipments (
    order_id,
    shipment_timestamp
);

CREATE INDEX idx_shipments_carrier_timestamp
ON shipments (
    carrier_id,
    shipment_timestamp
);

CREATE INDEX idx_shipment_status_history_shipment_timestamp
ON shipment_status_history (
    shipment_id,
    status_timestamp
);


-- ============================================================
-- END OF TRANSACTION DATA SCHEMA
-- ============================================================


-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 3: Operational Events
-- ============================================================


-- ============================================================
-- 10. CUSTOMER TICKETS
-- ============================================================

CREATE TABLE customer_tickets (
    ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    customer_id UUID NOT NULL,
    order_id UUID NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ NULL,

    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    status VARCHAR(20) NOT NULL DEFAULT 'Open',

    resolution_time_hours NUMERIC(18,4) NULL,
    satisfaction_score NUMERIC(8,4) NULL,

    CONSTRAINT fk_customer_tickets_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_customer_tickets_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_customer_tickets_category
        CHECK (
            category IN (
                'Delivery',
                'Payment',
                'ProductQuality',
                'Refund',
                'Order',
                'Other'
            )
        ),

    CONSTRAINT chk_customer_tickets_priority
        CHECK (
            priority IN (
                'Low',
                'Medium',
                'High',
                'Critical'
            )
        ),

    CONSTRAINT chk_customer_tickets_status
        CHECK (
            status IN (
                'Open',
                'InProgress',
                'Resolved',
                'Closed'
            )
        ),

    CONSTRAINT chk_customer_tickets_resolved_at
        CHECK (
            resolved_at IS NULL
            OR resolved_at >= created_at
        ),

    CONSTRAINT chk_customer_tickets_resolution_time
        CHECK (
            resolution_time_hours IS NULL
            OR resolution_time_hours >= 0
        ),

    CONSTRAINT chk_customer_tickets_satisfaction
        CHECK (
            satisfaction_score IS NULL
            OR (
                satisfaction_score >= 0
                AND satisfaction_score <= 5
            )
        )
);


-- ============================================================
-- 11. REVIEWS
-- ============================================================

CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    customer_id UUID NOT NULL,
    order_id UUID NOT NULL,
    product_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    rating INTEGER NOT NULL,

    sentiment_score NUMERIC(5,4) NULL,

    review_category VARCHAR(50) NOT NULL,

    CONSTRAINT fk_reviews_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_reviews_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_reviews_customer_order_product
        UNIQUE (
            customer_id,
            order_id,
            product_id
        ),

    CONSTRAINT chk_reviews_rating
        CHECK (
            rating BETWEEN 1 AND 5
        ),

    CONSTRAINT chk_reviews_sentiment
        CHECK (
            sentiment_score IS NULL
            OR (
                sentiment_score >= -1
                AND sentiment_score <= 1
            )
        )
);


-- ============================================================
-- 12. CUSTOMER BEHAVIOR EVENTS
-- ============================================================
--
-- NOTE:
-- campaign_id references marketing_campaigns, which is created
-- in Part 4. The campaign FK is intentionally added later via
-- ALTER TABLE after marketing_campaigns exists.
-- ============================================================

CREATE TABLE customer_behavior_events (
    behavior_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    customer_id UUID NULL,
    session_id UUID NOT NULL,

    product_id UUID NULL,
    campaign_id UUID NULL,

    event_timestamp TIMESTAMPTZ NOT NULL,

    event_type VARCHAR(50) NOT NULL,

    channel VARCHAR(50) NOT NULL,

    event_value NUMERIC(18,4) NULL,

    CONSTRAINT fk_behavior_events_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_behavior_events_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_behavior_events_type
        CHECK (
            event_type IN (
                'PageView',
                'ProductView',
                'AddToCart',
                'Checkout',
                'Purchase',
                'Search'
            )
        ),

    CONSTRAINT chk_behavior_events_value
        CHECK (
            event_value IS NULL
            OR event_value >= 0
        )
);


-- ============================================================
-- 13. INDEXES — OPERATIONAL EVENTS
-- ============================================================

CREATE INDEX idx_customer_tickets_customer_created
ON customer_tickets (
    customer_id,
    created_at
);

CREATE INDEX idx_customer_tickets_order
ON customer_tickets (
    order_id
);

CREATE INDEX idx_customer_tickets_status_created
ON customer_tickets (
    status,
    created_at
);

CREATE INDEX idx_reviews_customer_created
ON reviews (
    customer_id,
    created_at
);

CREATE INDEX idx_reviews_order
ON reviews (
    order_id
);

CREATE INDEX idx_reviews_product_created
ON reviews (
    product_id,
    created_at
);

CREATE INDEX idx_reviews_rating
ON reviews (
    rating
);

CREATE INDEX idx_behavior_events_customer_time
ON customer_behavior_events (
    customer_id,
    event_timestamp
);

CREATE INDEX idx_behavior_events_session_time
ON customer_behavior_events (
    session_id,
    event_timestamp
);

CREATE INDEX idx_behavior_events_product_time
ON customer_behavior_events (
    product_id,
    event_timestamp
);

CREATE INDEX idx_behavior_events_campaign_time
ON customer_behavior_events (
    campaign_id,
    event_timestamp
);

CREATE INDEX idx_behavior_events_type_time
ON customer_behavior_events (
    event_type,
    event_timestamp
);


-- ============================================================
-- END OF PART 3 — OPERATIONAL EVENTS
-- ============================================================


-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 4: Marketing & Finance
-- ============================================================


-- ============================================================
-- 14. MARKETING CAMPAIGNS
-- ============================================================

CREATE TABLE marketing_campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    campaign_name VARCHAR(250) NOT NULL,
    channel VARCHAR(50) NOT NULL,

    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NULL,

    budget_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    currency_code CHAR(3) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Draft',

    CONSTRAINT uq_marketing_campaigns_name
        UNIQUE (campaign_name),

    CONSTRAINT chk_marketing_campaigns_time
        CHECK (
            end_time IS NULL
            OR end_time >= start_time
        ),

    CONSTRAINT chk_marketing_campaigns_budget
        CHECK (
            budget_amount >= 0
        ),

    CONSTRAINT chk_marketing_campaigns_status
        CHECK (
            status IN (
                'Draft',
                'Active',
                'Paused',
                'Completed'
            )
        )
);


-- ============================================================
-- DEFERRED FOREIGN KEY — CUSTOMER BEHAVIOR → MARKETING CAMPAIGN
-- ============================================================
-- customer_behavior_events is defined in Part 3, while
-- marketing_campaigns is defined in Part 4. The FK is therefore
-- added here, after its parent table exists.
-- ============================================================

ALTER TABLE customer_behavior_events
    ADD CONSTRAINT fk_behavior_events_campaign
    FOREIGN KEY (campaign_id)
    REFERENCES marketing_campaigns(campaign_id)
    ON DELETE RESTRICT;


-- ============================================================
-- 15. MARKETING EVENTS
-- ============================================================

CREATE TABLE marketing_events (
    marketing_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    campaign_id UUID NOT NULL,

    event_timestamp TIMESTAMPTZ NOT NULL,

    event_type VARCHAR(50) NOT NULL,

    customer_id UUID NULL,
    order_id UUID NULL,

    metric_value NUMERIC(18,4) NOT NULL DEFAULT 0,
    cost_amount NUMERIC(18,2) NULL,

    CONSTRAINT fk_marketing_events_campaign
        FOREIGN KEY (campaign_id)
        REFERENCES marketing_campaigns(campaign_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_marketing_events_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_marketing_events_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_marketing_events_type
        CHECK (
            event_type IN (
                'Impression',
                'Click',
                'Conversion',
                'Spend',
                'AudienceUpdate'
            )
        ),

    CONSTRAINT chk_marketing_events_metric
        CHECK (
            metric_value >= 0
        ),

    CONSTRAINT chk_marketing_events_cost
        CHECK (
            cost_amount IS NULL
            OR cost_amount >= 0
        )
);


-- ============================================================
-- 16. FINANCIAL TRANSACTIONS
-- ============================================================

CREATE TABLE financial_transactions (
    financial_transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    transaction_timestamp TIMESTAMPTZ NOT NULL,

    transaction_type VARCHAR(50) NOT NULL,

    amount NUMERIC(18,2) NOT NULL,

    currency_code CHAR(3) NOT NULL,

    order_id UUID NULL,
    payment_id UUID NULL,
    purchase_order_id UUID NULL,
    shipment_id UUID NULL,
    campaign_id UUID NULL,

    reference_code VARCHAR(150) NOT NULL,

    CONSTRAINT uq_financial_transactions_reference
        UNIQUE (reference_code),

    CONSTRAINT fk_financial_transactions_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_financial_transactions_payment
        FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_financial_transactions_purchase_order
        FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_orders(purchase_order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_financial_transactions_shipment
        FOREIGN KEY (shipment_id)
        REFERENCES shipments(shipment_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_financial_transactions_campaign
        FOREIGN KEY (campaign_id)
        REFERENCES marketing_campaigns(campaign_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_financial_transactions_type
        CHECK (
            transaction_type IN (
                'Revenue',
                'COGS',
                'ShippingCost',
                'Refund',
                'MarketingSpend',
                'InventoryAdjustment'
            )
        ),

    CONSTRAINT chk_financial_transactions_amount
        CHECK (
            amount <> 0
        ),

    CONSTRAINT chk_financial_transactions_reference
        CHECK (
            order_id IS NOT NULL
            OR payment_id IS NOT NULL
            OR purchase_order_id IS NOT NULL
            OR shipment_id IS NOT NULL
            OR campaign_id IS NOT NULL
            OR reference_code IS NOT NULL
        )
);


-- ============================================================
-- 17. INDEXES — MARKETING & FINANCE
-- ============================================================

CREATE INDEX idx_marketing_campaigns_start_time
ON marketing_campaigns (
    start_time
);

CREATE INDEX idx_marketing_campaigns_status
ON marketing_campaigns (
    status
);

CREATE INDEX idx_marketing_events_campaign_time
ON marketing_events (
    campaign_id,
    event_timestamp
);

CREATE INDEX idx_marketing_events_customer_time
ON marketing_events (
    customer_id,
    event_timestamp
);

CREATE INDEX idx_marketing_events_order
ON marketing_events (
    order_id
);

CREATE INDEX idx_marketing_events_type_time
ON marketing_events (
    event_type,
    event_timestamp
);

CREATE INDEX idx_financial_transactions_timestamp
ON financial_transactions (
    transaction_timestamp
);

CREATE INDEX idx_financial_transactions_type_time
ON financial_transactions (
    transaction_type,
    transaction_timestamp
);

CREATE INDEX idx_financial_transactions_order
ON financial_transactions (
    order_id
);

CREATE INDEX idx_financial_transactions_payment
ON financial_transactions (
    payment_id
);

CREATE INDEX idx_financial_transactions_purchase_order
ON financial_transactions (
    purchase_order_id
);

CREATE INDEX idx_financial_transactions_shipment
ON financial_transactions (
    shipment_id
);

CREATE INDEX idx_financial_transactions_campaign
ON financial_transactions (
    campaign_id
);


-- ============================================================
-- END OF PART 4 — MARKETING & FINANCE
-- ============================================================


-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 5: Incident Metadata
-- ============================================================


-- ============================================================
-- 18. INCIDENTS
-- ============================================================

CREATE TABLE incidents (
    incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    scenario_id VARCHAR(100) NOT NULL,

    detected_at TIMESTAMPTZ NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NULL,

    severity VARCHAR(20) NOT NULL,

    affected_domain VARCHAR(50) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'Open',

    summary VARCHAR(1000) NOT NULL,

    CONSTRAINT chk_incidents_detected_at
        CHECK (
            detected_at >= start_time
        ),

    CONSTRAINT chk_incidents_end_time
        CHECK (
            end_time IS NULL
            OR end_time >= start_time
        ),

    CONSTRAINT chk_incidents_severity
        CHECK (
            severity IN (
                'Low',
                'Medium',
                'High',
                'Critical'
            )
        ),

    CONSTRAINT chk_incidents_domain
        CHECK (
            affected_domain IN (
                'Supply',
                'Inventory',
                'Fulfillment',
                'Delivery',
                'Payment',
                'Customer',
                'Marketing',
                'Finance'
            )
        ),

    CONSTRAINT chk_incidents_status
        CHECK (
            status IN (
                'Open',
                'Investigating',
                'Mitigated',
                'Closed'
            )
        )
);


-- ============================================================
-- 19. INCIDENT ENTITIES
-- ============================================================

CREATE TABLE incident_entities (
    incident_entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    entity_type VARCHAR(50) NOT NULL,

    entity_id UUID NOT NULL,

    observed_at TIMESTAMPTZ NOT NULL,

    impact_type VARCHAR(100) NOT NULL,

    impact_severity NUMERIC(8,4) NOT NULL,

    CONSTRAINT fk_incident_entities_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_incident_entities_type
        CHECK (
            entity_type IN (
                'Customer',
                'Product',
                'Supplier',
                'Warehouse',
                'Order',
                'PurchaseOrder',
                'Shipment',
                'Payment',
                'Campaign'
            )
        ),

    CONSTRAINT chk_incident_entities_severity
        CHECK (
            impact_severity >= 0
            AND impact_severity <= 1
        ),

    CONSTRAINT uq_incident_entities_observation
        UNIQUE (
            incident_id,
            entity_type,
            entity_id,
            observed_at
        )
);


-- ============================================================
-- 20. INDEXES — INCIDENT METADATA
-- ============================================================

CREATE INDEX idx_incidents_start_time
ON incidents (
    start_time
);

CREATE INDEX idx_incidents_detected_at
ON incidents (
    detected_at
);

CREATE INDEX idx_incidents_domain_status
ON incidents (
    affected_domain,
    status
);

CREATE INDEX idx_incidents_severity
ON incidents (
    severity
);

CREATE INDEX idx_incident_entities_incident_time
ON incident_entities (
    incident_id,
    observed_at
);

CREATE INDEX idx_incident_entities_entity
ON incident_entities (
    entity_type,
    entity_id,
    observed_at
);

CREATE INDEX idx_incident_entities_impact
ON incident_entities (
    impact_type,
    observed_at
);


-- ============================================================
-- END OF PART 5 — INCIDENT METADATA
-- ============================================================



-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 6: Causal Ground Truth — RESTRICTED
--
-- IMPORTANT:
-- These tables contain causal truth and evaluation evidence.
-- AI Analyst MUST NOT have access to these tables.
--
-- Intended users:
--   - Simulator
--   - Curator
--   - Evaluator
--   - Benchmark Engine
-- ============================================================


-- ============================================================
-- 6.1 CAUSAL NODES
-- ============================================================
--
-- Represents nodes in the ground-truth causal graph.
--
-- Typical causal chain:
--
-- RootCause
--     ↓
-- Mechanism
--     ↓
-- OperationalImpact
--     ↓
-- BusinessImpact
--     ↓
-- Outcome
--
-- This table is RESTRICTED.
-- ============================================================

CREATE TABLE causal_nodes (
    node_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    node_type VARCHAR(50) NOT NULL,

    domain VARCHAR(50) NOT NULL,

    entity_type VARCHAR(50),
    entity_id UUID,

    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,

    truth_label VARCHAR(250) NOT NULL,

    truth_description TEXT NOT NULL,

    CONSTRAINT fk_causal_nodes_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_causal_nodes_type
        CHECK (
            node_type IN (
                'RootCause',
                'Mechanism',
                'OperationalImpact',
                'BusinessImpact',
                'Outcome'
            )
        ),

    CONSTRAINT chk_causal_nodes_domain
        CHECK (
            domain IN (
                'Supply',
                'Inventory',
                'Fulfillment',
                'Delivery',
                'Payment',
                'Customer',
                'Marketing',
                'Finance'
            )
        ),

    CONSTRAINT chk_causal_nodes_valid_time
        CHECK (
            valid_to IS NULL
            OR valid_to >= valid_from
        ),

    CONSTRAINT chk_causal_nodes_entity_pair
        CHECK (
            (
                entity_type IS NULL
                AND entity_id IS NULL
            )
            OR
            (
                entity_type IS NOT NULL
                AND entity_id IS NOT NULL
            )
        )
);


-- ============================================================
-- 6.2 CAUSAL LINKS
-- ============================================================
--
-- Directed edges between causal nodes.
--
-- Example:
--
-- Supplier disruption
--        ↓
-- Delayed purchase order
--        ↓
-- Inventory shortage
--        ↓
-- Order delay
--        ↓
-- Revenue loss
--
-- relationship_type = Causes
-- represents the primary causal graph.
--
-- Other relationships:
--   Amplifies
--   Mitigates
--   CorrelatesWith
--
-- This table is RESTRICTED.
-- ============================================================

CREATE TABLE causal_links (
    causal_link_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    cause_node_id UUID NOT NULL,

    effect_node_id UUID NOT NULL,

    relationship_type VARCHAR(50) NOT NULL,

    lag_minutes NUMERIC(12,2) NOT NULL DEFAULT 0,

    confidence NUMERIC(8,4) NOT NULL,

    CONSTRAINT fk_causal_links_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_causal_links_cause_node
        FOREIGN KEY (cause_node_id)
        REFERENCES causal_nodes(node_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_causal_links_effect_node
        FOREIGN KEY (effect_node_id)
        REFERENCES causal_nodes(node_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_causal_links_relationship
        CHECK (
            relationship_type IN (
                'Causes',
                'Amplifies',
                'Mitigates',
                'CorrelatesWith'
            )
        ),

    CONSTRAINT chk_causal_links_lag
        CHECK (
            lag_minutes >= 0
        ),

    CONSTRAINT chk_causal_links_confidence
        CHECK (
            confidence >= 0
            AND confidence <= 1
        ),

    CONSTRAINT chk_causal_links_not_self
        CHECK (
            cause_node_id <> effect_node_id
        ),

    CONSTRAINT uq_causal_links
        UNIQUE (
            incident_id,
            cause_node_id,
            effect_node_id,
            relationship_type
        )
);


-- ============================================================
-- 6.3 INCIDENT CAUSES
-- ============================================================
--
-- Stores confirmed root causes for an incident.
--
-- cause_rank = 1
-- represents the primary root cause.
--
-- Multiple causes are allowed:
--
-- Primary:
--   Supplier disruption
--
-- Secondary:
--   Payment provider degradation
--
-- This table is RESTRICTED.
-- ============================================================

CREATE TABLE incident_causes (
    incident_cause_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    node_id UUID NOT NULL,

    cause_rank INTEGER NOT NULL,

    is_primary BOOLEAN NOT NULL DEFAULT FALSE,

    confirmed_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_incident_causes_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_incident_causes_node
        FOREIGN KEY (node_id)
        REFERENCES causal_nodes(node_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_incident_causes_rank
        CHECK (
            cause_rank >= 1
        ),

    CONSTRAINT uq_incident_causes_rank
        UNIQUE (
            incident_id,
            cause_rank
        )
);


-- ============================================================
-- 6.4 INCIDENT EVIDENCE
-- ============================================================
--
-- Stores curator-confirmed evidence supporting causal truth.
--
-- Evidence may originate from operational records such as:
--
--   - orders
--   - payments
--   - purchase_orders
--   - inventory_movements
--   - shipments
--   - tickets
--   - financial_transactions
--
-- IMPORTANT:
-- evidence_summary and is_decisive are RESTRICTED.
--
-- AI Analyst MUST NOT receive this table.
-- ============================================================

CREATE TABLE incident_evidence (
    incident_evidence_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    node_id UUID NOT NULL,

    evidence_type VARCHAR(50) NOT NULL,

    source_table VARCHAR(100),

    source_record_id UUID,

    evidence_timestamp TIMESTAMPTZ NOT NULL,

    evidence_summary TEXT NOT NULL,

    is_decisive BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_incident_evidence_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_incident_evidence_node
        FOREIGN KEY (node_id)
        REFERENCES causal_nodes(node_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_incident_evidence_type
        CHECK (
            evidence_type IN (
                'Log',
                'Metric',
                'Record',
                'ExpertAssessment'
            )
        ),

    CONSTRAINT chk_incident_evidence_source_pair
        CHECK (
            (
                source_table IS NULL
                AND source_record_id IS NULL
            )
            OR
            (
                source_table IS NOT NULL
                AND source_record_id IS NOT NULL
            )
        )
);


-- ============================================================
-- 6.5 INCIDENT OUTCOMES
-- ============================================================
--
-- Stores confirmed business consequences of an incident.
--
-- Examples:
--
--   RevenueLoss
--   SLADegradation
--   ChurnRisk
--   Stockout
--   Delay
--   RefundIncrease
--
-- This is ground truth.
--
-- AI Analyst MUST NOT access this table.
-- ============================================================

CREATE TABLE incident_outcomes (
    incident_outcome_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    node_id UUID NOT NULL,

    outcome_type VARCHAR(100) NOT NULL,

    measured_at TIMESTAMPTZ NOT NULL,

    metric_name VARCHAR(100) NOT NULL,

    metric_value NUMERIC(18,4) NOT NULL,

    financial_impact NUMERIC(18,2),

    currency_code CHAR(3),

    CONSTRAINT fk_incident_outcomes_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_incident_outcomes_node
        FOREIGN KEY (node_id)
        REFERENCES causal_nodes(node_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_incident_outcomes_type
        CHECK (
            outcome_type IN (
                'RevenueLoss',
                'SLADegradation',
                'ChurnRisk',
                'Stockout',
                'Delay',
                'RefundIncrease'
            )
        ),

    CONSTRAINT chk_incident_outcomes_financial_impact
        CHECK (
            financial_impact IS NULL
            OR financial_impact >= 0
        ),

    CONSTRAINT chk_incident_outcomes_currency
        CHECK (
            (
                financial_impact IS NULL
                AND currency_code IS NULL
            )
            OR
            (
                financial_impact IS NOT NULL
                AND currency_code IS NOT NULL
            )
        )
);


-- ============================================================
-- 6.6 INDEXES — CAUSAL GROUND TRUTH
-- ============================================================

CREATE INDEX idx_causal_nodes_incident
ON causal_nodes(incident_id);

CREATE INDEX idx_causal_nodes_incident_type
ON causal_nodes(
    incident_id,
    node_type
);

CREATE INDEX idx_causal_nodes_entity
ON causal_nodes(
    entity_type,
    entity_id
);

CREATE INDEX idx_causal_links_incident
ON causal_links(incident_id);

CREATE INDEX idx_causal_links_cause
ON causal_links(cause_node_id);

CREATE INDEX idx_causal_links_effect
ON causal_links(effect_node_id);

CREATE INDEX idx_incident_causes_incident
ON incident_causes(incident_id);

CREATE INDEX idx_incident_causes_node
ON incident_causes(node_id);

CREATE INDEX idx_incident_evidence_incident
ON incident_evidence(incident_id);

CREATE INDEX idx_incident_evidence_node
ON incident_evidence(node_id);

CREATE INDEX idx_incident_evidence_timestamp
ON incident_evidence(
    incident_id,
    evidence_timestamp
);

CREATE INDEX idx_incident_outcomes_incident
ON incident_outcomes(incident_id);

CREATE INDEX idx_incident_outcomes_node
ON incident_outcomes(node_id);

CREATE INDEX idx_incident_outcomes_measured_at
ON incident_outcomes(
    incident_id,
    measured_at
);


-- ============================================================
-- 6.7 RESTRICTED SCHEMA MARKER
-- ============================================================
--
-- These tables belong to the Ground Truth boundary.
--
-- DO NOT expose them through:
--   - AI Analyst views
--   - AI retrieval APIs
--   - embeddings
--   - prompts
--   - benchmark observations
--   - dashboards used by AI
--
-- Access control should be implemented separately using
-- PostgreSQL roles / schemas / service accounts.
-- ============================================================

COMMENT ON TABLE causal_nodes IS
'RESTRICTED: Causal ground truth nodes. AI Analyst access prohibited.';

COMMENT ON TABLE causal_links IS
'RESTRICTED: Causal ground truth links. AI Analyst access prohibited.';

COMMENT ON TABLE incident_causes IS
'RESTRICTED: Confirmed incident root causes. AI Analyst access prohibited.';

COMMENT ON TABLE incident_evidence IS
'RESTRICTED: Curator-confirmed decisive evidence. AI Analyst access prohibited.';

COMMENT ON TABLE incident_outcomes IS
'RESTRICTED: Confirmed incident outcomes. AI Analyst access prohibited.';


-- ============================================================
-- END OF PART 6
-- ============================================================


-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 7: Benchmark & Evaluation — RESTRICTED
--
-- IMPORTANT:
-- These tables define benchmark cases, observations and
-- evaluation targets.
--
-- AI Analyst:
--   - MAY receive allowlisted observations
--   - MUST NOT access benchmark targets
--
-- Intended users:
--   - Evaluator
--   - Curator
--   - Benchmark Engine
-- ============================================================


-- ============================================================
-- 7.1 BENCHMARK CASES
-- ============================================================
--
-- Defines an evaluation case around an incident.
--
-- The observation window determines what information is
-- available to the AI Analyst.
--
-- Example:
--
-- observation_start_time
--          ↓
--          ↓   AI-visible period
--          ↓
-- observation_cutoff_time
--          ↓
--      AI prediction
--
-- Ground truth is evaluated separately.
-- ============================================================

CREATE TABLE benchmark_cases (
    benchmark_case_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    incident_id UUID NOT NULL,

    case_name VARCHAR(250) NOT NULL,

    split VARCHAR(20) NOT NULL,

    observation_start_time TIMESTAMPTZ NOT NULL,

    observation_cutoff_time TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20) NOT NULL DEFAULT 'Draft',

    CONSTRAINT fk_benchmark_cases_incident
        FOREIGN KEY (incident_id)
        REFERENCES incidents(incident_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_benchmark_cases_name
        UNIQUE (case_name),

    CONSTRAINT chk_benchmark_cases_split
        CHECK (
            split IN (
                'Train',
                'Validation',
                'Test'
            )
        ),

    CONSTRAINT chk_benchmark_cases_time_window
        CHECK (
            observation_start_time
            <= observation_cutoff_time
        ),

    CONSTRAINT chk_benchmark_cases_status
        CHECK (
            status IN (
                'Draft',
                'Active',
                'Retired'
            )
        )
);


-- ============================================================
-- 7.2 BENCHMARK OBSERVATIONS
-- ============================================================
--
-- Registry of operational records made available to a
-- benchmark case.
--
-- This table DOES NOT duplicate operational data.
--
-- It stores references to records that the AI Analyst is
-- allowed to observe.
--
-- Example:
--
-- benchmark_case
--      ↓
--      ├── order record
--      ├── payment record
--      ├── shipment record
--      ├── inventory movement
--      └── customer ticket
--
-- Only records inside the observation window and before
-- cutoff are allowed.
-- ============================================================

CREATE TABLE benchmark_observations (
    benchmark_observation_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    benchmark_case_id UUID NOT NULL,

    source_table VARCHAR(100) NOT NULL,

    source_record_id UUID NOT NULL,

    observed_at TIMESTAMPTZ NOT NULL,

    observation_role VARCHAR(30) NOT NULL,

    CONSTRAINT fk_benchmark_observations_case
        FOREIGN KEY (benchmark_case_id)
        REFERENCES benchmark_cases(benchmark_case_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_benchmark_observations_role
        CHECK (
            observation_role IN (
                'Signal',
                'Context',
                'Correlation'
            )
        ),

    CONSTRAINT uq_benchmark_observations_record
        UNIQUE (
            benchmark_case_id,
            source_table,
            source_record_id
        )
);


-- ============================================================
-- 7.3 EVALUATION TARGETS
-- ============================================================
--
-- Stores the expected answer / rubric for an AI Analyst.
--
-- IMPORTANT:
--
-- This is RESTRICTED GROUND TRUTH.
--
-- It MUST NOT be:
--   - inserted into AI prompts
--   - exposed through AI views
--   - embedded
--   - retrieved
--   - returned by AI APIs
--   - placed into benchmark observations
--
-- Target types:
--
--   RootCause
--   CausalPath
--   AffectedEntity
--   RecommendedAction
--   Outcome
-- ============================================================

CREATE TABLE evaluation_targets (
    evaluation_target_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    benchmark_case_id UUID NOT NULL,

    target_type VARCHAR(50) NOT NULL,

    target_value JSONB NOT NULL,

    causal_node_id UUID,

    scoring_weight NUMERIC(8,4) NOT NULL DEFAULT 1,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_evaluation_targets_case
        FOREIGN KEY (benchmark_case_id)
        REFERENCES benchmark_cases(benchmark_case_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_evaluation_targets_node
        FOREIGN KEY (causal_node_id)
        REFERENCES causal_nodes(node_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_evaluation_targets_type
        CHECK (
            target_type IN (
                'RootCause',
                'CausalPath',
                'AffectedEntity',
                'RecommendedAction',
                'Outcome'
            )
        ),

    CONSTRAINT chk_evaluation_targets_weight
        CHECK (
            scoring_weight >= 0
        )
);


-- ============================================================
-- 7.4 INDEXES — BENCHMARK
-- ============================================================

CREATE INDEX idx_benchmark_cases_incident
ON benchmark_cases(incident_id);

CREATE INDEX idx_benchmark_cases_split
ON benchmark_cases(split);

CREATE INDEX idx_benchmark_cases_status
ON benchmark_cases(status);

CREATE INDEX idx_benchmark_observations_case
ON benchmark_observations(
    benchmark_case_id
);

CREATE INDEX idx_benchmark_observations_time
ON benchmark_observations(
    benchmark_case_id,
    observed_at
);

CREATE INDEX idx_benchmark_observations_source
ON benchmark_observations(
    source_table,
    source_record_id
);

CREATE INDEX idx_evaluation_targets_case
ON evaluation_targets(
    benchmark_case_id
);

CREATE INDEX idx_evaluation_targets_node
ON evaluation_targets(
    causal_node_id
);

CREATE INDEX idx_evaluation_targets_type
ON evaluation_targets(
    benchmark_case_id,
    target_type
);


-- ============================================================
-- 7.5 RESTRICTED COMMENTS
-- ============================================================

COMMENT ON TABLE benchmark_cases IS
'RESTRICTED: Benchmark case definitions and observation cutoffs.';

COMMENT ON TABLE benchmark_observations IS
'RESTRICTED: Allowlisted operational records for benchmark cases.';

COMMENT ON TABLE evaluation_targets IS
'RESTRICTED: Ground truth targets and evaluation rubrics. AI access prohibited.';


-- ============================================================
-- END OF PART 7
-- ============================================================


-- ============================================================
-- Enterprise Digital Twin
-- Database Schema V1
-- Part 8: Integrity & Access Control
--
-- Purpose:
--   1. Cross-table integrity validation
--   2. Polymorphic reference validation
--   3. Causal graph validation
--   4. Benchmark leakage validation
--   5. AI Analyst access boundary
--   6. Restricted Ground Truth boundary
--   7. Audit support
--
-- IMPORTANT:
-- This section assumes Parts 1-7 already exist.
-- ============================================================


-- ============================================================
-- 8.1 ENTITY REGISTRY
-- ============================================================
--
-- Polymorphic references such as:
--
--   entity_type + entity_id
--
-- cannot be enforced by a normal PostgreSQL FK.
--
-- This registry provides a controlled catalog of valid
-- entity types used by the Digital Twin.
-- ============================================================

CREATE TABLE entity_registry (
    entity_type VARCHAR(50) PRIMARY KEY,

    description VARCHAR(250) NOT NULL,

    is_operational BOOLEAN NOT NULL DEFAULT TRUE,

    is_ai_visible BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 8.1.1 ENTITY REGISTRY — CONTROLLED VOCABULARY
-- ============================================================

INSERT INTO entity_registry (
    entity_type,
    description,
    is_operational,
    is_ai_visible
)
VALUES
    ('Customer', 'Customer entity', TRUE, TRUE),
    ('Product', 'Product entity', TRUE, TRUE),
    ('Category', 'Product category entity', TRUE, TRUE),
    ('Supplier', 'Supplier entity', TRUE, TRUE),
    ('Warehouse', 'Warehouse entity', TRUE, TRUE),
    ('Carrier', 'Carrier entity', TRUE, TRUE),
    ('PaymentMethod', 'Payment method entity', TRUE, TRUE),
    ('Order', 'Sales order entity', TRUE, TRUE),
    ('OrderItem', 'Sales order item entity', TRUE, TRUE),
    ('Payment', 'Payment entity', TRUE, TRUE),
    ('PurchaseOrder', 'Purchase order entity', TRUE, TRUE),
    ('PurchaseOrderItem', 'Purchase order item entity', TRUE, TRUE),
    ('Shipment', 'Shipment entity', TRUE, TRUE),
    ('Campaign', 'Marketing campaign entity', TRUE, TRUE),
    ('InventorySnapshot', 'Inventory snapshot entity', TRUE, TRUE),
    ('InventoryMovement', 'Inventory movement entity', TRUE, TRUE),
    ('CustomerTicket', 'Customer support ticket', TRUE, TRUE),
    ('Review', 'Customer review entity', TRUE, TRUE),
    ('CustomerBehaviorEvent', 'Customer behavior event', TRUE, TRUE),
    ('MarketingEvent', 'Marketing event', TRUE, TRUE),
    ('FinancialTransaction', 'Financial transaction entity', TRUE, TRUE),
    ('Incident', 'Operational incident metadata', TRUE, TRUE)
ON CONFLICT (entity_type) DO NOTHING;


-- ============================================================
-- 8.2 ENTITY VALIDATION FUNCTION
-- ============================================================
--
-- Validates:
--
--   entity_type
--   entity_id
--
-- against the actual operational tables.
--
-- This is required because PostgreSQL does not support a
-- polymorphic FK directly.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_entity_reference(
    p_entity_type VARCHAR,
    p_entity_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN

    IF p_entity_type IS NULL
       OR p_entity_id IS NULL THEN
        RETURN FALSE;
    END IF;


    IF NOT EXISTS (
        SELECT 1
        FROM entity_registry
        WHERE entity_type = p_entity_type
    ) THEN
        RETURN FALSE;
    END IF;


    CASE p_entity_type

        WHEN 'Customer' THEN
            RETURN EXISTS (
                SELECT 1
                FROM customers
                WHERE customer_id = p_entity_id
            );

        WHEN 'Product' THEN
            RETURN EXISTS (
                SELECT 1
                FROM products
                WHERE product_id = p_entity_id
            );

        WHEN 'Category' THEN
            RETURN EXISTS (
                SELECT 1
                FROM categories
                WHERE category_id = p_entity_id
            );

        WHEN 'Supplier' THEN
            RETURN EXISTS (
                SELECT 1
                FROM suppliers
                WHERE supplier_id = p_entity_id
            );

        WHEN 'Warehouse' THEN
            RETURN EXISTS (
                SELECT 1
                FROM warehouses
                WHERE warehouse_id = p_entity_id
            );

        WHEN 'Carrier' THEN
            RETURN EXISTS (
                SELECT 1
                FROM carriers
                WHERE carrier_id = p_entity_id
            );

        WHEN 'PaymentMethod' THEN
            RETURN EXISTS (
                SELECT 1
                FROM payment_methods
                WHERE payment_method_id = p_entity_id
            );

        WHEN 'Order' THEN
            RETURN EXISTS (
                SELECT 1
                FROM orders
                WHERE order_id = p_entity_id
            );

        WHEN 'OrderItem' THEN
            RETURN EXISTS (
                SELECT 1
                FROM order_items
                WHERE order_item_id = p_entity_id
            );

        WHEN 'Payment' THEN
            RETURN EXISTS (
                SELECT 1
                FROM payments
                WHERE payment_id = p_entity_id
            );

        WHEN 'PurchaseOrder' THEN
            RETURN EXISTS (
                SELECT 1
                FROM purchase_orders
                WHERE purchase_order_id = p_entity_id
            );

        WHEN 'PurchaseOrderItem' THEN
            RETURN EXISTS (
                SELECT 1
                FROM purchase_order_items
                WHERE purchase_order_item_id = p_entity_id
            );

        WHEN 'Shipment' THEN
            RETURN EXISTS (
                SELECT 1
                FROM shipments
                WHERE shipment_id = p_entity_id
            );

        WHEN 'Campaign' THEN
            RETURN EXISTS (
                SELECT 1
                FROM marketing_campaigns
                WHERE campaign_id = p_entity_id
            );

        WHEN 'InventorySnapshot' THEN
            RETURN EXISTS (
                SELECT 1
                FROM inventory_snapshots
                WHERE inventory_snapshot_id = p_entity_id
            );

        WHEN 'InventoryMovement' THEN
            RETURN EXISTS (
                SELECT 1
                FROM inventory_movements
                WHERE inventory_movement_id = p_entity_id
            );

        WHEN 'CustomerTicket' THEN
            RETURN EXISTS (
                SELECT 1
                FROM customer_tickets
                WHERE ticket_id = p_entity_id
            );

        WHEN 'Review' THEN
            RETURN EXISTS (
                SELECT 1
                FROM reviews
                WHERE review_id = p_entity_id
            );

        WHEN 'CustomerBehaviorEvent' THEN
            RETURN EXISTS (
                SELECT 1
                FROM customer_behavior_events
                WHERE behavior_event_id = p_entity_id
            );

        WHEN 'MarketingEvent' THEN
            RETURN EXISTS (
                SELECT 1
                FROM marketing_events
                WHERE marketing_event_id = p_entity_id
            );

        WHEN 'FinancialTransaction' THEN
            RETURN EXISTS (
                SELECT 1
                FROM financial_transactions
                WHERE financial_transaction_id = p_entity_id
            );

        WHEN 'Incident' THEN
            RETURN EXISTS (
                SELECT 1
                FROM incidents
                WHERE incident_id = p_entity_id
            );

        ELSE
            RETURN FALSE;

    END CASE;

END;
$$;


-- ============================================================
-- 8.3 CROSS-ENTITY VALIDATION
-- ============================================================
--
-- Validates polymorphic entity references in incident_entities.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_incident_entities()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM incident_entities ie
    WHERE NOT validate_entity_reference(
        ie.entity_type,
        ie.entity_id
    );

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.4 CAUSAL NODE / INCIDENT CONSISTENCY
-- ============================================================
--
-- All causal nodes belonging to an incident must reference
-- the same incident.
--
-- This validation catches incorrect cross-incident links.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_causal_links()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM causal_links cl
    JOIN causal_nodes cn_cause
        ON cn_cause.node_id = cl.cause_node_id
    JOIN causal_nodes cn_effect
        ON cn_effect.node_id = cl.effect_node_id
    WHERE
        cl.incident_id <> cn_cause.incident_id
        OR cl.incident_id <> cn_effect.incident_id;

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.5 INCIDENT CAUSE VALIDATION
-- ============================================================
--
-- incident_causes must reference RootCause nodes belonging
-- to the same incident.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_incident_causes()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM incident_causes ic
    JOIN causal_nodes cn
        ON cn.node_id = ic.node_id
    WHERE
        ic.incident_id <> cn.incident_id
        OR cn.node_type <> 'RootCause';

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.6 INCIDENT OUTCOME VALIDATION
-- ============================================================
--
-- incident_outcomes must reference Outcome nodes belonging
-- to the same incident.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_incident_outcomes()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM incident_outcomes io
    JOIN causal_nodes cn
        ON cn.node_id = io.node_id
    WHERE
        io.incident_id <> cn.incident_id
        OR cn.node_type <> 'Outcome';

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.7 INCIDENT EVIDENCE VALIDATION
-- ============================================================
--
-- Evidence must point to a node belonging to the same
-- incident.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_incident_evidence()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM incident_evidence ie
    JOIN causal_nodes cn
        ON cn.node_id = ie.node_id
    WHERE
        ie.incident_id <> cn.incident_id;

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.8 CAUSAL GRAPH DAG VALIDATION
-- ============================================================
--
-- Only relationship_type = 'Causes' participates in the
-- causal DAG.
--
-- The graph must not contain:
--
--   A → B → C → A
--
-- This function returns the number of causal cycles detected.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_causal_dag()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    cycle_count INTEGER;
BEGIN

    WITH RECURSIVE graph AS (

        SELECT
            cl.cause_node_id AS root_node,
            cl.effect_node_id AS current_node,
            ARRAY[
                cl.cause_node_id,
                cl.effect_node_id
            ] AS path,
            FALSE AS cycle_found

        FROM causal_links cl
        WHERE cl.relationship_type = 'Causes'


        UNION ALL


        SELECT
            g.root_node,
            cl.effect_node_id,
            g.path || cl.effect_node_id,
            cl.effect_node_id = ANY(g.path)

        FROM graph g

        JOIN causal_links cl
            ON cl.cause_node_id = g.current_node

        WHERE
            cl.relationship_type = 'Causes'
            AND NOT g.cycle_found
    )

    SELECT COUNT(*)
    INTO cycle_count
    FROM graph
    WHERE cycle_found = TRUE;

    RETURN cycle_count;

END;
$$;


-- ============================================================
-- 8.9 BENCHMARK OBSERVATION VALIDATION
-- ============================================================
--
-- Benchmark observations must:
--
--   1. Reference an existing operational record.
--   2. Be inside the observation window.
--   3. Not occur after cutoff.
--
-- Restricted Ground Truth must never appear as source_table.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_benchmark_observations()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM benchmark_observations bo
    JOIN benchmark_cases bc
        ON bc.benchmark_case_id = bo.benchmark_case_id
    WHERE
        bo.observed_at < bc.observation_start_time
        OR bo.observed_at > bc.observation_cutoff_time
        OR bo.source_table IN (
            'causal_nodes',
            'causal_links',
            'incident_causes',
            'incident_evidence',
            'incident_outcomes',
            'evaluation_targets',
            'benchmark_cases'
        );

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.10 BENCHMARK CASE CONSISTENCY
-- ============================================================
--
-- The benchmark case must reference an existing incident.
-- The incident must exist before benchmark creation.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_benchmark_cases()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM benchmark_cases bc
    LEFT JOIN incidents i
        ON i.incident_id = bc.incident_id
    WHERE i.incident_id IS NULL;

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.11 EVALUATION TARGET CONSISTENCY
-- ============================================================
--
-- causal_node_id, when present, must:
--
--   - belong to the same incident as the benchmark case;
--   - exist in causal_nodes.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_evaluation_targets()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count INTEGER;
BEGIN

    SELECT COUNT(*)
    INTO invalid_count
    FROM evaluation_targets et
    JOIN benchmark_cases bc
        ON bc.benchmark_case_id = et.benchmark_case_id
    LEFT JOIN causal_nodes cn
        ON cn.node_id = et.causal_node_id
    WHERE
        et.causal_node_id IS NOT NULL
        AND (
            cn.node_id IS NULL
            OR cn.incident_id <> bc.incident_id
        );

    RETURN invalid_count;

END;
$$;


-- ============================================================
-- 8.12 MASTER VALIDATION FUNCTION
-- ============================================================
--
-- Runs the major integrity checks.
--
-- A production data pipeline should reject a dataset when
-- any returned value is greater than zero.
-- ============================================================

CREATE OR REPLACE FUNCTION validate_enterprise_digital_twin()
RETURNS TABLE (
    check_name VARCHAR,
    invalid_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN

    RETURN QUERY
    SELECT
        'incident_entities'::VARCHAR,
        validate_incident_entities();

    RETURN QUERY
    SELECT
        'causal_links'::VARCHAR,
        validate_causal_links();

    RETURN QUERY
    SELECT
        'incident_causes'::VARCHAR,
        validate_incident_causes();

    RETURN QUERY
    SELECT
        'incident_evidence'::VARCHAR,
        validate_incident_evidence();

    RETURN QUERY
    SELECT
        'incident_outcomes'::VARCHAR,
        validate_incident_outcomes();

    RETURN QUERY
    SELECT
        'causal_dag'::VARCHAR,
        validate_causal_dag();

    RETURN QUERY
    SELECT
        'benchmark_cases'::VARCHAR,
        validate_benchmark_cases();

    RETURN QUERY
    SELECT
        'benchmark_observations'::VARCHAR,
        validate_benchmark_observations();

    RETURN QUERY
    SELECT
        'evaluation_targets'::VARCHAR,
        validate_evaluation_targets();

END;
$$;


-- ============================================================
-- 8.13 ACCESS CONTROL ROLES
-- ============================================================
--
-- Roles:
--
--   edt_ai_analyst
--   edt_simulator
--   edt_evaluator
--   edt_curator
--
-- IMPORTANT:
-- Role creation may require PostgreSQL administrative
-- privileges.
--
-- The following section is intended for controlled
-- deployment environments.
-- ============================================================

DO $$
BEGIN

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'edt_ai_analyst'
    ) THEN
        CREATE ROLE edt_ai_analyst NOLOGIN;
    END IF;


    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'edt_simulator'
    ) THEN
        CREATE ROLE edt_simulator NOLOGIN;
    END IF;


    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'edt_evaluator'
    ) THEN
        CREATE ROLE edt_evaluator NOLOGIN;
    END IF;


    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'edt_curator'
    ) THEN
        CREATE ROLE edt_curator NOLOGIN;
    END IF;

END
$$;


-- ============================================================
-- 8.14 AI ANALYST — DEFAULT DENY
-- ============================================================
--
-- AI Analyst receives no direct table access by default.
--
-- This is intentional.
--
-- Access should later be granted only to approved
-- read-only views/API objects.
-- ============================================================

REVOKE ALL ON ALL TABLES
IN SCHEMA public
FROM edt_ai_analyst;

REVOKE ALL ON ALL SEQUENCES
IN SCHEMA public
FROM edt_ai_analyst;

REVOKE ALL ON ALL FUNCTIONS
IN SCHEMA public
FROM edt_ai_analyst;


-- ============================================================
-- 8.15 EXPLICIT AI DENY — GROUND TRUTH
-- ============================================================
--
-- Explicitly document the restricted boundary.
-- ============================================================

REVOKE ALL ON
    incidents,
    causal_nodes,
    causal_links,
    incident_causes,
    incident_evidence,
    incident_outcomes,
    benchmark_cases,
    evaluation_targets
FROM edt_ai_analyst;


-- ============================================================
-- 8.16 AI ANALYST — ALLOWED OPERATIONAL TABLES
-- ============================================================
--
-- Direct table access is allowed for operational data.
-- Direct access to 'incidents' is revoked to prevent data leakage (scenario_id).
-- Instead, AI Analyst accesses the safe projection view 'ai_incident_observations'.
-- ============================================================

GRANT SELECT ON
    customers,
    categories,
    products,
    suppliers,
    supplier_products,
    warehouses,
    carriers,
    payment_methods,
    orders,
    order_items,
    order_status_history,
    payments,
    payment_status_history,
    inventory_snapshots,
    inventory_movements,
    purchase_orders,
    purchase_order_items,
    shipments,
    shipment_status_history,
    customer_tickets,
    reviews,
    customer_behavior_events,
    marketing_campaigns,
    marketing_events,
    financial_transactions,
    incident_entities
TO edt_ai_analyst;


-- ============================================================
-- 8.16.1 AI INCIDENT OBSERVATIONS (SAFE VIEW)
-- ============================================================
--
-- Exposes safe surface symptoms of incidents to AI Analyst.
-- Explicitly hides scenario_id to prevent Ground Truth / benchmark leakage.
-- ============================================================

CREATE OR REPLACE VIEW ai_incident_observations AS
SELECT
    incident_id,
    detected_at,
    start_time,
    end_time,
    severity,
    affected_domain,
    status,
    summary AS surface_symptoms
FROM incidents;

GRANT SELECT ON ai_incident_observations TO edt_ai_analyst;


-- ============================================================
-- 8.17 AI ANALYST — NO WRITE ACCESS
-- ============================================================

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
ON ALL TABLES
IN SCHEMA public
FROM edt_ai_analyst;


-- ============================================================
-- 8.18 SIMULATOR ACCESS
-- ============================================================
--
-- Simulator requires broad write access because it generates
-- operational data and ground truth.
--
-- Production deployments should narrow this further by
-- separating generator and curator service accounts.
-- ============================================================

GRANT SELECT, INSERT, UPDATE
ON ALL TABLES
IN SCHEMA public
TO edt_simulator;


-- ============================================================
-- 8.19 EVALUATOR ACCESS
-- ============================================================
--
-- Evaluator can read:
--
--   - Ground Truth
--   - Benchmark
--   - AI outputs
--
-- AI outputs are intentionally not represented as a core
-- operational table in V1 and will be added in a later
-- evaluation/output schema.
-- ============================================================

GRANT SELECT
ON
    causal_nodes,
    causal_links,
    incident_causes,
    incident_evidence,
    incident_outcomes,
    benchmark_cases,
    benchmark_observations,
    evaluation_targets
TO edt_evaluator;


-- ============================================================
-- 8.20 CURATOR ACCESS
-- ============================================================
--
-- Curator is allowed to manage Ground Truth and benchmark
-- definitions.
-- ============================================================

GRANT SELECT, INSERT, UPDATE
ON
    causal_nodes,
    causal_links,
    incident_causes,
    incident_evidence,
    incident_outcomes,
    benchmark_cases,
    benchmark_observations,
    evaluation_targets
TO edt_curator;


-- ============================================================
-- 8.21 AUDIT LOG
-- ============================================================
--
-- Stores security/audit events.
--
-- This table does NOT store the content of sensitive queries.
-- It records metadata required for traceability.
-- ============================================================

CREATE TABLE audit_log (
    audit_log_id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    event_timestamp TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    actor_role VARCHAR(100) NOT NULL,

    action_type VARCHAR(50) NOT NULL,

    object_type VARCHAR(100),

    object_id UUID,

    success BOOLEAN NOT NULL,

    metadata JSONB
);


-- ============================================================
-- 8.22 AUDIT LOG INDEXES
-- ============================================================

CREATE INDEX idx_audit_log_timestamp
ON audit_log(event_timestamp);

CREATE INDEX idx_audit_log_actor
ON audit_log(actor_role);

CREATE INDEX idx_audit_log_object
ON audit_log(
    object_type,
    object_id
);


-- ============================================================
-- 8.23 SECURITY DOCUMENTATION
-- ============================================================

COMMENT ON TABLE entity_registry IS
'Controlled registry for polymorphic entity references.';

COMMENT ON TABLE audit_log IS
'Security and data-access audit metadata.';

COMMENT ON FUNCTION validate_entity_reference(VARCHAR, UUID) IS
'Validates polymorphic entity_type/entity_id references.';

COMMENT ON FUNCTION validate_causal_dag() IS
'Validates that Causes relationships do not contain cycles.';

COMMENT ON FUNCTION validate_enterprise_digital_twin() IS
'Runs Enterprise Digital Twin integrity validation suite.';


-- ============================================================
-- 8.24 FINAL ARCHITECTURAL BOUNDARY
-- ============================================================
--
-- AI Analyst:
--
--   ALLOWED
--   ├── Master Data
--   ├── Transaction Data
--   ├── Operational Events
--   ├── Marketing
--   ├── Finance
--   ├── ai_incident_observations (Safe Projection View)
--   ├── incident_entities (Impacted scope)
--   └── Allowlisted benchmark observations
--
--   FORBIDDEN
--   ├── incidents (direct table access — contains scenario_id)
--   ├── causal_nodes
--   ├── causal_links
--   ├── incident_causes
--   ├── incident_evidence
--   ├── incident_outcomes
--   ├── benchmark_cases
--   └── evaluation_targets
--
-- ============================================================


-- ============================================================
-- END OF PART 8
-- ============================================================
