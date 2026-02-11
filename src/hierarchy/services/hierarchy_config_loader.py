import json
from pathlib import Path
from typing import Any, Dict, List

from src.hierarchy.domain.hierarchy_models import (
    HierarchyDirective,
    HierarchyEdge,
    HierarchyGraph,
    HierarchyLevel,
    HierarchyNode,
    directive_from_payload,
)


class HierarchyConfigLoader:
    """
    Loads hierarchy bootstrap config from disk.
    """

    def __init__(self, config_path: str = "config/hierarchy.json"):
        self.config_path = Path(config_path)

    def load(self) -> HierarchyGraph:
        if not self.config_path.exists():
            return HierarchyGraph.default()
        payload = self._read_json()
        return self._parse(payload)

    def _read_json(self) -> Dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _parse(self, payload: Dict[str, Any]) -> HierarchyGraph:
        node_rows = payload.get("nodes", [])
        edge_rows = payload.get("edges", [])
        directive_rows = payload.get("directives", [])

        nodes: List[HierarchyNode] = []
        edges: List[HierarchyEdge] = []
        directives: List[HierarchyDirective] = []

        for row in node_rows:
            raw_level = str(row.get("level", "L0")).upper()
            try:
                level = HierarchyLevel(raw_level)
            except Exception:
                level = HierarchyLevel.L0
            nodes.append(
                HierarchyNode(
                    id=str(row.get("id")),
                    level=level,
                    name=str(row.get("name", row.get("id", "node"))),
                    parent_id=row.get("parent_id"),
                    metadata=dict(row.get("metadata") or {}),
                )
            )

        for row in edge_rows:
            parent_id = row.get("parent_id")
            child_id = row.get("child_id")
            if not parent_id or not child_id:
                continue
            edges.append(HierarchyEdge(parent_id=str(parent_id), child_id=str(child_id)))

        for row in directive_rows:
            directives.append(directive_from_payload(dict(row)))

        if not nodes:
            nodes = [HierarchyNode(id="global", level=HierarchyLevel.L0, name="Global")]

        return HierarchyGraph(nodes=nodes, edges=edges, directives=directives)

