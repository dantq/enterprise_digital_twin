"""Enterprise Multi-Dimensional Analytics & Diagnostic Engine (Bậc 1 & Bậc 2).

Provides comprehensive mathematical and business intelligence:
1. Multi-Temporal Analysis:
   - Month-over-Month (MoM), Quarter-over-Quarter (QoQ), Year-over-Year (YoY) growth.
   - Decomposition of Gross Revenue, Discounts, Net Revenue, COGS, Gross Margin %, Order Volumes, AOV.
2. Comparative Benchmarking Matrix:
   - Omnichannel Matrix (Channels: Website, Mobile App, Marketplace, Store).
   - Store / Branch Matrix (Physical branches across regions).
   - Carrier Logistics SLA Matrix (GHN, Viettel Post, VNPost, J&T, GHTK).
   - Payment Methods & Gateway Friction Matrix (MoMo, Credit Card, Bank Transfer, ZaloPay, COD).
   - Supplier Procurement & On-Time Performance Matrix.
3. Diagnostic & Root-Cause Analysis (Bậc 2):
   - Cancellation reason decomposition (OUT_OF_STOCK, PAYMENT_TIMEOUT, CUSTOMER_CANCELLED).
   - Statistical anomaly isolation using Z-Scores (mu +/- 2 sigma).
   - Economic loss attribution across operational bottlenecks.
"""

import math
from datetime import datetime
from typing import Any, Dict, List, Optional
from ai_analyst.db_sandbox import execute_analyst_query


