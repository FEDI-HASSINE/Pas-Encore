from abc import ABC, abstractmethod


class AllocationStrategy(ABC):
    """
    Interface commune pour toutes les stratégies d'allocation.
    """

    @abstractmethod
    def allocate(self, task, current_time):
        """
        Choisit le nœud sur lequel exécuter une tâche.

        Args:
            task: tâche à allouer
            current_time: temps courant de la simulation SimPy

        Returns:
            Le nœud choisi pour exécuter la tâche.
        """
        pass