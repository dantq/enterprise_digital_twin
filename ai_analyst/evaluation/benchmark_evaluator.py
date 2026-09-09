"""Ground Truth Benchmark Evaluation Engine.

Evaluates an AI Analyst RCA report against restricted Ground Truth
stored in Layer 7 tables (`benchmark_cases`, `evaluation_targets`).

Evaluation Dimensions:
1. Root Cause Precision (Weight: 30%): Primary cause and domain identification.
2. Causal Path Accuracy (Weight: 25%): Strict sequence of nodes and DAG edges.
3. Affected Entity Match (Weight: 15%): Entity ID and type exactness.
4. Outcome Financial Estimation (Weight: 15%): Loss accuracy within specified tolerance.
5. Recommended Actions Relevance (Weight: 15%): Mitigations and preventative policies.
"""

from typing import Any, Dict, List, Optional
from ai_analyst.db_sandbox import get_evaluator_connection


class BenchmarkEvaluator:
    """Evaluates RCA reports against Ground Truth targets using administrative privileges."""

    def __init__(self, name: str = "BenchmarkEvaluator"):
        self.name = name

    def evaluate_rca(self, rca_report: Dict[str, Any]) -> Dict[str, Any]:
        """Runs rubric scoring against evaluation_targets for the incident's benchmark case."""
        incident_id = rca_report.get("incident_id")

        with get_evaluator_connection() as conn:
            with conn.cursor() as cur:
                # 1. Fetch benchmark case
                cur.execute("""
                    SELECT benchmark_case_id, case_name, split, observation_cutoff_time
                    FROM benchmark_cases
                    WHERE incident_id = %s
                """, (incident_id,))
                case_row = cur.fetchone()

                if not case_row:
                    return {
                        "status": "ERROR",
                        "error": f"No benchmark_case registered for incident_id: {incident_id}",
                    }

                benchmark_case_id = case_row["benchmark_case_id"]

                # 2. Fetch evaluation targets
                cur.execute("""
                    SELECT evaluation_target_id, target_type, target_value, scoring_weight
                    FROM evaluation_targets
                    WHERE benchmark_case_id = %s
                    ORDER BY scoring_weight DESC;
                """, (benchmark_case_id,))
                targets = cur.fetchall()

        total_score = 0.0
        max_score = 0.0
        target_results: List[Dict[str, Any]] = []

        for target in targets:
            ttype = target["target_type"]
            tval = target["target_value"]
            weight = float(target["scoring_weight"])
            max_score += weight * 100.0

            earned_pct, status, rationale = self._score_target(ttype, tval, rca_report)
            earned_points = earned_pct * weight * 100.0
            total_score += earned_points

            target_results.append({
                "target_type": ttype,
                "weight": weight,
                "earned_points": round(earned_points, 2),
                "max_points": round(weight * 100.0, 2),
                "status": status,
                "rationale": rationale,
            })

        # Calculate final percentage
        final_pct = (total_score / max_score * 100.0) if max_score > 0 else 0.0

        if final_pct >= 90.0:
            grade = "EXCELLENT"
        elif final_pct >= 75.0:
            grade = "GOOD"
        elif final_pct >= 60.0:
            grade = "FAIR"
        else:
            grade = "FAIL"

        return {
            "evaluator": self.name,
            "benchmark_case_id": str(benchmark_case_id),
            "case_name": case_row["case_name"],
            "split": case_row["split"],
            "total_score": round(final_pct, 2),
            "grade": grade,
            "target_results": target_results,
        }

    def _score_target(
        self,
        target_type: str,
        target_value: Dict[str, Any],
        rca: Dict[str, Any],
    ) -> tuple[float, str, str]:
        """Scores an individual evaluation target against the RCA output."""
        if target_type == "RootCause":
            expected_cause = target_value.get("primary_root_cause")
            expected_domain = target_value.get("domain")
            actual_cause = rca.get("primary_root_cause")
            actual_domain = rca.get("domain")

            match_cause = (actual_cause == expected_cause)
            match_domain = (actual_domain == expected_domain) or (actual_domain in ("Delivery", "Logistics") and expected_domain in ("Delivery", "Logistics"))

            if match_cause and match_domain:
                return (
                    1.0,
                    "PASSED",
                    f"Xác định chính xác 100% Nguyên nhân gốc '{actual_cause}' và Miền '{actual_domain}'."
                )
            elif match_domain:
                return (
                    0.5,
                    "PARTIAL",
                    f"Xác định đúng miền '{actual_domain}' nhưng nguyên nhân gốc lệch ('{actual_cause}' vs kỳ vọng '{expected_cause}')."
                )
            else:
                return (
                    0.0,
                    "FAILED",
                    f"Không khớp nguyên nhân gốc. Thực tế: '{actual_cause}', Kỳ vọng: '{expected_cause}'."
                )

        elif target_type == "CausalPath":
            expected_seq = target_value.get("causal_sequence", [])
            actual_seq = rca.get("causal_path", {}).get("causal_sequence", [])

            # Measure edge intersection
            exp_set = {f"{u}->{v}" for u, v in expected_seq}
            act_set = {f"{u}->{v}" for u, v in actual_seq}

            if not exp_set:
                return 1.0, "PASSED", "Không có ràng buộc chuỗi."

            matched_edges = exp_set.intersection(act_set)
            edge_recall = len(matched_edges) / len(exp_set)

            if edge_recall >= 1.0:
                return (
                    1.0,
                    "PASSED",
                    f"Chuỗi DAG nhân quả khớp tuyệt đối ({len(matched_edges)}/{len(exp_set)} cạnh đúng)."
                )
            elif edge_recall >= 0.60:
                return (
                    edge_recall,
                    "PARTIAL",
                    f"Chuỗi nhân quả khớp một phần ({len(matched_edges)}/{len(exp_set)} cạnh)."
                )
            else:
                return (
                    edge_recall,
                    "FAILED",
                    f"Chuỗi nhân quả lệch nhiều so với chuẩn ({len(matched_edges)}/{len(exp_set)} cạnh)."
                )

        elif target_type == "AffectedEntity":
            expected_id = str(target_value.get("entity_id"))
            expected_name = target_value.get("entity_name")
            actual_entity = rca.get("affected_entity") or {}
            actual_id = str(actual_entity.get("entity_id"))
            actual_name = actual_entity.get("entity_name")

            if actual_id == expected_id or (actual_name and expected_name and actual_name.lower() == expected_name.lower()):
                return (
                    1.0,
                    "PASSED",
                    f"Xác định chính xác thực thể nguồn: '{actual_name}' (ID: {actual_id})."
                )
            else:
                return (
                    0.0,
                    "FAILED",
                    f"Không nhận diện đúng thực thể. Thực tế: '{actual_name}', Kỳ vọng: '{expected_name}'."
                )

        elif target_type == "Outcome":
            expected_val = float(target_value.get("expected_value", 0))
            tolerance = float(target_value.get("tolerance_percent", 0.20))
            actual_val = float(rca.get("outcome", {}).get("value", 0))

            if expected_val <= 0:
                return 1.0, "PASSED", "Không có giá trị kỳ vọng."

            error = abs(actual_val - expected_val) / expected_val

            if error <= tolerance:
                return (
                    1.0,
                    "PASSED",
                    f"Định lượng tổn thất chính xác trong ngưỡng dung sai: {actual_val:,.2f} VND (Sai số: {error*100:.2f}% <= {tolerance*100:.0f}%)."
                )
            elif error <= (tolerance * 2):
                return (
                    0.5,
                    "PARTIAL",
                    f"Định lượng tổn thất sai lệch nhẹ: {actual_val:,.2f} VND (Sai số: {error*100:.2f}%)."
                )
            else:
                return (
                    0.0,
                    "FAILED",
                    f"Định lượng tổn thất vượt dung sai: Thực tế {actual_val:,.2f} VND vs Kỳ vọng {expected_val:,.2f} VND."
                )

        elif target_type == "RecommendedAction":
            expected_actions = target_value.get("recommended_actions", [])
            actual_actions = rca.get("recommended_actions", [])

            if not expected_actions or not actual_actions:
                return 0.5, "PARTIAL", "Đề xuất hành động cơ bản."

            # Calculate keyword semantic overlap
            hit_count = 0
            for exp in expected_actions:
                exp_words = set(exp.lower().split())
                for act in actual_actions:
                    act_words = set(act.lower().split())
                    overlap = len(exp_words.intersection(act_words))
                    if overlap >= 3:
                        hit_count += 1
                        break

            action_pct = min(1.0, hit_count / max(1, len(expected_actions)))
            if action_pct >= 0.75:
                return (
                    1.0,
                    "PASSED",
                    f"Đề xuất hành động hoàn chỉnh và bám sát thực tiễn ({hit_count}/{len(expected_actions)} danh mục giải pháp trọng yếu)."
                )
            elif action_pct >= 0.50:
                return (
                    0.75,
                    "PARTIAL",
                    f"Đề xuất hành động đáp ứng phần lớn ({hit_count}/{len(expected_actions)} giải pháp)."
                )
            else:
                return (
                    action_pct,
                    "FAILED",
                    "Đề xuất hành động chưa bao phủ các khâu trọng yếu."
                )

        return 0.5, "PARTIAL", f"Loại mục tiêu '{target_type}' được đánh giá mặc định."
