# Root PVS pilot: fewer fixed-depth nodes, no tactical improvement

**The prototype is not selected. v1.52 remains the provisional upload.**
Cycle 31 completed on 8 September at 13:32 BST. Its predeclared practical
improvement gate failed because none of the four recent mistakes improved.
No new games, neural training, package or Elo claim resulted.

The only code change was to scout later root moves with a narrow search window
and fully re-search any improving bound. Evaluation, neural weights, policy,
Alien Gambit, clocks and the rest of the search were unchanged.

| Measure | Selected v1.52 | Root PVS prototype |
|---|---:|---:|
| Production initialization | 64.696 s | 79.051 s |
| Fixed-depth completed attempts | 22/22 | 22/22 |
| Aggregate fixed-depth nodes | 373,445 | 280,371 |
| Aggregate fixed-depth search time | 2.963 s | 2.071 s |
| Mean completed depth over 21 one-second probes | 5.143 | 5.143 |
| Teacher mean regret at 80k / 320k | 234.10 / 246.29 cp | 234.10 / 246.29 cp |
| Largest one-second probe wall time | 1.012 s | 1.010 s |

The fixed-depth searches used **24.92% fewer nodes**, with identical completed
scores in all 22 comparisons. Nine independent tests passed, covering fail-hard
scout bounds, mandatory full re-search, signed policy bonuses, ties, mate scores,
interruption, restoration and source identity. Both production workers also
passed legal-move, board/history restoration, mate-in-one and 512-node interrupted
iteration checks. These are exposed development checks, not an independent
strength estimate or a guarantee for every position.

The cheap efficiency gate passed, but **all 21 clock-limited move choices were
identical between builds**. Mean completed depth was also unchanged. Existing
teacher references and compatible cached analyses covered every choice, so the
review requested zero new teacher nodes. There were no new paired 200cp errors
or mate losses, but no qualifying repair either. The original requirement for
at least one recent warning to improve by 100cp at both budgets remains in force.

The result supports retaining root PVS as an unselected engineering component.
It does not support replacing the upload, changing the acceptance rule, or
repeating timing until a favorable result appears. The difference between lower
fixed-depth work and unchanged clock behavior warrants caution about translating
one speed measurement into playing strength.

Next, inspect how the selected evaluator scores the verified refutations of
`30...Bxf2+` and `26.gxf6 e.p.`. Compare the positions after forced exchanges and
the rook fork, preserving both teacher queen alternatives. Establish whether
the dominant error comes from an unseen continuation or a wrongly valued
descendant before changing evaluation or fitting a residual network. The
existing four recent warnings and 17 retained roots provide targeted data;
another broad game download or blind fitting run is not justified.

The hidden Normal-priority task exited successfully and was removed after
verifying that no owned chess process remained. Sources, histories and limits
were frozen before execution. All selected v1.52 bytes and older releases remain
unchanged. See [predeclared rules](IMPROVEMENT_CYCLE_31.md) and the complete
[evidence manifest](evidence/root-pvs-20260908/manifest.json).