class EnterpriseAnalyticsEngine:
    """Core deterministic analytics engine supporting Bậc 1 (Descriptive) and Bậc 2 (Diagnostic)."""

    @staticmethod
    def get_temporal_growth_analysis(grain: str = "month") -> Dict[str, Any]:
        """Calculates multi-temporal time series from 2025 to 2026 with MoM/QoQ/YoY growth rates."""
        grain_sql = "month" if grain == "month" else "quarter"
        
        sql = f"""
            WITH period_metrics AS (
                SELECT 
                    date_trunc('{grain_sql}', o.order_timestamp)::date AS period_date,
                    TO_CHAR(date_trunc('{grain_sql}', o.order_timestamp), 
                        CASE WHEN '{grain_sql}' = 'month' THEN 'YYYY-MM' ELSE 'YYYY-"Q"Q' END
                    ) AS period_label,
                    COUNT(o.order_id) AS total_orders,
                    COUNT(CASE WHEN o.order_status IN ('Delivered', 'Shipped', 'Fulfilled') THEN 1 END) AS successful_orders,
                    COUNT(CASE WHEN o.order_status = 'Cancelled' THEN 1 END) AS cancelled_orders,
                    COALESCE(SUM(o.subtotal), 0) AS gross_sales,
                    COALESCE(SUM(o.discount_amount), 0) AS total_discounts,
                    COALESCE(SUM(CASE WHEN o.order_status IN ('Delivered', 'Shipped', 'Fulfilled') THEN o.total_amount ELSE 0 END), 0) AS net_revenue,
                    COALESCE(SUM(o.total_amount), 0) AS booked_volume
                FROM orders o
                GROUP BY 1, 2
                ORDER BY 1 ASC
            ),
            cogs_metrics AS (
                SELECT 
                    date_trunc('{grain_sql}', o.order_timestamp)::date AS period_date,
                    COALESCE(SUM(oi.quantity * p.unit_cost), 0) AS cogs
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                JOIN products p ON oi.product_id = p.product_id
                WHERE o.order_status IN ('Delivered', 'Shipped', 'Fulfilled')
                GROUP BY 1
            )
            SELECT 
                pm.period_date,
                pm.period_label,
                pm.total_orders,
                pm.successful_orders,
                pm.cancelled_orders,
                ROUND(pm.cancelled_orders::NUMERIC / NULLIF(pm.total_orders, 0) * 100, 2) AS cancellation_rate_pct,
                ROUND(pm.gross_sales, 2) AS gross_sales,
                ROUND(pm.total_discounts, 2) AS total_discounts,
                ROUND(pm.net_revenue, 2) AS net_revenue,
                ROUND(pm.booked_volume, 2) AS booked_volume,
                ROUND(COALESCE(cm.cogs, 0), 2) AS cogs,
                ROUND(pm.net_revenue - COALESCE(cm.cogs, 0), 2) AS gross_profit,
                ROUND(
                    (pm.net_revenue - COALESCE(cm.cogs, 0))::NUMERIC / NULLIF(pm.net_revenue, 0) * 100, 2
                ) AS gross_margin_pct,
                ROUND(pm.booked_volume::NUMERIC / NULLIF(pm.total_orders, 0), 2) AS aov
            FROM period_metrics pm
            LEFT JOIN cogs_metrics cm ON pm.period_date = cm.period_date
            ORDER BY pm.period_date ASC;
        """
        rows = execute_analyst_query(sql)

        # Calculate MoM, QoQ, YoY in Python
        periods: List[Dict[str, Any]] = []
        label_map: Dict[str, Dict[str, Any]] = {}

        for i, row in enumerate(rows):
            p_data = {
                "period_date": str(row["period_date"]),
                "period_label": row["period_label"],
                "total_orders": int(row["total_orders"] or 0),
                "successful_orders": int(row["successful_orders"] or 0),
                "cancelled_orders": int(row["cancelled_orders"] or 0),
                "cancellation_rate_pct": float(row["cancellation_rate_pct"] or 0.0),
                "gross_sales": float(row["gross_sales"] or 0.0),
                "total_discounts": float(row["total_discounts"] or 0.0),
                "net_revenue": float(row["net_revenue"] or 0.0),
                "booked_volume": float(row["booked_volume"] or 0.0),
                "cogs": float(row["cogs"] or 0.0),
                "gross_profit": float(row["gross_profit"] or 0.0),
                "gross_margin_pct": float(row["gross_margin_pct"] or 0.0),
                "aov": float(row["aov"] or 0.0),
                "growth_mom_pct": 0.0,
                "growth_yoy_pct": None,
            }

            # MoM / Prior-period growth
            if i > 0:
                prev_rev = periods[i - 1]["net_revenue"]
                if prev_rev > 0:
                    mom = ((p_data["net_revenue"] - prev_rev) / prev_rev) * 100.0
                    p_data["growth_mom_pct"] = round(mom, 2)

            # YoY calculation
            label = row["period_label"]
            parts = label.split("-")
            if len(parts) == 2:
                year, sub = parts[0], parts[1]
                prev_year = str(int(year) - 1)
                prior_label = f"{prev_year}-{sub}"
                if prior_label in label_map:
                    prior_rev = label_map[prior_label]["net_revenue"]
                    if prior_rev > 0:
                        yoy = ((p_data["net_revenue"] - prior_rev) / prior_rev) * 100.0
                        p_data["growth_yoy_pct"] = round(yoy, 2)

            label_map[label] = p_data
            periods.append(p_data)

        # Summary aggregates
        total_booked = sum(p["booked_volume"] for p in periods)
        total_net = sum(p["net_revenue"] for p in periods)
        total_orders = sum(p["total_orders"] for p in periods)
        total_cancelled = sum(p["cancelled_orders"] for p in periods)

        return {
            "grain": grain,
            "total_periods": len(periods),
            "summary": {
                "total_booked_volume": round(total_booked, 2),
                "total_recognized_net_revenue": round(total_net, 2),
                "total_orders": total_orders,
                "total_cancelled_orders": total_cancelled,
                "overall_cancellation_rate_pct": round(total_cancelled / total_orders * 100, 2) if total_orders else 0.0,
            },
            "timeline": periods,
        }

    @staticmethod
    def get_comparative_matrix() -> Dict[str, Any]:
        """Generates cross-dimensional benchmarking matrices across Channels, Stores, Carriers, Payments, and Suppliers."""
        
        # 1. Omnichannel Matrix
        channel_sql = """
            SELECT 
                channel,
                COUNT(order_id) AS total_orders,
                COUNT(CASE WHEN order_status IN ('Delivered', 'Shipped', 'Fulfilled') THEN 1 END) AS successful_orders,
                COUNT(CASE WHEN order_status = 'Cancelled' THEN 1 END) AS cancelled_orders,
                COALESCE(SUM(total_amount), 0) AS total_volume,
                COALESCE(SUM(CASE WHEN order_status IN ('Delivered', 'Shipped', 'Fulfilled') THEN total_amount ELSE 0 END), 0) AS recognized_revenue,
                ROUND(AVG(total_amount), 2) AS aov,
                ROUND(COUNT(CASE WHEN order_status = 'Cancelled' THEN 1 END)::NUMERIC / NULLIF(COUNT(order_id), 0) * 100, 2) AS cancel_rate_pct
            FROM orders
            GROUP BY channel
            ORDER BY recognized_revenue DESC;
        """
        channels = [
            {
                "channel": r["channel"] or "Unknown",
                "total_orders": int(r["total_orders"]),
                "successful_orders": int(r["successful_orders"]),
                "cancelled_orders": int(r["cancelled_orders"]),
                "cancel_rate_pct": float(r["cancel_rate_pct"] or 0),
                "total_volume": float(r["total_volume"] or 0),
                "recognized_revenue": float(r["recognized_revenue"] or 0),
                "aov": float(r["aov"] or 0),
            }
            for r in execute_analyst_query(channel_sql)
        ]

        # 2. Stores / Physical Branches Matrix
        store_sql = """
            SELECT 
                s.store_id,
                s.store_code,
                s.store_name,
                s.city,
                s.region,
                s.store_type,
                COUNT(o.order_id) AS total_orders,
                COALESCE(SUM(o.total_amount), 0) AS total_revenue,
                COUNT(DISTINCT e.employee_id) AS staff_count
            FROM stores s
            LEFT JOIN orders o ON s.store_id = o.store_id
            LEFT JOIN employees e ON s.store_id = e.store_id
            GROUP BY s.store_id, s.store_code, s.store_name, s.city, s.region, s.store_type
            ORDER BY total_revenue DESC;
        """
        stores = [
            {
                "store_id": str(r["store_id"]),
                "store_code": r["store_code"],
                "store_name": r["store_name"],
                "city": r["city"],
                "region": r["region"],
                "store_type": r["store_type"],
                "total_orders": int(r["total_orders"] or 0),
                "total_revenue": float(r["total_revenue"] or 0),
                "staff_count": int(r["staff_count"] or 0),
            }
            for r in execute_analyst_query(store_sql)
        ]

        # 3. Carrier Logistics & SLA Matrix
        carrier_sql = """
            SELECT 
                c.carrier_id,
                c.carrier_name,
                c.average_delivery_days AS target_delivery_days,
                c.delivery_reliability,
                COUNT(s.shipment_id) AS total_shipments,
                COUNT(CASE WHEN s.shipment_status = 'Delivered' THEN 1 END) AS delivered_shipments,
                COUNT(CASE 
                    WHEN s.shipment_status = 'Delivered' AND s.delivered_timestamp > s.estimated_delivery_timestamp THEN 1
                END) AS delayed_shipments,
                ROUND(
                    COUNT(CASE WHEN s.shipment_status = 'Delivered' AND s.delivered_timestamp > s.estimated_delivery_timestamp THEN 1 END)::NUMERIC / 
                    NULLIF(COUNT(CASE WHEN s.shipment_status = 'Delivered' THEN 1 END), 0) * 100, 2
                ) AS delay_rate_pct,
                ROUND(
                    AVG(CASE WHEN s.shipment_status = 'Delivered' THEN 
                        EXTRACT(EPOCH FROM (s.delivered_timestamp - s.shipment_timestamp)) / 86400 
                    END)::NUMERIC, 2
                ) AS avg_delivery_days
            FROM carriers c
            LEFT JOIN shipments s ON c.carrier_id = s.carrier_id
            GROUP BY c.carrier_id, c.carrier_name, c.average_delivery_days, c.delivery_reliability
            ORDER BY delay_rate_pct DESC;
        """
        carriers = [
            {
                "carrier_id": str(r["carrier_id"]),
                "carrier_name": r["carrier_name"],
                "target_delivery_days": float(r["target_delivery_days"] or 0),
                "delivery_reliability": float(r["delivery_reliability"] or 0),
                "total_shipments": int(r["total_shipments"] or 0),
                "delivered_shipments": int(r["delivered_shipments"] or 0),
                "delayed_shipments": int(r["delayed_shipments"] or 0),
                "delay_rate_pct": float(r["delay_rate_pct"] or 0),
                "on_time_rate_pct": round(100.0 - float(r["delay_rate_pct"] or 0), 2),
                "avg_delivery_days": float(r["avg_delivery_days"] or 0),
            }
            for r in execute_analyst_query(carrier_sql)
        ]

        # 4. Payment Gateways & Failure Friction Matrix
        payment_sql = """
            SELECT 
                pm.payment_method_id,
                pm.method_name,
                pm.provider,
                COUNT(p.payment_id) AS total_transactions,
                COUNT(CASE WHEN p.payment_status IN ('Captured', 'Settled') THEN 1 END) AS successful_transactions,
                COUNT(CASE WHEN p.payment_status = 'Failed' THEN 1 END) AS failed_transactions,
                ROUND(
                    COUNT(CASE WHEN p.payment_status = 'Failed' THEN 1 END)::NUMERIC / 
                    NULLIF(COUNT(p.payment_id), 0) * 100, 2
                ) AS failure_rate_pct,
                COALESCE(SUM(CASE WHEN p.payment_status IN ('Captured', 'Settled') THEN p.amount ELSE 0 END), 0) AS captured_amount,
                COALESCE(SUM(CASE WHEN p.payment_status = 'Failed' THEN p.amount ELSE 0 END), 0) AS lost_transaction_amount
            FROM payment_methods pm
            LEFT JOIN payments p ON pm.payment_method_id = p.payment_method_id
            GROUP BY pm.payment_method_id, pm.method_name, pm.provider
            ORDER BY failure_rate_pct DESC;
        """
        payments = [
            {
                "payment_method_id": str(r["payment_method_id"]),
                "method_name": r["method_name"],
                "provider": r["provider"],
                "total_transactions": int(r["total_transactions"] or 0),
                "successful_transactions": int(r["successful_transactions"] or 0),
                "failed_transactions": int(r["failed_transactions"] or 0),
                "failure_rate_pct": float(r["failure_rate_pct"] or 0),
                "success_rate_pct": round(100.0 - float(r["failure_rate_pct"] or 0), 2),
                "captured_amount": float(r["captured_amount"] or 0),
                "lost_transaction_amount": float(r["lost_transaction_amount"] or 0),
            }
            for r in execute_analyst_query(payment_sql)
        ]

        # 5. Suppliers & Procurement Performance Matrix
        supplier_sql = """
            SELECT 
                s.supplier_id,
                s.supplier_name,
                s.reliability_score,
                s.average_lead_time_days,
                COUNT(po.purchase_order_id) AS total_pos,
                COUNT(CASE WHEN po.po_status = 'Delayed' OR (po.received_timestamp > po.expected_delivery_timestamp) THEN 1 END) AS delayed_pos,
                ROUND(
                    COUNT(CASE WHEN po.po_status = 'Delayed' OR (po.received_timestamp > po.expected_delivery_timestamp) THEN 1 END)::NUMERIC /
                    NULLIF(COUNT(po.purchase_order_id), 0) * 100, 2
                ) AS delay_rate_pct,
                COALESCE(SUM(po.total_amount), 0) AS total_po_value
            FROM suppliers s
            LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            GROUP BY s.supplier_id, s.supplier_name, s.reliability_score, s.average_lead_time_days
            ORDER BY total_po_value DESC;
        """
        suppliers = [
            {
                "supplier_id": str(r["supplier_id"]),
                "supplier_name": r["supplier_name"],
                "reliability_score": float(r["reliability_score"] or 0),
                "average_lead_time_days": float(r["average_lead_time_days"] or 0),
                "total_pos": int(r["total_pos"] or 0),
                "delayed_pos": int(r["delayed_pos"] or 0),
                "delay_rate_pct": float(r["delay_rate_pct"] or 0),
                "total_po_value": float(r["total_po_value"] or 0),
            }
            for r in execute_analyst_query(supplier_sql)
        ]

        return {
            "channels": channels,
            "stores": stores,
            "carriers": carriers,
            "payment_methods": payments,
            "suppliers": suppliers,
        }

    @staticmethod
    def get_diagnostic_deep_dive() -> Dict[str, Any]:
        """Performs deep diagnostic decomposition (Bậc 2) on cancellations, statistical anomalies, and loss attribution."""
        
        # 1. Decomposition of Order Cancellations
        reason_sql = """
            SELECT 
                COALESCE(reason_code, 'UNSPECIFIED') AS reason_code,
                COUNT(*) AS cancel_count,
                ROUND(COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER () * 100, 2) AS percentage
            FROM order_status_history
            WHERE status = 'Cancelled'
            GROUP BY 1
            ORDER BY cancel_count DESC;
        """
        cancellation_reasons = [
            {
                "reason_code": r["reason_code"],
                "cancel_count": int(r["cancel_count"]),
                "percentage": float(r["percentage"]),
                "operational_meaning": {
                    "OUT_OF_STOCK": "Kho đứt hàng do đứt gãy cung ứng hoặc mất cân đối tồn kho đa điểm",
                    "PAYMENT_TIMEOUT": "Khách hàng treo thanh toán do cổng thanh toán gặp lỗi kỹ thuật / timeout",
                    "CUSTOMER_CANCELLED": "Khách hàng chủ động hủy do chờ đợi xử lý quá lâu hoặc đổi ý",
                    "UNSPECIFIED": "Hủy đơn hệ thống tự động qua luồng Streaming Simulation",
                }.get(r["reason_code"], "Nguyên nhân vận hành khác"),
            }
            for r in execute_analyst_query(reason_sql)
        ]

        # 2. Statistical Anomaly Detection on Monthly Cancellation Rate (Z-score test)
        timeline = EnterpriseAnalyticsEngine.get_temporal_growth_analysis(grain="month")["timeline"]
        rates = [p["cancellation_rate_pct"] for p in timeline if p["total_orders"] >= 10]
        
        anomalous_periods: List[Dict[str, Any]] = []
        if len(rates) >= 4:
            mean_rate = sum(rates) / len(rates)
            variance = sum((x - mean_rate) ** 2 for x in rates) / (len(rates) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 1.0

            for p in timeline:
                rate = p["cancellation_rate_pct"]
                z_score = round((rate - mean_rate) / std_dev, 2) if std_dev > 0 else 0.0
                if z_score >= 1.96:  # 95% confidence interval
                    anomalous_periods.append({
                        "period_label": p["period_label"],
                        "cancellation_rate_pct": rate,
                        "mean_baseline_pct": round(mean_rate, 2),
                        "z_score": z_score,
                        "severity": "CRITICAL" if z_score >= 3.0 else "HIGH",
                        "diagnostic_verdict": f"Tỷ lệ hủy đơn đạt {rate}% (vượt {z_score} độ lệch chuẩn so với mức trung bình {mean_rate:.1f}%).",
                    })

        # 3. Incident Financial Loss Quantification Attribution
        incident_loss_sql = """
            SELECT 
                'OUT_OF_STOCK' AS cause,
                COALESCE(SUM(o.total_amount), 0) AS estimated_lost_revenue,
                COUNT(o.order_id) AS impacted_orders
            FROM orders o
            JOIN order_status_history osh ON o.order_id = osh.order_id
            WHERE osh.status = 'Cancelled' AND osh.reason_code = 'OUT_OF_STOCK'
            UNION ALL
            SELECT 
                'PAYMENT_FAILURE' AS cause,
                COALESCE(SUM(p.amount), 0) AS estimated_lost_revenue,
                COUNT(p.payment_id) AS impacted_orders
            FROM payments p
            WHERE p.payment_status = 'Failed'
            UNION ALL
            SELECT 
                'CUSTOMER_CANCELLED' AS cause,
                COALESCE(SUM(o.total_amount), 0) AS estimated_lost_revenue,
                COUNT(o.order_id) AS impacted_orders
            FROM orders o
            JOIN order_status_history osh ON o.order_id = osh.order_id
            WHERE osh.status = 'Cancelled' AND osh.reason_code = 'CUSTOMER_CANCELLED';
        """
        loss_attribution = [
            {
                "cause": r["cause"],
                "estimated_lost_revenue": float(r["estimated_lost_revenue"] or 0),
                "impacted_orders": int(r["impacted_orders"] or 0),
            }
            for r in execute_analyst_query(incident_loss_sql)
        ]

        total_quantified_loss = sum(item["estimated_lost_revenue"] for item in loss_attribution)

        return {
            "cancellation_decomposition": cancellation_reasons,
            "statistical_anomalies": anomalous_periods,
            "loss_attribution": loss_attribution,
            "total_quantified_erosion_loss": total_quantified_loss,
        }

    @staticmethod
    def get_executive_summary_report() -> Dict[str, Any]:
        """Synthesizes high-level insights across Bậc 1 & Bậc 2 for C-Level and the 6-Agent Committee."""
        temporal = EnterpriseAnalyticsEngine.get_temporal_growth_analysis(grain="month")
        matrix = EnterpriseAnalyticsEngine.get_comparative_matrix()
        diagnostic = EnterpriseAnalyticsEngine.get_diagnostic_deep_dive()

        timeline = temporal.get("timeline", [])
        latest_period = timeline[-1] if timeline else {}
        prev_period = timeline[-2] if len(timeline) >= 2 else {}

        top_channel = matrix["channels"][0] if matrix["channels"] else {}
        worst_carrier = matrix["carriers"][0] if matrix["carriers"] else {}
        worst_payment = matrix["payment_methods"][0] if matrix["payment_methods"] else {}

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "WARNING" if diagnostic["statistical_anomalies"] else "HEALTHY",
            "executive_summary": {
                "latest_period": latest_period.get("period_label"),
                "latest_revenue": latest_period.get("net_revenue"),
                "latest_mom_growth_pct": latest_period.get("growth_mom_pct"),
                "total_historical_orders": temporal["summary"]["total_orders"],
                "historical_cancellation_rate_pct": temporal["summary"]["overall_cancellation_rate_pct"],
                "total_quantified_loss_vnd": diagnostic["total_quantified_erosion_loss"],
            },
            "top_operational_findings": [
                f"Kênh sinh lời chủ lực: '{top_channel.get('channel')}' với doanh thu thuần {top_channel.get('recognized_revenue', 0):,.0f} VND ({top_channel.get('total_orders')} đơn).",
                f"Điểm nghẽn Logistics: Đối tác '{worst_carrier.get('carrier_name')}' có tỷ lệ trễ giao cao nhất ({worst_carrier.get('delay_rate_pct')}%, {worst_carrier.get('delayed_shipments')} đơn trễ).",
                f"Ma sát Cổng thanh toán: Cổng '{worst_payment.get('method_name')}' có tỷ lệ giao dịch thất bại cao nhất ({worst_payment.get('failure_rate_pct')}%, thất thoát ước tính: {worst_payment.get('lost_transaction_amount', 0):,.0f} VND).",
                f"Phát hiện {len(diagnostic['statistical_anomalies'])} kỳ kinh doanh có tỷ lệ hủy đơn đột biến đạt mức ý nghĩa thống kê (Z-score >= 1.96).",
            ],
            "data_slices": {
                "temporal": temporal,
                "comparative": matrix,
                "diagnostic": diagnostic,
            },
        }
