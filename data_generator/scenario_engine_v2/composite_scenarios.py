"""Composite Scenarios Orchestrator for Scenario Engine V2.

Implements:
1. S006 — Cú sốc Kép (The Perfect Storm):
   - Concurrency: S001 (Viet Electronics Supplier Delay) + S003 (MoMo Payment Outage)
2. S007 — Xung đột Vận chuyển & Khiếu nại Chất lượng (Logistics & Quality Clash):
   - Concurrency: S002 (GHN Overload & Delay) + S005 (Eco Laptop 072 Hardware Defect)
3. Noise injection and marginal financial attribution.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from data_generator.scenario_engine_v2.temporal_curves import (
    TemporalCurveEngine,
    CrisisPhase,
    CurveProfile,
)
from data_generator.scenario_engine_v2.business_noise import (
    BusinessNoiseEngine,
    NoiseProfile,
)
from data_generator.scenario_engine_v2.causal_ground_truth_v2 import (
    CompositeCausalGraph,
    MarginalAttributionResult,
)

COMPOSITE_CATALOG = {
    "S006": {
        "scenario_id": "S006",
        "title": "Cú sốc Kép: Đứt gãy Cung ứng & Sập Cổng Thanh toán",
        "name_en": "The Perfect Storm: Supplier Disruption & Payment Outage",
        "primary_sub_scenarios": ["S001", "S003"],
        "affected_domains": ["Procurement", "Inventory", "Payment", "Sales", "Finance"],
        "concurrency_level": "DUAL_SIMULTANEOUS",
        "target_entities": {
            "supplier": "Viet Electronics",
            "warehouse": "Kho TP Hồ Chí Minh",
            "payment_gateway": "MoMo",
        },
        "ground_truth_losses": {
            "S001_Supplier_Disruption": 1077000000.0,
            "S003_Payment_Degradation": 703000000.0,
        },
        "interaction_offset_rate": 0.045,  # 4.5% interaction deduction
        "surface_symptoms": (
            "Hệ thống giám sát vận hành ghi nhận tình trạng bất thường kép trong tháng 08/2026: "
            "Tồn kho máy tính tại Kho TP.HCM cạn kiệt dẫn đến gia tăng đơn hàng bị hủy do hết hàng, "
            "đồng thời tỷ lệ giao dịch thanh toán trực tuyến qua ví điện tử MoMo sụt giảm nghiêm trọng, "
            "tạo ra lượng lớn khiếu nại song song từ khách hàng."
        ),
    },
    "S007": {
        "scenario_id": "S007",
        "title": "Xung đột Vận chuyển & Khiếu nại Chất lượng Phần cứng",
        "name_en": "Logistics Bottleneck & Hardware Quality Crisis",
        "primary_sub_scenarios": ["S002", "S005"],
        "affected_domains": ["Logistics", "Customer Service", "Product", "Finance"],
        "concurrency_level": "DUAL_SIMULTANEOUS",
        "target_entities": {
            "carrier": "GHN",
            "product": "Eco Laptop 072",
        },
        "ground_truth_losses": {
            "S002_Logistics_Disruption": 185000000.0,
            "S005_Quality_Degradation": 425000000.0,
        },
        "interaction_offset_rate": 0.035,
        "surface_symptoms": (
            "Báo cáo trải nghiệm khách hàng ghi nhận làn sóng bất mãn tăng vọt cục bộ: "
            "Tỷ lệ giao hàng trễ của đơn vị vận chuyển GHN tăng lên mức báo động (trên 38%), "
            "kèm theo số lượng yêu cầu hoàn trả và đánh giá 1 sao đối với sản phẩm 'Eco Laptop 072' tăng đột biến, "
            "làm sụt giảm điểm CSAT toàn hệ thống từ 4.45 xuống dưới 3.15."
        ),
    },
}


class CompositeScenarioOrchestrator:
    """Orchestrates simulation, temporal evaluation, noise generation, and DAG ground truth."""

    def __init__(
        self,
        noise_profile: Optional[NoiseProfile] = None,
        curve_type: CurveProfile = CurveProfile.MULTI_PHASE_PIECEWISE,
    ):
        self.noise_engine = BusinessNoiseEngine(noise_profile or NoiseProfile())
        self.curve_engine = TemporalCurveEngine(curve_type=curve_type)

    def get_scenario_catalog(self) -> List[Dict[str, Any]]:
        """Returns metadata for all V2 scenarios."""
        return list(COMPOSITE_CATALOG.values())

    def build_causal_dag_s006(self) -> CompositeCausalGraph:
        """Constructs full multi-root DAG for S006 with Collider node."""
        dag = CompositeCausalGraph(scenario_id="S006", title=COMPOSITE_CATALOG["S006"]["title"])

        # Branch 1: Supply Chain
        dag.add_node("RC_SUPPLY", "Gián đoạn Viet Electronics", "Procurement", "RootCause", "NCC giao trễ PO máy tính")
        dag.add_node("MECH_PO_DELAY", "Chậm nhập kho TP.HCM", "Procurement", "Mechanism", "PO trễ dẫn đến không có hàng nhập")
        dag.add_node("IMP_STOCKOUT", "Tồn kho cạn kiệt", "Inventory", "OperationalImpact", "Tồn kho Eco Laptop = 0")
        dag.add_node("IMP_CANCEL", "Đơn hàng bị hủy", "Sales", "OperationalImpact", "Khách hàng bị hủy đơn do hết hàng")

        # Branch 2: Payment
        dag.add_node("RC_PAYMENT", "Sự cố Cổng MoMo", "Payment", "RootCause", "Gateway MoMo phản hồi timeout")
        dag.add_node("MECH_FAIL_RATE", "Tỷ lệ lỗi > 35%", "Payment", "Mechanism", "Giao dịch thanh toán thất bại tăng vọt")
        dag.add_node("IMP_ABANDON", "Từ bỏ giỏ hàng", "Customer", "OperationalImpact", "Khách hàng bỏ dở quá trình thanh toán")

        # Collider Node
        dag.add_node("COLLIDER_REVENUE", "Doanh thu sụt giảm & Thiệt hại kép", "Finance", "Collider", "Tác động cộng hưởng lên P&L")

        # Edges Branch 1
        dag.add_edge("RC_SUPPLY", "MECH_PO_DELAY", weight=1.0, description="NCC trễ làm chậm nhập kho")
        dag.add_edge("MECH_PO_DELAY", "IMP_STOCKOUT", weight=0.95, description="Không nhập được hàng làm cạn kho")
        dag.add_edge("IMP_STOCKOUT", "IMP_CANCEL", weight=0.90, description="Hết hàng dẫn đến hủy đơn")
        dag.add_edge("IMP_CANCEL", "COLLIDER_REVENUE", weight=0.605, description="Hủy đơn làm mất doanh thu")

        # Edges Branch 2
        dag.add_edge("RC_PAYMENT", "MECH_FAIL_RATE", weight=1.0, description="Lỗi cổng làm tăng tỷ lệ thất bại")
        dag.add_edge("MECH_FAIL_RATE", "IMP_ABANDON", weight=0.85, description="Lỗi thanh toán làm khách bỏ giỏ")
        dag.add_edge("IMP_ABANDON", "COLLIDER_REVENUE", weight=0.395, description="Bỏ giỏ hàng làm mất doanh thu")

        return dag

    def build_causal_dag_s007(self) -> CompositeCausalGraph:
        """Constructs full multi-root DAG for S007 with Collider node."""
        dag = CompositeCausalGraph(scenario_id="S007", title=COMPOSITE_CATALOG["S007"]["title"])

        # Branch 1: Logistics
        dag.add_node("RC_LOGISTICS", "Đình công & Quá tải GHN", "Logistics", "RootCause", "Kho phân loại GHN tắc nghẽn")
        dag.add_node("MECH_DELIVERY_DELAY", "Thời gian giao tăng 7.5 ngày", "Logistics", "Mechanism", "Tỷ lệ giao trễ vượt 38%")
        dag.add_node("IMP_LATE_COMPLAINTS", "Khiếu nại giao trễ", "Customer Service", "OperationalImpact", "Khách hàng giục đơn và đòi bồi hoàn")

        # Branch 2: Quality
        dag.add_node("RC_QUALITY", "Lỗi linh kiện Eco Laptop 072", "Product", "RootCause", "Pin và cáp màn hình lỗi từ nhà máy")
        dag.add_node("MECH_DEFECT_RATE", "Tỷ lệ hỏng hóc tăng", "Product", "Mechanism", "Khách phản ánh máy không lên nguồn")
        dag.add_node("IMP_RETURNS", "Yêu cầu đổi trả tăng vọt", "Customer Service", "OperationalImpact", "Yêu cầu RMA và hoàn tiền tăng gấp 4 lần")

        # Collider Node
        dag.add_node("COLLIDER_CHURN", "Bùng nổ 1 Sao & Khách hàng rời bỏ", "Customer", "Collider", "Uy tín sụt giảm và bồi hoàn tài chính")

        # Edges
        dag.add_edge("RC_LOGISTICS", "MECH_DELIVERY_DELAY", weight=1.0)
        dag.add_edge("MECH_DELIVERY_DELAY", "IMP_LATE_COMPLAINTS", weight=0.88)
        dag.add_edge("IMP_LATE_COMPLAINTS", "COLLIDER_CHURN", weight=0.303)

        dag.add_edge("RC_QUALITY", "MECH_DEFECT_RATE", weight=1.0)
        dag.add_edge("MECH_DEFECT_RATE", "IMP_RETURNS", weight=0.92)
        dag.add_edge("IMP_RETURNS", "COLLIDER_CHURN", weight=0.697)

        return dag

    def run_simulation(
        self,
        scenario_id: str,
        progress_t: float = 0.65,
        apply_noise: bool = True,
    ) -> Dict[str, Any]:
        """Runs a simulated observation of a composite scenario at normalized time progress_t."""
        if scenario_id not in COMPOSITE_CATALOG:
            raise ValueError(f"Unknown scenario_id: {scenario_id}. Available: {list(COMPOSITE_CATALOG.keys())}")

        meta = COMPOSITE_CATALOG[scenario_id]
        curve_eval = self.curve_engine.evaluate_normalized(progress_t)
        effective_sev = curve_eval["effective_severity"]

        # Build DAG
        dag = self.build_causal_dag_s006() if scenario_id == "S006" else self.build_causal_dag_s007()
        attribution = dag.calculate_marginal_attribution(
            primary_losses=meta["ground_truth_losses"],
            interaction_rate=meta["interaction_offset_rate"],
        )

        # Scale loss by active temporal severity
        scaled_loss = round(attribution.total_financial_loss * effective_sev, 2)
        if apply_noise:
            scaled_loss = self.noise_engine.apply_metric_jitter(scaled_loss, "financial_loss")

        return {
            "status": "SUCCESS",
            "scenario_id": scenario_id,
            "title": meta["title"],
            "temporal_state": curve_eval,
            "surface_observation": {
                "detected_severity": "CRITICAL" if effective_sev >= 0.75 else ("HIGH" if effective_sev >= 0.40 else "MEDIUM"),
                "affected_domains": meta["affected_domains"],
                "surface_symptoms": meta["surface_symptoms"],
                "estimated_current_loss_vnd": scaled_loss,
                "concurrency_level": meta["concurrency_level"],
            },
            "ground_truth_hidden": {
                "total_expected_loss_vnd": attribution.total_financial_loss,
                "interaction_offset_vnd": attribution.interaction_offset,
                "causes": attribution.causes,
                "attribution_shares": attribution.attribution_shares,
                "causal_dag": dag.to_dict(),
            },
        }
