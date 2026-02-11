import fnmatch
from dataclasses import dataclass
from typing import List, Optional

from src.core.domain.entity import AIHuman
from src.core.domain.strategic_context import StrategicContext
from src.hierarchy.domain.hierarchy_models import HierarchyDirective, HierarchyGraph, HierarchyLevel
from src.hierarchy.services.hierarchy_config_loader import HierarchyConfigLoader
from src.hierarchy.store.postgres_hierarchy_override_store import PostgresHierarchyOverrideStore


@dataclass(frozen=True)
class EffectiveHierarchyView:
    directives: List[HierarchyDirective]

    def by_level(self, level: HierarchyLevel) -> List[HierarchyDirective]:
        return [d for d in self.directives if d.level == level]


class HierarchyProjectionService:
    """
    Builds effective hierarchy directives from config + runtime overrides.
    """

    def __init__(
        self,
        config_loader: Optional[HierarchyConfigLoader] = None,
        override_store: Optional[PostgresHierarchyOverrideStore] = None,
    ):
        self.config_loader = config_loader or HierarchyConfigLoader()
        self.override_store = override_store

    def build_graph(self) -> HierarchyGraph:
        base_graph = self.config_loader.load()
        if not self.override_store:
            return base_graph
        merged = list(base_graph.directives) + self.override_store.list_active()
        return HierarchyGraph(nodes=base_graph.nodes, edges=base_graph.edges, directives=merged)

    def resolve_for_context(
        self,
        context: StrategicContext,
        human: Optional[AIHuman] = None,
    ) -> EffectiveHierarchyView:
        graph = self.build_graph()
        scope_keys = self._scope_keys(context, human)
        matched = [d for d in graph.directives if self._matches(d.target, scope_keys)]
        matched.sort(key=lambda x: self._precedence_rank(x.level))
        return EffectiveHierarchyView(directives=matched)

    def _scope_keys(self, context: StrategicContext, human: Optional[AIHuman]) -> List[str]:
        keys = [
            "*",
            f"country:{context.country}",
            f"region:{context.region or '*'}",
            f"domain:{context.domain}",
            context.domain,
        ]
        if human:
            keys.append(f"human:{human.id}")
        if ":" in context.domain:
            platform = context.domain.split(":", 1)[0]
            keys.append(f"platform:{platform}")
            keys.append(f"{platform}:*")
        return keys

    def _matches(self, pattern: str, scope_keys: List[str]) -> bool:
        for key in scope_keys:
            if fnmatch.fnmatch(key, pattern):
                return True
        return False

    def _precedence_rank(self, level: HierarchyLevel) -> int:
        if level == HierarchyLevel.L0:
            return 0
        if level == HierarchyLevel.L1:
            return 1
        return 2

