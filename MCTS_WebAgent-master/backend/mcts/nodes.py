#backend/mcts/nodes.py
import numpy as np
from abc import ABC, abstractmethod

class MonteCarloTreeSearchNode(ABC):

    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self._number_of_visits = 0
        self._total_reward = 0.0

    @property
    def n(self):
        return self._number_of_visits

    @property
    def q(self):
        return self._total_reward

    @abstractmethod
    def untried_actions(self):
        pass

    @abstractmethod
    def expand(self):
        pass

    @abstractmethod
    def is_terminal_node(self):
        pass

    @abstractmethod
    def rollout(self):
        pass

    def backpropagate(self, reward):
        self._number_of_visits += 1
        self._total_reward += reward
        if self.parent:
            self.parent.backpropagate(reward)

    def is_fully_expanded(self):
        return len(self.untried_actions()) == 0

    def best_child(self, c_param=1.4):
        weights = [
            (child.q / (child.n + 1e-6)) +
            c_param * np.sqrt((2 * np.log(self.n + 1) / (child.n + 1e-6)))
            for child in self.children
        ]
        return self.children[np.argmax(weights)]
