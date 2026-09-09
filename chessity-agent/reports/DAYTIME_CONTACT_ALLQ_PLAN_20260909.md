# Prove immediate contact mates after quiescence continuations

Trial01 corrected direct mate leaves but left all tested root decisions unchanged.
Its qdepth-zero restriction excludes positions reached after a capture or check
evasion inside quiescence. Test the identical legal mate proof at every nonchecked
quiescence node, including the existing qdepth limit. This remains an immediate
terminal proof: no quiet-check recursion, extensions or finite mate labels.

Use the same preserved fast-legal parent, twenty-one exposed roots, ABBA repeats,
one-/three-second budgets and five-million-node cap. Add correctness checks at
qdepth 0, 1, 4, 11 and 12 for both real mates and colour mirrors. Preserve the
independent random legality/mate oracle, state restoration and AST isolation.

Keep the existing independent teacher gate unchanged: strictly lower finite mean
three-second regret at both 80k/320k budgets, no new stable >=200cp error or mate
loss at either time budget, and a teacher-supported Bxh7+ choice at at least one
root in both three-second repeats. These exposed probes are development evidence.
Only a pass proceeds to short games. Retain v1.55 and all failed sources otherwise.
Respect serial CPU work, 1400MB capacity, STOP flags and the daytime cutoff.
