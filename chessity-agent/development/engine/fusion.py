"""Bounded root fusion of the original value and learned move-policy networks."""


class RootFusion:
    def __init__(self, policy, value, value_cp=5):
        self.policy = policy
        self.value = value
        self.value_cp = max(0, min(10, int(value_cp)))

    def bonuses(self, board, moves, max_cp=15):
        budget = max(0, min(25, int(max_cp)))
        value_budget = min(budget, self.value_cp)
        policy_budget = budget - value_budget
        prior = self.policy.bonuses(board, moves, policy_budget)
        scores = {}
        for move in moves:
            board.push(move)
            try:
                outcome = board.outcome(claim_draw=True)
                if outcome:
                    # After our move the side to move is the opponent. Mate and draw are explicit.
                    score = 0 if outcome.winner is None else 100000 if outcome.winner != board.turn else -100000
                else:
                    score = -self.value.centipawns(board)
                scores[move] = score
            finally:
                board.pop()
        best = max(scores.values()) if scores else 0
        return {move: min(budget, max(0, prior[move] + round(
            value_budget * max(0.0, min(1.0, 1.0 + (scores[move] - best) / 200.0))
        ))) for move in moves}
