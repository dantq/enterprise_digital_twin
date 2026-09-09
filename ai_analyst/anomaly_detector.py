"""Business Heartbeat & Anomaly Detector Engine for Enterprise Digital Twin.

Monitors operational metrics across 5 core enterprise domains:
1. Payment Systems: Failure spikes, gateway dropouts, lost transaction amounts.
2. Supply Chain: Overdue purchase orders, supplier fulfillment delays, stockouts.
3. Logistics & Carrier SLAs: Delivery delays, on-time breach rates by carrier.
4. Marketing Operations: Budget burn vs low conversion, CAC inflation, conversion collapses.
5. Customer Experience & Quality: 1-star review spikes, ticket surges, defect rates.

Provides:
- Real-time pulse scanning (`run_full_scan`).
- Anomaly categorization with severity ratings (CRITICAL, HIGH, MEDIUM).
- Seamless integration with MultiAgentOrchestrator for automated RCA dispatch.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from ai_analyst.db_sandbox import execute_analyst_query, get_incident_observations


class BusinessHeartbeatDetector:
    """Continuous operational scanner detecting anomalies across enterprise domains."""

    def __init__(self):
        # Detection Thresholds
        self.payment_failure_threshold = 0.20       # >20% failure rate indicates gateway/method anomaly
        self.payment_min_attempts = 5              # At least 5 attempts to consider spike
        self.logistics_delay_threshold = 0.20       # >20% delay rate in carrier shipments
        self.logistics_min_shipments = 5           # At least 5 shipments
        self.supply_overdue_days_threshold = 1      # >=1 overdue PO in key supplier
        self.marketing_min_clicks = 1000           # At least 1,000 clicks
        self.marketing_cvr_floor = 0.01            # CVR < 1% with significant spend
        self.customer_one_star_min = 5             # At least 5 1-star reviews for a product

    def scan_payment_health(self) -> List[Dict[str, Any]]:
        """Scans payment methods for failure spikes and high lost revenue."""
        anomalies = []
        sql = """
            SELECT 
                pm.payment_method_id,
                pm.method_name,
                pm.provider,
                COUNT(p.payment_id) AS total_attempts,
                COUNT(CASE WHEN p.payment_status = 'Failed' THEN 1 END) AS failed_attempts,
                ROUND(
                    COUNT(CASE WHEN p.payment_status = 'Failed' THEN 1 END)::NUMERIC / 
                    NULLIF(COUNT(p.payment_id), 0), 4
                ) AS failure_rate,
                COALESCE(SUM(CASE WHEN p.payment_status = 'Failed' THEN p.amount ELSE 0 END), 0) AS failed_amount,
                MIN(p.payment_timestamp) AS window_start,
                MAX(p.payment_timestamp) AS window_end
            FROM payments p
            JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
            GROUP BY pm.payment_method_id, pm.method_name, pm.provider
            HAVING COUNT(p.payment_id) >= %s
            ORDER BY failure_rate DESC;
        """
        rows = execute_analyst_query(sql, (self.payment_min_attempts,))
        for r in rows:
            frate = float(r["failure_rate"] or 0)
            failed_count = int(r["failed_attempts"] or 0)
            provider = r["provider"] or r["method_name"]
            failed_amount = float(r["failed_amount"] or 0)

            if frate >= self.payment_failure_threshold:
                severity = "CRITICAL" if frate >= 0.35 or failed_amount >= 50_000_000 else "HIGH"
                anomalies.append({
                    "domain": "Payment",
                    "code": "ANOM_PAYMENT_FAILURE_SPIKE",
                    "severity": severity,
                    "entity_id": str(r["payment_method_id"]),
                    "entity_name": f"{r['method_name']} ({provider})",
                    "metric_name": "payment_failure_rate",
                    "metric_value": round(frate * 100, 2),
                    "threshold": round(self.payment_failure_threshold * 100, 2),
                    "unit": "%",
                    "failed_amount": failed_amount,
                    "description": (
                        f"Phát hiện tỷ lệ thanh toán thất bại đột biến ở cổng {r['method_name']} ({provider}) "
                        f"đạt {frate*100:.1f}% ({failed_count}/{r['total_attempts']} giao dịch lỗi, "
                        f"tổng tiền thất thoát ước tính: {failed_amount:,.0f} VND)."
                    ),
                    "symptom": f"Payment failure rate reached {frate*100:.1f}% on {r['method_name']} with {failed_amount:,.0f} VND failed volume.",
                    "window_start": r["window_start"],
                    "window_end": r["window_end"],
                })
        return anomalies

    def scan_logistics_health(self) -> List[Dict[str, Any]]:
        """Scans carrier performance for SLA breach and high delivery delay rates."""
        anomalies = []
        sql = """
            SELECT 
                c.carrier_id,
                c.carrier_name,
                COUNT(s.shipment_id) AS total_shipments,
                COUNT(CASE 
                    WHEN s.shipment_status = 'Delivered' AND s.delivered_timestamp > s.estimated_delivery_timestamp THEN 1
                    WHEN s.shipment_status IN ('InTransit', 'PickedUp', 'Delayed') AND s.estimated_delivery_timestamp < CURRENT_TIMESTAMP THEN 1 
                END) AS delayed_count,
                ROUND(
                    COUNT(CASE 
                        WHEN s.shipment_status = 'Delivered' AND s.delivered_timestamp > s.estimated_delivery_timestamp THEN 1
                        WHEN s.shipment_status IN ('InTransit', 'PickedUp', 'Delayed') AND s.estimated_delivery_timestamp < CURRENT_TIMESTAMP THEN 1 
                    END)::NUMERIC / NULLIF(COUNT(s.shipment_id), 0), 4
                ) AS delay_rate,
                COALESCE(AVG(CASE WHEN s.delivered_timestamp > s.estimated_delivery_timestamp 
                    THEN EXTRACT(EPOCH FROM (s.delivered_timestamp - s.estimated_delivery_timestamp))/86400 ELSE 0 END), 0) AS avg_delay_days,
                MIN(s.shipment_timestamp) AS window_start,
                MAX(s.shipment_timestamp) AS window_end
            FROM shipments s
            JOIN carriers c ON s.carrier_id = c.carrier_id
            GROUP BY c.carrier_id, c.carrier_name
            HAVING COUNT(s.shipment_id) >= %s
            ORDER BY delay_rate DESC;
        """
        rows = execute_analyst_query(sql, (self.logistics_min_shipments,))
        for r in rows:
            drate = float(r["delay_rate"] or 0)
            delayed_count = int(r["delayed_count"] or 0)
            avg_delay = float(r["avg_delay_days"] or 0)

            if drate >= self.logistics_delay_threshold:
                severity = "CRITICAL" if drate >= 0.40 or avg_delay >= 2.0 else "HIGH"
                anomalies.append({
                    "domain": "Delivery",
                    "code": "ANOM_LOGISTICS_SLA_BREACH",
                    "severity": severity,
                    "entity_id": str(r["carrier_id"]),
                    "entity_name": r["carrier_name"],
                    "metric_name": "carrier_delay_rate",
                    "metric_value": round(drate * 100, 2),
                    "threshold": round(self.logistics_delay_threshold * 100, 2),
                    "unit": "%",
                    "avg_delay_days": round(avg_delay, 1),
                    "description": (
                        f"Đơn vị vận chuyển {r['carrier_name']} vi phạm cam kết SLA: "
                        f"Tỷ lệ giao trễ đạt {drate*100:.1f}% ({delayed_count}/{r['total_shipments']} vận đơn), "
                        f"thời gian trễ trung bình {avg_delay:.1f} ngày/đơn."
                    ),
                    "symptom": f"Delivery delay rate spiked to {drate*100:.1f}% on carrier {r['carrier_name']}.",
                    "window_start": r["window_start"],
                    "window_end": r["window_end"],
                })
        return anomalies

    def scan_supply_inventory_health(self) -> List[Dict[str, Any]]:
        """Scans purchase orders and stock levels for supply disruptions."""
        anomalies = []
        sql = """
            SELECT 
                s.supplier_id,
                s.supplier_name,
                COUNT(po.purchase_order_id) AS total_pos,
                COUNT(CASE WHEN po.po_status = 'Ordered' AND po.expected_delivery_timestamp < CURRENT_TIMESTAMP THEN 1 END) AS overdue_pos,
                COALESCE(SUM(CASE WHEN po.po_status = 'Ordered' AND po.expected_delivery_timestamp < CURRENT_TIMESTAMP THEN po.total_amount ELSE 0 END), 0) AS overdue_amount,
                MIN(po.order_timestamp) AS window_start,
                MAX(po.expected_delivery_timestamp) AS window_end
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            GROUP BY s.supplier_id, s.supplier_name
            HAVING COUNT(CASE WHEN po.po_status = 'Ordered' AND po.expected_delivery_timestamp < CURRENT_TIMESTAMP THEN 1 END) >= 1
            ORDER BY overdue_pos DESC;
        """
        rows = execute_analyst_query(sql)
        for r in rows:
            overdue_cnt = int(r["overdue_pos"] or 0)
            overdue_amt = float(r["overdue_amount"] or 0)
            severity = "CRITICAL" if overdue_cnt >= 2 or overdue_amt >= 100_000_000 else "HIGH"
            anomalies.append({
                "domain": "Supply",
                "code": "ANOM_SUPPLIER_DISRUPTION",
                "severity": severity,
                "entity_id": str(r["supplier_id"]),
                "entity_name": r["supplier_name"],
                "metric_name": "overdue_po_count",
                "metric_value": overdue_cnt,
                "threshold": 1,
                "unit": "PO",
                "overdue_amount": overdue_amt,
                "description": (
                    f"Nhà cung cấp {r['supplier_name']} có {overdue_cnt} đơn hàng mua (PO) bị quá hạn giao, "
                    f"tổng giá trị hàng tắc nghẽn: {overdue_amt:,.0f} VND, gây nguy cơ đứt gãy tồn kho diện rộng."
                ),
                "symptom": f"Supplier {r['supplier_name']} has {overdue_cnt} overdue purchase orders causing severe inventory stockout.",
                "window_start": r["window_start"],
                "window_end": r["window_end"],
            })
        return anomalies

    def scan_marketing_health(self) -> List[Dict[str, Any]]:
        """Scans marketing campaigns for budget burn with sub-par conversion."""
        anomalies = []
        sql = """
            SELECT 
                c.campaign_id,
                c.campaign_name,
                c.channel,
                c.budget_amount,
                COALESCE(SUM(CASE WHEN e.event_type = 'Impression' THEN e.metric_value ELSE 0 END), 0) AS impressions,
                COALESCE(SUM(CASE WHEN e.event_type = 'Click' THEN e.metric_value ELSE 0 END), 0) AS clicks,
                COALESCE(SUM(CASE WHEN e.event_type = 'Conversion' THEN e.metric_value ELSE 0 END), 0) AS conversions,
                COALESCE(MAX(CASE WHEN e.event_type = 'Spend' THEN e.cost_amount ELSE 0 END), 0) AS recorded_spend,
                c.start_time,
                c.end_time
            FROM marketing_campaigns c
            LEFT JOIN marketing_events e ON c.campaign_id = e.campaign_id
            GROUP BY c.campaign_id, c.campaign_name, c.channel, c.budget_amount, c.start_time, c.end_time
            ORDER BY budget_amount DESC;
        """
        rows = execute_analyst_query(sql)
        for crow in rows:
            clicks = int(crow["clicks"] or 0)
            conversions = int(crow["conversions"] or 0)
            spend = float(crow["recorded_spend"] or crow["budget_amount"] or 0)
            cname = crow["campaign_name"]
            channel = crow["channel"]

            cvr = (conversions / clicks) if clicks > 0 else 0.0
            if clicks >= self.marketing_min_clicks and cvr <= self.marketing_cvr_floor and spend >= 20_000_000:
                severity = "CRITICAL" if cvr < 0.005 and spend >= 50_000_000 else "HIGH"
                anomalies.append({
                    "domain": "Marketing",
                    "code": "ANOM_MARKETING_INEFFICIENCY",
                    "severity": severity,
                    "entity_id": str(crow["campaign_id"]),
                    "entity_name": f"{cname} ({channel})",
                    "metric_name": "conversion_rate",
                    "metric_value": round(cvr * 100, 2),
                    "threshold": round(self.marketing_cvr_floor * 100, 2),
                    "unit": "%",
                    "spend": spend,
                    "clicks": clicks,
                    "conversions": conversions,
                    "description": (
                        f"Chiến dịch '{cname}' ({channel}) có dấu hiệu đốt ngân sách nghiêm trọng: "
                        f"Đã chi tiêu {spend:,.0f} VND nhận {clicks:,} clicks nhưng chỉ tạo ra {conversions} lượt chuyển đổi "
                        f"(CVR: {cvr*100:.2f}%, thấp hơn ngưỡng an toàn {self.marketing_cvr_floor*100:.1f}%)."
                    ),
                    "symptom": f"Marketing campaign {cname} burned {spend:,.0f} VND with dismal CVR {cvr*100:.2f}%.",
                    "window_start": crow["start_time"],
                    "window_end": crow["end_time"],
                })
        return anomalies

    def scan_customer_product_health(self) -> List[Dict[str, Any]]:
        """Scans customer reviews for severe negative review surges on specific products."""
        anomalies = []
        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                COUNT(r.review_id) AS total_reviews,
                COUNT(CASE WHEN r.rating = 1 THEN 1 END) AS one_star_reviews,
                COUNT(CASE WHEN r.rating <= 2 THEN 1 END) AS negative_reviews,
                ROUND(AVG(r.rating)::NUMERIC, 2) AS avg_rating,
                ROUND(AVG(r.sentiment_score)::NUMERIC, 2) AS avg_sentiment,
                MIN(r.created_at) AS window_start,
                MAX(r.created_at) AS window_end
            FROM reviews r
            JOIN products p ON r.product_id = p.product_id
            GROUP BY p.product_id, p.product_name
            HAVING COUNT(CASE WHEN r.rating = 1 THEN 1 END) >= %s
            ORDER BY one_star_reviews DESC;
        """
        rows = execute_analyst_query(sql, (self.customer_one_star_min,))
        for r in rows:
            one_stars = int(r["one_star_reviews"] or 0)
            total = int(r["total_reviews"] or 0)
            avg_rate = float(r["avg_rating"] or 5.0)
            pname = r["product_name"]

            if one_stars >= self.customer_one_star_min and avg_rate <= 3.5:
                severity = "CRITICAL" if one_stars >= 15 or avg_rate <= 2.5 else "HIGH"
                anomalies.append({
                    "domain": "Customer",
                    "code": "ANOM_PRODUCT_DEFECT_CRISIS",
                    "severity": severity,
                    "entity_id": str(r["product_id"]),
                    "entity_name": pname,
                    "metric_name": "one_star_reviews_count",
                    "metric_value": one_stars,
                    "threshold": self.customer_one_star_min,
                    "unit": "đánh giá 1 sao",
                    "avg_rating": avg_rate,
                    "total_reviews": total,
                    "description": (
                        f"Phát hiện làn sóng khiếu nại chất lượng phần cứng tại sản phẩm '{pname}': "
                        f"Ghi nhận {one_stars}/{total} đánh giá 1 sao, điểm CSAT trung bình rớt thảm hại "
                        f"còn {avg_rate}/5.0 sao."
                    ),
                    "symptom": f"Product {pname} triggered an alarming wave of 1-star reviews ({one_stars} reviews), avg rating {avg_rate}/5.0.",
                    "window_start": r["window_start"],
                    "window_end": r["window_end"],
                })
        return anomalies

    def run_full_scan(self) -> Dict[str, Any]:
        """Runs an end-to-end pulse scan across all 5 operational enterprise domains."""
        scan_time = datetime.now()
        domain_anomalies: Dict[str, List[Dict[str, Any]]] = {
            "Payment": [],
            "Delivery": [],
            "Supply": [],
            "Marketing": [],
            "Customer": [],
        }

        try:
            domain_anomalies["Payment"] = self.scan_payment_health()
        except Exception as e:
            print(f"[Detector Warning] Payment health check error: {e}")

        try:
            domain_anomalies["Delivery"] = self.scan_logistics_health()
        except Exception as e:
            print(f"[Detector Warning] Logistics health check error: {e}")

        try:
            domain_anomalies["Supply"] = self.scan_supply_inventory_health()
        except Exception as e:
            print(f"[Detector Warning] Supply health check error: {e}")

        try:
            domain_anomalies["Marketing"] = self.scan_marketing_health()
        except Exception as e:
            print(f"[Detector Warning] Marketing health check error: {e}")

        try:
            domain_anomalies["Customer"] = self.scan_customer_product_health()
        except Exception as e:
            print(f"[Detector Warning] Customer/Product health check error: {e}")

        all_anomalies = []
        for domain, items in domain_anomalies.items():
            all_anomalies.extend(items)

        # Match with active incident observations in database
        observations = get_incident_observations()
        obs_by_domain = {o["affected_domain"]: o for o in observations}

        enriched_anomalies = []
        for anom in all_anomalies:
            d = anom["domain"]
            matched_obs = obs_by_domain.get(d)
            if matched_obs:
                anom["incident_id"] = str(matched_obs["incident_id"])
                anom["matched_observation"] = {
                    "incident_id": str(matched_obs["incident_id"]),
                    "affected_domain": matched_obs["affected_domain"],
                    "severity": matched_obs["severity"],
                    "status": matched_obs["status"],
                    "detected_at": matched_obs["detected_at"],
                    "start_time": matched_obs["start_time"],
                    "end_time": matched_obs["end_time"],
                    "surface_symptoms": matched_obs["surface_symptoms"],
                }
            else:
                fake_id = str(uuid.uuid4())
                anom["incident_id"] = fake_id
                anom["matched_observation"] = {
                    "incident_id": fake_id,
                    "affected_domain": d,
                    "severity": anom["severity"],
                    "status": "Investigating",
                    "detected_at": scan_time,
                    "start_time": anom.get("window_start") or (scan_time - timedelta(days=7)),
                    "end_time": anom.get("window_end") or scan_time,
                    "surface_symptoms": anom["symptom"],
                }
            enriched_anomalies.append(anom)

        is_healthy = len(enriched_anomalies) == 0
        return {
            "scan_timestamp": scan_time.isoformat(),
            "healthy": is_healthy,
            "total_anomalies": len(enriched_anomalies),
            "domains_scanned": list(domain_anomalies.keys()),
            "anomalies_detected": enriched_anomalies,
            "summary_by_domain": {d: len(items) for d, items in domain_anomalies.items()},
        }
