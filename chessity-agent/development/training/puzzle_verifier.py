"""Offline independent labels. Exact short mates and explicitly approximate engine estimates."""

import os
import subprocess
import time

import chess
import chess.engine


class ProofCutoff(Exception):
    pass


def mate_moves(board, plies=1, node_cap=50000):
    """All root moves forcing mate within the horizon, covering every legal defence.

    None denotes an unresolved cutoff, never a failed proof or a draw.
    """
    solver, nodes = board.turn, 0

    def win(left):
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            raise ProofCutoff
        outcome = board.outcome(claim_draw=True)
        if outcome:
            return outcome.winner == solver
        if left == 0:
            return False
        values = []
        attacking = board.turn == solver
        for move in list(board.legal_moves):
            board.push(move)
            try:
                value = win(left - 1)
            finally:
                board.pop()
            if attacking and value:
                return True
            if not attacking and not value:
                return False
            values.append(value)
        return any(values) if attacking else all(values)

    result = []
    try:
        for move in list(board.legal_moves):
            board.push(move)
            try:
                if win(plies - 1):
                    result.append(move.uci())
            finally:
                board.pop()
    except ProofCutoff:
        return None, nodes
    return sorted(result), nodes


def root_key(board):
    return " ".join(board.fen().split()[:4])


def duplicate_key(board):
    """Merge exact transpositions and vertical colour mirrors before splitting."""
    return min(root_key(board), root_key(board.mirror()))


class Verifier:
    def __init__(self, executable, budgets=(80000, 320000)):
        self.engine = chess.engine.SimpleEngine.popen_uci(
            str(executable.resolve()),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.settings = {"Threads": 1, "Hash": 32, "UCI_LimitStrength": False}
        self.engine.configure(self.settings)
        self.budgets = budgets

    def close(self):
        self.engine.quit()

    def analyse(self, board, nodes):
        self.engine.configure({"Clear Hash": None})
        lines = self.engine.analyse(board, chess.engine.Limit(nodes=nodes),
                                    multipv=board.legal_moves.count(), game=object())
        results = {}
        for info in lines:
            score = info["score"].pov(board.turn)
            pv = [m.uci() for m in info["pv"]]
            results[pv[0]] = {"cp": score.score(), "mate": score.mate(), "pv": pv,
                             "depth": info.get("depth"), "nodes": info.get("nodes", 0),
                             "seconds": info.get("time", 0)}
        return results

    def verify(self, row):
        board = chess.Board(row["solver_fen"])
        history = row.get("relevant_history", {})
        if history.get("complete"):
            restored = chess.Board(history["start_fen"])
            for uci in history["moves"]:
                restored.push_uci(uci)
            if restored.fen() != board.fen():
                raise ValueError("Recorded history does not reach solver FEN")
            board = restored
        if not board.is_valid() or board.is_game_over(claim_draw=True) or board.halfmove_clock >= 80:
            return None, "invalid, terminal, or inadequate draw history"
        started = time.perf_counter()
        legal = {m.uci() for m in board.legal_moves}
        exact, proof_nodes = mate_moves(board)
        horizon = 1
        if not exact and "mateIn2" in row.get("secondary_themes", []):
            horizon = 3
            exact, proof_nodes = mate_moves(board, 3)
        analyses = [self.analyse(board, n) for n in self.budgets]
        if any(set(a) != legal for a in analyses):
            return None, "incomplete legal root coverage"
        first, deep = analyses
        cp_only = all(v["cp"] is not None for a in analyses for v in a.values())
        targets, bad = {}, []
        if exact:
            acceptable = exact
            targets = {move: float(move in exact) / len(exact) for move in legal}
            objective, confidence, proof = "forced_mate", "exact", f"exhaustive_mate_within_{horizon}_plies"
        elif cp_only:
            import math

            best = [max(v["cp"] for v in a.values()) for a in analyses]
            # Accept near-best alternatives only when both budgets agree. Quarantine unstable leaders.
            acceptable = [m for m in legal if all(best[i] - analyses[i][m]["cp"] <= 70 for i in range(2))]
            if not acceptable or abs(best[0] - best[1]) > 100:
                return None, "unstable leading analysis"
            for move in sorted(legal):
                regret = [best[i] - analyses[i][move]["cp"] for i in range(2)]
                if min(regret) >= 200:
                    bad.append({"move": move, "regret_cp": regret, "refutation": deep[move]["pv"]})
                # Soft supervision avoids pretending every estimated small score gap is exact.
                targets[move] = math.exp(max(-15, (deep[move]["cp"] - best[1]) / 100))
            total = sum(targets.values())
            targets = {m: v / total for m, v in targets.items()}
            confidence, proof = "engine_supported", "two_budget_full_legal_root_analysis"
            if board.is_check():
                objective = "defence_estimate"
            elif best[1] <= 100:
                objective = "no_verified_tactical_win"
            else:
                objective = "preserve_estimated_advantage"
        else:
            return None, "non-exact mate scores; no centipawn conversion or strict reward"
        predicate = (
            f"Force checkmate against every legal defence within {horizon} plies."
            if exact else "Choose a move within 70cp of the best at BOTH declared budgets. Estimated move quality, not proof of a win."
        )
        output = dict(row)
        output.update(
            acceptable_first_moves=sorted(acceptable), target_distribution=targets,
            candidate_moves=analyses, tempting_bad_moves_and_refutations=bad,
            objective_type=objective, confidence=confidence, proof_type=proof,
            objective_predicate=predicate, score_perspective="root side to move",
            score_type="exact_mate_objective" if exact else "centipawns_separate_from_mate",
            continuation_branches=[deep[m]["pv"] for m in sorted(acceptable)],
            teacher_version=self.engine.id, teacher_settings=self.settings,
            verification_budget={"requested_nodes_per_pass": self.budgets,
                                 "actual_nodes_per_pass": [max(v["nodes"] for v in a.values()) for a in analyses],
                                 "seconds": time.perf_counter() - started,
                                 "exact_proof_nodes": proof_nodes,
                                 "mate_horizon_plies": horizon if exact else None},
        )
        return output, None
