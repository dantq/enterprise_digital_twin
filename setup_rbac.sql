-- ============================================================
-- ENTERPRISE DIGITAL TWIN — RBAC Setup Script for Render.com
-- Chạy script này SAU KHI restore backup_edt.sql lên cloud DB
-- ============================================================

-- Bước 1: Tạo restricted role cho AI Analyst
-- (Role này không có quyền login, chỉ được SET ROLE bởi superuser)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'edt_ai_analyst') THEN
        CREATE ROLE edt_ai_analyst NOLOGIN;
        RAISE NOTICE 'Role edt_ai_analyst created.';
    ELSE
        RAISE NOTICE 'Role edt_ai_analyst already exists, skipping.';
    END IF;
END
$$;

-- Bước 2: Grant SELECT trên các bảng vận hành (Layer 1-5) — AI Analyst được phép
GRANT SELECT ON
    orders,
    order_items,
    order_status_history,
    payments,
    payment_methods,
    payment_status_history,
    shipments,
    shipment_status_history,
    carriers,
    categories,
    products,
    suppliers,
    supplier_products,
    purchase_orders,
    purchase_order_items,
    warehouses,
    inventory_snapshots,
    inventory_movements,
    customers,
    customer_tickets,
    customer_behavior_events,
    stores,
    employees,
    reviews,
    marketing_campaigns,
    marketing_events,
    financial_transactions,
    incident_entities
TO edt_ai_analyst;

-- Bước 3: Grant SELECT trên view an toàn Layer 5
-- View này ẩn scenario_id và root_causes — ngăn ground truth leakage
GRANT SELECT ON ai_incident_observations TO edt_ai_analyst;

-- Bước 4: KHÔNG grant quyền gì trên các bảng Ground Truth (Layer 6 & 7)
-- incidents, causal_nodes, causal_links, causal_outcomes
-- benchmark_cases, evaluation_targets
-- Không cần REVOKE vì mặc định không có quyền

-- Kiểm tra kết quả
DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '=== RBAC Setup Complete ===';
    RAISE NOTICE 'Tables accessible by edt_ai_analyst:';
    FOR r IN
        SELECT table_name
        FROM information_schema.role_table_grants
        WHERE grantee = 'edt_ai_analyst'
          AND privilege_type = 'SELECT'
        ORDER BY table_name
    LOOP
        RAISE NOTICE '  + %', r.table_name;
    END LOOP;
END
$$;
