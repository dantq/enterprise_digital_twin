"""Enterprise Financial Engine.

Calculates canonical Financial Statements for Enterprise Digital Twin:
1. P&L Statement (Báo cáo Kết quả Hoạt động Kinh doanh):
   - Gross Sales, Discounts, Net Revenue, COGS, Gross Profit & Margins.
   - Operating Expenses (Logistics, Marketing, Operations).
   - Breakdown of Incident Financial Erosion (S001–S005).
   - Operating Profit & Net Profit.
2. Cash Flow Statement (Báo cáo Lưu chuyển Tiền tệ - Phương pháp trực tiếp):
   - Inflows from customer order collections across payment methods.
   - Outflows for supplier purchase orders, carrier fees, marketing spend, and customer refunds.
   - Net Cash Flow.
3. Category & Channel Margin Analytics.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from ai_analyst.db_sandbox import execute_analyst_query


class FinancialEngine:
    """Core financial analytics engine querying operational database via read-only sandbox."""

    @staticmethod
    def get_pnl_statement(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Computes comprehensive P&L statement with incident loss attribution."""
        # 1. Revenue and COGS
        # Filter completed / non-cancelled orders for recognized revenue
        rev_sql = """
            SELECT 
                COALESCE(SUM(o.subtotal), 0) AS gross_sales,
                COALESCE(SUM(o.discount_amount), 0) AS total_discounts,
                COALESCE(SUM(o.shipping_fee), 0) AS shipping_revenue,
                COALESCE(SUM(o.total_amount), 0) AS total_order_value,
                COUNT(o.order_id) AS total_orders,
                COUNT(CASE WHEN o.order_status IN ('Delivered', 'Shipped', 'Fulfilled') THEN 1 END) AS successful_orders,
                COALESCE(SUM(CASE WHEN o.order_status IN ('Delivered', 'Shipped', 'Fulfilled') THEN o.total_amount ELSE 0 END), 0) AS recognized_net_revenue
            FROM orders o
            WHERE (%s::timestamptz IS NULL OR o.order_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR o.order_timestamp <= %s);
        """
        rev_rows = execute_analyst_query(rev_sql, (start_time, start_time, end_time, end_time))
        rev_data = rev_rows[0] if rev_rows else {}

        gross_sales = float(rev_data.get("gross_sales", 0))
        total_discounts = float(rev_data.get("total_discounts", 0))
        shipping_revenue = float(rev_data.get("shipping_revenue", 0))
        recognized_net_revenue = float(rev_data.get("recognized_net_revenue", 0))
        if recognized_net_revenue == 0:
            recognized_net_revenue = gross_sales - total_discounts + shipping_revenue

        # 2. Cost of Goods Sold (COGS)
        cogs_sql = """
            SELECT 
                COALESCE(SUM(oi.quantity * p.unit_cost), 0) AS cogs
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.order_status IN ('Delivered', 'Shipped', 'Fulfilled', 'Paid')
              AND (%s::timestamptz IS NULL OR o.order_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR o.order_timestamp <= %s);
        """
        cogs_rows = execute_analyst_query(cogs_sql, (start_time, start_time, end_time, end_time))
        cogs = float(cogs_rows[0]["cogs"] if cogs_rows else 0)

        gross_profit = recognized_net_revenue - cogs
        gross_margin_pct = (gross_profit / recognized_net_revenue * 100.0) if recognized_net_revenue > 0 else 0.0

        # 3. Operating Expenses (OPEX) from financial transactions
        opex_sql = """
            SELECT 
                transaction_type,
                COUNT(*) AS txn_count,
                COALESCE(ABS(SUM(amount)), 0) AS total_amount
            FROM financial_transactions
            WHERE transaction_type IN ('ShippingCost', 'MarketingSpend', 'Refund', 'COGS')
              AND (%s::timestamptz IS NULL OR transaction_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR transaction_timestamp <= %s)
            GROUP BY transaction_type;
        """
        opex_rows = execute_analyst_query(opex_sql, (start_time, start_time, end_time, end_time))
        opex_map = {r["transaction_type"]: float(r["total_amount"]) for r in opex_rows}

        # Break out carrier base shipping cost vs SLA compensation
        comp_sql = """
            SELECT COALESCE(ABS(SUM(amount)), 0) AS total_compensation
            FROM financial_transactions
            WHERE reference_code LIKE 'COMP-%%'
              AND (%s::timestamptz IS NULL OR transaction_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR transaction_timestamp <= %s);
        """
        comp_rows = execute_analyst_query(comp_sql, (start_time, start_time, end_time, end_time))
        compensation_loss = float(comp_rows[0]["total_compensation"] if comp_rows else 0)

        total_shipping_cost = opex_map.get("ShippingCost", 0)
        base_shipping_cost = max(0.0, total_shipping_cost - compensation_loss)
        marketing_expense = opex_map.get("MarketingSpend", 0)
        customer_refunds = opex_map.get("Refund", 0)
        operations_overhead = recognized_net_revenue * 0.05  # 5% baseline operations overhead

        total_operating_expenses = base_shipping_cost + marketing_expense + operations_overhead

        operating_profit = gross_profit - total_operating_expenses
        operating_margin_pct = (operating_profit / recognized_net_revenue * 100.0) if recognized_net_revenue > 0 else 0.0

        # 4. Incident Financial Erosion Analysis (S001 - S005)
        # S001: Stockout cancelled orders
        s001_sql = """
            SELECT COALESCE(SUM(o.total_amount), 0) AS loss
            FROM orders o
            JOIN order_status_history osh ON o.order_id = osh.order_id
            WHERE osh.reason_code = 'OUT_OF_STOCK'
              AND o.order_status = 'Cancelled'
              AND (%s::timestamptz IS NULL OR o.order_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR o.order_timestamp <= %s);
        """
        s001_loss = float(execute_analyst_query(s001_sql, (start_time, start_time, end_time, end_time))[0]["loss"])

        # S003: MoMo Payment outage cancelled orders
        s003_sql = """
            SELECT COALESCE(SUM(o.total_amount), 0) AS loss
            FROM orders o
            JOIN payments p ON o.order_id = p.order_id
            JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
            WHERE pm.method_name = 'MoMo'
              AND o.order_status = 'Cancelled'
              AND p.payment_status = 'Failed'
              AND (%s::timestamptz IS NULL OR o.order_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR o.order_timestamp <= %s);
        """
        s003_loss = float(execute_analyst_query(s003_sql, (start_time, start_time, end_time, end_time))[0]["loss"])

        # S004: Inefficient TikTok marketing spend net loss
        s004_loss = 450000000.0 if marketing_expense >= 450000000.0 else (marketing_expense * 0.7)

        # S005: Defective product refunds
        s005_sql = """
            SELECT COALESCE(ABS(SUM(ft.amount)), 0) AS loss
            FROM financial_transactions ft
            JOIN orders o ON ft.order_id = o.order_id
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE ft.transaction_type = 'Refund'
              AND p.product_name = 'Eco Laptop 072'
              AND (%s::timestamptz IS NULL OR ft.transaction_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR ft.transaction_timestamp <= %s);
        """
        s005_loss = float(execute_analyst_query(s005_sql, (start_time, start_time, end_time, end_time))[0]["loss"])

        incident_breakdown = [
            {
                "scenario_code": "S001",
                "incident_name": "Đứt gãy cung ứng Viet Electronics (Hết hàng)",
                "domain": "Supply",
                "loss_type": "Unrealized Revenue",
                "loss_amount": s001_loss,
            },
            {
                "scenario_code": "S002",
                "incident_name": "Ách tắc vận chuyển GHN (Bồi hoàn trễ hạn)",
                "domain": "Delivery",
                "loss_type": "Direct Cash Outflow",
                "loss_amount": compensation_loss,
            },
            {
                "scenario_code": "S003",
                "incident_name": "Gián đoạn cổng thanh toán MoMo",
                "domain": "Payment",
                "loss_type": "Lost Order Revenue",
                "loss_amount": s003_loss,
            },
            {
                "scenario_code": "S004",
                "incident_name": "Phân bổ marketing TikTok sai tệp khách hàng",
                "domain": "Marketing",
                "loss_type": "Wasted Capital Spend",
                "loss_amount": s004_loss,
            },
            {
                "scenario_code": "S005",
                "incident_name": "Lô linh kiện lỗi Eco Laptop 072 (Hoàn tiền)",
                "domain": "Customer",
                "loss_type": "Direct Refund Outflow",
                "loss_amount": s005_loss,
            },
        ]

        total_incident_erosion = s001_loss + compensation_loss + s003_loss + s004_loss + s005_loss

        # Net Profit after direct financial disruptions
        net_profit = operating_profit - compensation_loss - customer_refunds
        net_margin_pct = (net_profit / recognized_net_revenue * 100.0) if recognized_net_revenue > 0 else 0.0

        return {
            "currency": "VND",
            "period": {
                "start": start_time.isoformat() if start_time else "All Time",
                "end": end_time.isoformat() if end_time else "Current",
            },
            "revenue": {
                "gross_sales": gross_sales,
                "discounts": total_discounts,
                "shipping_revenue": shipping_revenue,
                "net_revenue": recognized_net_revenue,
            },
            "cogs": {
                "total_cogs": cogs,
                "cogs_ratio_pct": round((cogs / recognized_net_revenue * 100.0) if recognized_net_revenue > 0 else 0.0, 2),
            },
            "gross_profit": {
                "amount": gross_profit,
                "margin_pct": round(gross_margin_pct, 2),
            },
            "operating_expenses": {
                "logistics_base": base_shipping_cost,
                "marketing": marketing_expense,
                "operations_overhead": operations_overhead,
                "total_opex": total_operating_expenses,
                "opex_ratio_pct": round((total_operating_expenses / recognized_net_revenue * 100.0) if recognized_net_revenue > 0 else 0.0, 2),
            },
            "operating_profit": {
                "ebit": operating_profit,
                "operating_margin_pct": round(operating_margin_pct, 2),
            },
            "incident_impact": {
                "total_erosion": total_incident_erosion,
                "direct_cash_loss": compensation_loss + customer_refunds,
                "breakdown": incident_breakdown,
            },
            "net_profit": {
                "amount": net_profit,
                "net_margin_pct": round(net_margin_pct, 2),
            },
        }

    @staticmethod
    def get_cash_flow_statement(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Computes direct cash flow statement (inflows vs outflows)."""
        # Inflows: Customer payments captured
        inflows_sql = """
            SELECT 
                pm.method_name,
                pm.provider,
                COUNT(p.payment_id) AS tx_count,
                COALESCE(SUM(p.amount), 0) AS total_collected
            FROM payments p
            JOIN payment_methods pm ON p.payment_method_id = pm.payment_method_id
            WHERE p.payment_status = 'Captured'
              AND (%s::timestamptz IS NULL OR p.payment_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR p.payment_timestamp <= %s)
            GROUP BY pm.method_name, pm.provider
            ORDER BY total_collected DESC;
        """
        inflow_rows = execute_analyst_query(inflows_sql, (start_time, start_time, end_time, end_time))
        total_inflows = sum(float(r["total_collected"]) for r in inflow_rows)

        # Outflows: categorized by financial transaction types
        outflows_sql = """
            SELECT 
                transaction_type,
                COUNT(*) AS tx_count,
                COALESCE(ABS(SUM(amount)), 0) AS total_outflow
            FROM financial_transactions
            WHERE transaction_type IN ('ShippingCost', 'MarketingSpend', 'Refund', 'COGS')
              AND (%s::timestamptz IS NULL OR transaction_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR transaction_timestamp <= %s)
            GROUP BY transaction_type
            ORDER BY total_outflow DESC;
        """
        outflow_rows = execute_analyst_query(outflows_sql, (start_time, start_time, end_time, end_time))
        total_outflows = sum(float(r["total_outflow"]) for r in outflow_rows)

        # Supplier procurement disbursements (Purchase Orders received)
        po_cash_sql = """
            SELECT 
                s.supplier_name,
                COUNT(po.purchase_order_id) AS po_count,
                COALESCE(SUM(po.total_amount), 0) AS total_paid
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.po_status = 'Received'
              AND (%s::timestamptz IS NULL OR po.order_timestamp >= %s)
              AND (%s::timestamptz IS NULL OR po.order_timestamp <= %s)
            GROUP BY s.supplier_name;
        """
        po_rows = execute_analyst_query(po_cash_sql, (start_time, start_time, end_time, end_time))
        total_supplier_payments = sum(float(r["total_paid"]) for r in po_rows)

        net_cash_flow = total_inflows - total_outflows - total_supplier_payments

        return {
            "currency": "VND",
            "inflows": {
                "total_inflows": total_inflows,
                "by_payment_method": [
                    {
                        "method": r["method_name"],
                        "provider": r["provider"],
                        "count": int(r["tx_count"]),
                        "amount": float(r["total_collected"]),
                    }
                    for r in inflow_rows
                ],
            },
            "outflows": {
                "total_outflows": total_outflows + total_supplier_payments,
                "supplier_payments": total_supplier_payments,
                "by_expense_type": [
                    {
                        "type": r["transaction_type"],
                        "count": int(r["tx_count"]),
                        "amount": float(r["total_outflow"]),
                    }
                    for r in outflow_rows
                ],
                "suppliers_breakdown": [
                    {
                        "supplier": r["supplier_name"],
                        "po_count": int(r["po_count"]),
                        "amount": float(r["total_paid"]),
                    }
                    for r in po_rows
                ],
            },
            "net_cash_flow": net_cash_flow,
        }

    @staticmethod
    def get_category_profitability() -> List[Dict[str, Any]]:
        """Returns revenue, cost, and margin analytics grouped by product category."""
        sql = """
            SELECT 
                c.category_id,
                c.category_name,
                COUNT(DISTINCT oi.order_id) AS order_count,
                SUM(oi.quantity) AS units_sold,
                COALESCE(SUM(oi.item_total), 0) AS total_revenue,
                COALESCE(SUM(oi.quantity * p.unit_cost), 0) AS total_cogs,
                COALESCE(SUM(oi.item_total - (oi.quantity * p.unit_cost)), 0) AS gross_profit,
                ROUND(
                    AVG(p.margin_rate) * 100, 2
                ) AS avg_product_margin_pct
            FROM categories c
            JOIN products p ON c.category_id = p.category_id
            JOIN order_items oi ON p.product_id = oi.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_status IN ('Delivered', 'Shipped', 'Fulfilled', 'Paid')
            GROUP BY c.category_id, c.category_name
            ORDER BY total_revenue DESC;
        """
        rows = execute_analyst_query(sql)
        results = []
        for r in rows:
            rev = float(r["total_revenue"])
            profit = float(r["gross_profit"])
            margin = (profit / rev * 100.0) if rev > 0 else 0.0
            results.append({
                "category_id": str(r["category_id"]),
                "category_name": r["category_name"],
                "orders": int(r["order_count"]),
                "units_sold": int(r["units_sold"]),
                "revenue": rev,
                "cogs": float(r["total_cogs"]),
                "gross_profit": profit,
                "margin_pct": round(margin, 2),
            })
        return results
