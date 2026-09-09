"""Causal Ground Truth V2: Composite Directed Acyclic Graphs & Marginal Attribution.

Supports:
1. Multi-Root Causal DAGs with multiple independent trigger events.
2. Interaction Collider Nodes where multiple paths converge on financial outcomes.
3. Quantified Marginal Attribution Weights (Marginal Contribution %).
4. Strict topological cycle detection (Acyclicity verification).
"""

from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field


class CausalNodeV2(BaseModel):
    node_id: str
    label: str
    domain: str
    node_type: str  # RootCause, Mechanism, OperationalImpact, Outcome, Collider
    description: str


class CausalEdgeV2(BaseModel):
    source_id: str
    target_id: str
    weight: float = 1.0  # Marginal weight / strength
    description: str


class MarginalAttributionResult(BaseModel):
    scenario_id: str
    total_financial_loss: float
    causes: List[Dict[str, Any]]
    interaction_offset: float
    attribution_shares: Dict[str, float]  # cause_id -> percentage (0.0 to 1.0)


class CompositeCausalGraph:
    """Manages multi-incident causal DAG and computes marginal attribution."""

    def __init__(self, scenario_id: str, title: str):
        self.scenario_id = scenario_id
        self.title = title
        self.nodes: Dict[str, CausalNodeV2] = {}
        self.edges: List[CausalEdgeV2] = []

    def add_node(
        self,
        node_id: str,
        label: str,
        domain: str,
        node_type: str,
        description: str,
    ) -> CausalNodeV2:
        node = CausalNodeV2(
            node_id=node_id,
            label=label,
            domain=domain,
            node_type=node_type,
            description=description,
        )
        self.nodes[node_id] = node
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        weight: float = 1.0,
        description: str = "",
    ):
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Invalid edge: {source_id} -> {target_id}. Nodes must exist.")
        self.edges.append(
            CausalEdgeV2(
                source_id=source_id,
                target_id=target_id,
                weight=weight,
                description=description,
            )
        )

    def verify_acyclicity(self) -> bool:
        """Verifies using Kahn's algorithm that the graph contains zero directed cycles."""
        adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}

        for edge in self.edges:
            adj[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count == len(self.nodes)

    def calculate_marginal_attribution(
        self,
        primary_losses: Dict[str, float],
        interaction_rate: float = 0.05,
    ) -> MarginalAttributionResult:
        """Calculates marginal attribution preventing double-counting.

        L_total = sum(L_i) - L_interaction
        """
        raw_sum = sum(primary_losses.values())
        interaction_offset = raw_sum * interaction_rate
        total_loss = max(0.0, raw_sum - interaction_offset)

        shares: Dict[str, float] = {}
        for cause_id, loss in primary_losses.items():
            shares[cause_id] = round((loss / max(raw_sum, 1e-6)), 4)

        causes_list = [
            {
                "cause_id": cid,
                "gross_loss": val,
                "share_pct": round(shares[cid] * 100.0, 2),
            }
            for cid, val in primary_losses.items()
        ]

        return MarginalAttributionResult(
            scenario_id=self.scenario_id,
            total_financial_loss=round(total_loss, 2),
            causes=causes_list,
            interaction_offset=round(interaction_offset, 2),
            attribution_shares=shares,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "is_acyclic": self.verify_acyclicity(),
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "edges": [e.model_dump() for e in self.edges],
        }
