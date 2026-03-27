#backend/mcts/search.py
class MonteCarloTreeSearch:

    def __init__(self, node):
        self.root = node

    def best_action(self, simulations_number=20):

        for _ in range(simulations_number):
            node = self._tree_policy()
            reward = node.rollout()
            node.backpropagate(reward)

        return self.root.best_child(c_param=0.0)

    def _tree_policy(self):
        node = self.root

        while not node.is_terminal_node():
            if not node.is_fully_expanded():
                return node.expand()
            else:
                node = node.best_child()

        return node
