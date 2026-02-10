import json
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from dataclasses import asdict

from src.core.domain.budget_snapshot import BudgetSnapshot
from src.core.domain.resource import StrategicResourceBudget


class BudgetPersistenceBackend(ABC):
    """
    Interface for persisting and retrieving the global resource budget.
    """

    @abstractmethod
    def load(self) -> Optional[BudgetSnapshot]:
        pass

    @abstractmethod
    def save(self, snapshot: BudgetSnapshot) -> None:
        pass


class InMemoryBudgetBackend(BudgetPersistenceBackend):
    def __init__(self):
        self._snapshot: Optional[BudgetSnapshot] = None

    def load(self) -> Optional[BudgetSnapshot]:
        return self._snapshot

    def save(self, snapshot: BudgetSnapshot) -> None:
        self._snapshot = snapshot


class FileBudgetBackend(BudgetPersistenceBackend):
    def __init__(self, file_path: str):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    def load(self) -> Optional[BudgetSnapshot]:
        if not os.path.exists(self.file_path):
            return None

        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)

            budget_data = data['budget']
            budget = StrategicResourceBudget(
                energy_budget=budget_data['energy_budget'],
                attention_budget=budget_data['attention_budget'],
                execution_slots=budget_data['execution_slots'],
                last_updated=datetime.fromisoformat(budget_data['last_updated']),
                energy_recovery_rate=budget_data['energy_recovery_rate'],
                attention_recovery_rate=budget_data['attention_recovery_rate'],
                slot_recovery_rate=budget_data['slot_recovery_rate']
            )

            return BudgetSnapshot(
                budget=budget,
                timestamp=datetime.fromisoformat(data['timestamp']),
                version=data.get('version', "1.0")
            )
        except Exception as e:
            print(f"Error loading budget: {e}")
            return None

    def save(self, snapshot: BudgetSnapshot) -> None:
        data = {
            "budget": asdict(snapshot.budget),
            "timestamp": snapshot.timestamp.isoformat(),
            "version": snapshot.version
        }
        # Handle datetime serialization inside asdict result if needed,
        # but asdict keeps datetime objects. We need to serialize them.
        data["budget"]["last_updated"] = snapshot.budget.last_updated.isoformat()

        dir_name = os.path.dirname(self.file_path)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_name = tmp_file.name

        os.replace(tmp_name, self.file_path)