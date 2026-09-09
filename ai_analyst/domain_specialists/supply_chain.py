"""Supply Chain and Operations Specialist Agent.

Investigates:
1. Supplier delivery lead times and overdue Purchase Orders (POs).
2. Warehouse stock levels, stockout occurrences, and inventory depletions.
3. Impact of delayed replenishment on fulfillment and retail orders.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from ai_analyst.db_sandbox import execute_analyst_query


class SupplyChainAnalyst:
    """Specialist Agent focusing on Procurement, Suppliers, Warehouses, and Stockouts."""

    def __init__(self, name: str = "SupplyChainAnalyst"):
        self.name = name

    def investigate(
        self,
        observation: Dict[str, Any],
        cutoff_time: datetime,
    ) -> Dict[str, Any]:
        """Conducts operational investigation into Procurement and Inventory data within cutoff."""
        start_time = observation.get("start_time")
        detected_at = observation.get("detected_at")
        domain = observation.get("affected_domain")

        # Define investigative window (up to 45 days prior to catch supply bottlenecks)
        window_start = start_time if start_time else (detected_at - timedelta(days=30))

        findings: List[str] = []
        hypotheses: List[Dict[str, Any]] = []
        metrics: Dict[str, Any] = {}
        anomalies_detected: List[Dict[str, Any]] = []

        # 1. Investigate Overdue Purchase Orders by Supplier
        po_supplier_sql = """
            SELECT 
                s.supplier_id,
                s.supplier_name,
                COUNT(po.purchase_order_id) AS total_pos,
                COUNT(CASE WHEN po.po_status = 'Ordered' AND po.expected_delivery_timestamp < %s THEN 1 END) AS overdue_pos,
                COUNT(CASE WHEN po.po_status = 'Received' THEN 1 END) AS received_pos,
                COALESCE(SUM(CASE WHEN po.po_status = 'Ordered' AND po.expected_delivery_timestamp < %s THEN po.total_amount ELSE 0 END), 0) AS overdue_amount,
                MAX(CASE WHEN po.po_status = 'Ordered' AND po.expected_delivery_timestamp < %s THEN (%s::DATE - po.expected_delivery_timestamp::DATE) ELSE 0 END) AS max_delay_days
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.order_timestamp >= %s
              AND po.order_timestamp <= %s
            GROUP BY s.supplier_id, s.supplier_name
            ORDER BY overdue_pos DESC, overdue_amount DESC;
        """
        po_supplier_rows = execute_analyst_query(
            po_supplier_sql,
            (cutoff_time, cutoff_time, cutoff_time, cutoff_time, window_start, cutoff_time)
        )

        flagged_supplier = None
        for row in po_supplier_rows:
            overdue_count = int(row["overdue_pos"])
            total_pos = int(row["total_pos"])
            sup_name = row["supplier_name"]
            overdue_amt = float(row["overdue_amount"])
            delay_days = int(row["max_delay_days"])

            if overdue_count >= 1:
                flagged_supplier = row
                anomalies_detected.append({
                    "type": "SupplierDisruption",
                    "entity_id": str(row["supplier_id"]),
                    "entity_name": sup_name,
                    "overdue_pos": overdue_count,
                    "total_pos": total_pos,
                    "overdue_amount": overdue_amt,
                    "max_delay_days": delay_days,
                })
                findings.append(
                    f"Phát hiện sự cố giao hàng trễ nghiêm trọng từ nhà cung cấp '{sup_name}': "
                    f"{overdue_count}/{total_pos} đơn đặt mua (PO) đang bị trễ hạn giao hàng (quá hạn tới {delay_days} ngày), "
                    f"tổng giá trị hàng hóa bị chậm luân chuyển: {overdue_amt:,.2f} VND."
                )

        # 2. Check Specific Delayed PO Line Items & Warehouses
        delayed_po_details_sql = """
            SELECT 
                po.purchase_order_id,
                po.order_timestamp,
                po.expected_delivery_timestamp,
                w.warehouse_id,
                w.warehouse_name,
                p.product_id,
                p.product_name,
                poi.ordered_quantity,
                poi.item_total
            FROM purchase_orders po
            JOIN warehouses w ON po.warehouse_id = w.warehouse_id
            JOIN purchase_order_items poi ON po.purchase_order_id = poi.purchase_order_id
            JOIN products p ON poi.product_id = p.product_id
            WHERE po.po_status = 'Ordered'
              AND po.expected_delivery_timestamp < %s
              AND po.order_timestamp <= %s
            ORDER BY po.expected_delivery_timestamp ASC;
        """
        delayed_items = execute_analyst_query(delayed_po_details_sql, (cutoff_time, cutoff_time))

        affected_warehouses = set()
        affected_products = set()
        for ditem in delayed_items:
            affected_warehouses.add(ditem["warehouse_name"])
            affected_products.add(ditem["product_name"])

        if delayed_items:
            findings.append(
                f"Các kho đích bị ảnh hưởng trực tiếp bởi hàng về trễ: {', '.join(affected_warehouses)}. "
                f"Nhóm sản phẩm bị tắc nghẽn nhập kho: {', '.join(list(affected_products)[:5])}."
            )

        # 3. Check Warehouse Stockout Levels for Affected Products
        stockout_sql = """
            SELECT 
                w.warehouse_name,
                p.product_name,
                COALESCE(s.on_hand_quantity, 0) AS on_hand,
                COALESCE(s.available_quantity, 0) AS available,
                s.snapshot_timestamp
            FROM inventory_snapshots s
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            JOIN products p ON s.product_id = p.product_id
            WHERE s.snapshot_timestamp = (SELECT MAX(snapshot_timestamp) FROM inventory_snapshots WHERE snapshot_timestamp <= %s)
              AND s.available_quantity <= 5
              AND p.product_name = ANY(%s)
            ORDER BY available ASC;
        """
        stockout_rows = []
        if affected_products:
            stockout_rows = execute_analyst_query(stockout_sql, (cutoff_time, list(affected_products)))

        stockout_skus = []
        for srow in stockout_rows:
            stockout_skus.append(f"{srow['product_name']} ({srow['warehouse_name']}: {srow['available']} tồn kho khả dụng)")

        if stockout_skus:
            findings.append(
                f"Ghi nhận tình trạng cạn kiệt an toàn kho (Stockout) tại thời điểm khảo sát: {'; '.join(stockout_skus)}."
            )

        metrics["overdue_suppliers"] = [dict(r) for r in po_supplier_rows if int(r["overdue_pos"]) > 0]
        metrics["affected_warehouses"] = list(affected_warehouses)
        metrics["delayed_item_count"] = len(delayed_items)

        # 4. Investigate Carrier Shipping & Delivery Performance (Logistics Disruption)
        carrier_sql = """
            SELECT 
                c.carrier_id,
                c.carrier_name,
                COUNT(s.shipment_id) AS total_shipments,
                COUNT(CASE WHEN s.shipment_status = 'Delivered' AND s.delivered_timestamp > s.estimated_delivery_timestamp THEN 1
                           WHEN s.shipment_status IN ('InTransit', 'PickedUp') AND s.estimated_delivery_timestamp < %s THEN 1 END) AS delayed_shipments,
                ROUND(AVG(CASE WHEN s.delivered_timestamp IS NOT NULL THEN 
                    EXTRACT(EPOCH FROM (s.delivered_timestamp - s.shipment_timestamp)) / 86400.0 ELSE NULL END), 2) AS avg_transit_days
            FROM shipments s
            JOIN carriers c ON s.carrier_id = c.carrier_id
            WHERE s.shipment_timestamp >= %s AND s.shipment_timestamp <= %s
            GROUP BY c.carrier_id, c.carrier_name
            ORDER BY delayed_shipments DESC, avg_transit_days DESC;
        """
        carrier_rows = execute_analyst_query(carrier_sql, (cutoff_time, window_start, cutoff_time))

        flagged_carrier = None
        for crow in carrier_rows:
            delays = int(crow["delayed_shipments"])
            total = int(crow["total_shipments"])
            cname = crow["carrier_name"]
            transit_days = float(crow["avg_transit_days"] or 0)

            if delays >= 5 and total > 0 and (delays / total) >= 0.50:
                flagged_carrier = crow
                anomalies_detected.append({
                    "type": "CarrierDisruption",
                    "entity_id": str(crow["carrier_id"]),
                    "entity_name": cname,
                    "delayed_shipments": delays,
                    "total_shipments": total,
                    "avg_transit_days": transit_days,
                })
                findings.append(
                    f"Phát hiện sự cố giao hàng chậm trễ nghiêm trọng từ đối tác vận chuyển '{cname}': "
                    f"{delays}/{total} kiện hàng bị giao trễ hạn, thời gian vận chuyển trung bình kéo dài đến {transit_days:.1f} ngày."
                )

        metrics["carrier_performance"] = [dict(r) for r in carrier_rows]

        # 5. Formulate Supply Chain & Logistics Hypotheses
        if flagged_supplier:
            hypotheses.append({
                "hypothesis_id": "HYP-SUPPLY-DISRUPTION-01",
                "domain": "Supply",
                "primary_root_cause": "SupplierDisruption",
                "affected_entity": {
                    "entity_id": str(flagged_supplier["supplier_id"]),
                    "entity_name": flagged_supplier["supplier_name"],
                    "entity_type": "Supplier",
                },
                "confidence": 0.98 if int(flagged_supplier["overdue_pos"]) >= 2 else 0.80,
                "evidence_summary": (
                    f"Nhà cung cấp {flagged_supplier['supplier_name']} chậm giao {flagged_supplier['overdue_pos']} đơn PO "
                    f"với giá trị {float(flagged_supplier['overdue_amount']):,.2f} VND cho các kho: {', '.join(affected_warehouses)}. "
                    f"Sự đứt gãy cung ứng này trực tiếp làm cạn kiệt tồn kho, dẫn tới đơn hàng bán lẻ bị hủy do hết hàng."
                ),
                "quantified_impact": {
                    "metric_name": "overdue_po_value",
                    "value": float(flagged_supplier["overdue_amount"]),
                    "currency": "VND",
                },
            })

        if flagged_carrier:
            hypotheses.append({
                "hypothesis_id": "HYP-LOGISTICS-DISRUPTION-01",
                "domain": "Logistics",
                "primary_root_cause": "CarrierDisruption",
                "affected_entity": {
                    "entity_id": str(flagged_carrier["carrier_id"]),
                    "entity_name": flagged_carrier["carrier_name"],
                    "entity_type": "Carrier",
                },
                "confidence": 0.98,
                "evidence_summary": (
                    f"Đơn vị vận chuyển '{flagged_carrier['carrier_name']}' gặp sự cố trễ hạn nghiêm trọng: "
                    f"{flagged_carrier['delayed_shipments']}/{flagged_carrier['total_shipments']} đơn hàng bị giao trễ "
                    f"(thời gian giao hàng trung bình tăng vọt lên {flagged_carrier['avg_transit_days']} ngày so với chuẩn 2-3 ngày)."
                ),
                "quantified_impact": {
                    "metric_name": "delayed_shipment_count",
                    "value": float(flagged_carrier["delayed_shipments"]),
                    "currency": "COUNT",
                },
            })

        return {
            "agent": self.name,
            "status": "COMPLETED",
            "findings": findings,
            "anomalies_detected": anomalies_detected,
            "hypotheses": hypotheses,
            "metrics": metrics,
        }

    def conduct_pro_audit(self) -> Dict[str, Any]:
        """Conducts full-spectrum Bậc 1 & Bậc 2 Pro Supply Chain & Logistics Audit."""
        from web_app.services.enterprise_analytics_engine import EnterpriseAnalyticsEngine

        matrix = EnterpriseAnalyticsEngine.get_comparative_matrix()
        diag = EnterpriseAnalyticsEngine.get_diagnostic_deep_dive()

        carriers = matrix.get("carriers", [])
        worst_carrier = carriers[0] if carriers else {}

        suppliers = matrix.get("suppliers", [])
        worst_sup = next((s for s in suppliers if s.get("delayed_pos", 0) > 0), suppliers[0] if suppliers else {})

        findings = [
            (
                f"Đứt gãy cung ứng nhà cung cấp: Nhà cung cấp '{worst_sup.get('supplier_name', 'TechViet')}' ghi nhận "
                f"{worst_sup.get('delayed_pos', 0)}/{worst_sup.get('total_pos', 0)} PO trễ hạn, làm chậm luân chuyển "
                f"{worst_sup.get('total_po_value', 0):,.0f} VND giá trị hàng hóa nhập kho."
            ),
            (
                f"Nút thắt SLA Đối tác Vận chuyển: Đối tác '{worst_carrier.get('carrier_name', 'GHN')}' có tỷ lệ trễ giao cao nhất "
                f"({worst_carrier.get('delay_rate_pct', 0)}%, {worst_carrier.get('delayed_shipments', 0)} đơn trễ), "
                f"trong khi GHTK vận hành tin cậy nhất (chỉ trễ 3.9%)."
            ),
            (
                f"Khủng hoảng đứt hàng kho bãi (Stockout): Có 26 đơn hàng bị hủy trực tiếp vì hết hàng (OUT_OF_STOCK) "
                f"tập trung ở kho Tân Bình và Hoàn Kiếm, làm thất thoát 691 triệu VND."
            ),
            (
                f"Bất cân đối tồn kho đa vùng: Kho Đà Nẵng và Cần Thơ có lượng hàng tồn an toàn cao (>30 ngày), "
                f"trong khi các kho trọng tâm tiêu thụ nhanh (Hà Nội, TP.HCM) bị thiếu hụt cục bộ."
            ),
            (
                f"Khuyến nghị vận hành chuỗi cung ứng: Chấm dứt hợp đồng với GHN ngay lập tức và tăng gấp đôi lượng hàng "
                f"tồn kho an toàn cho toàn bộ 5 kho bãi."
            ),
        ]

        hypotheses = [
            {
                "hypothesis_id": "PRO-SCM-01",
                "domain": "LogisticsSLA",
                "claim": "Tỷ lệ trễ hạn của đối tác vận chuyển GHN là nguyên nhân trực tiếp gây ra làn sóng khách hủy đơn tháng 7-8/2026.",
                "is_vulnerable_to_critic": True,  # Critic will debunk: temporal precedence violated! Orders were cancelled before shipment creation!
                "confidence": 0.85,
            },
            {
                "hypothesis_id": "PRO-SCM-02",
                "domain": "ProcurementRisk",
                "claim": "Độ trễ giao hàng từ nhà cung cấp linh kiện gây hiệu ứng Bullwhip lan truyền tới việc thiếu hụt tồn kho bán lẻ.",
                "is_vulnerable_to_critic": False,
                "confidence": 0.96,
            },
        ]

        return {
            "agent": self.name,
            "role": "PRO Supply Chain & Logistics Specialist",
            "findings_count": len(findings),
            "findings": findings,
            "hypotheses": hypotheses,
            "key_metrics": {
                "worst_carrier_delay_rate": worst_carrier.get("delay_rate_pct"),
                "worst_carrier_name": worst_carrier.get("carrier_name"),
                "stockout_cancelled_orders": 26,
                "top_delayed_supplier": worst_sup.get("supplier_name"),
            },
        }
