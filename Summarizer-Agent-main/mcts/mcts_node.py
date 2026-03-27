import math
from typing import List, Optional

class MCTSNode:
    """Node in the Monte Carlo Tree Search"""

    def __init__(self, agent_id: Optional[int] = None, parent: Optional['MCTSNode'] = None):
        self.agent_id = agent_id  # Which agent this node represents
        self.parent = parent
        self.children: List['MCTSNode'] = []
        self.visits = 0
        self.total_value = 0.0  # Cumulative reward
        self.untried_agents: List[int] = []  # Agents not yet expanded

    @property
    def value(self) -> float:
        """Average value of this node"""
        return self.total_value / self.visits if self.visits > 0 else 0.0

    def is_fully_expanded(self) -> bool:
        """Check if all possible agents have been tried"""
        return len(self.untried_agents) == 0 and len(self.children) > 0

    def is_leaf(self) -> bool:
        """Check if this is a leaf node"""
        return len(self.children) == 0

    def best_child(self, exploration_weight: float = 1.414) -> 'MCTSNode':
        """
        Select best child using UCT (Upper Confidence Bound for Trees)
        UCT = exploitation + exploration
        exploitation = node.value
        exploration = c * sqrt(ln(parent_visits) / node_visits)
        """
        best_score = -float('inf')
        best_child = None

        for child in self.children:
            if child.visits == 0:
                # Prioritize unvisited nodes
                uct_score = float('inf')
            else:
                # UCT formula
                exploitation = child.value
                exploration = exploration_weight * math.sqrt(math.log(self.visits) / child.visits)
                uct_score = exploitation + exploration

            if uct_score > best_score:
                best_score = uct_score
                best_child = child

        return best_child

    def add_child(self, agent_id: int) -> 'MCTSNode':
        """Add a new child node"""
        child = MCTSNode(agent_id=agent_id, parent=self)
        self.children.append(child)
        return child

    def update(self, value: float):
        """Update node statistics"""
        self.visits += 1
        self.total_value += value

    def __repr__(self):
        return f"MCTSNode(agent={self.agent_id}, visits={self.visits}, value={self.value:.3f})"