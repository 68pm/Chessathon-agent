# Requested practical diagnostic after the local-value fit

The user explicitly requested the bots play2400/2600 again after learning from
the losses and draw. The completed local fit reduced training MAE on37 independent
descendants from309.5 to156.87cp but FAILED the17-root move-quality gate. Keep
that failure and the current53 upload. This new practical diagnostic does not
change the gate, qualify a release, or claim the trained candidate improved.

There is now a genuinely changed, fitted network to test. Run one fresh E55 colour
pair each against nominal2400 and2600 at120s+0.5s, exactly four initial games.
Both colours and every result stay in the record. Same prepared E55 opening as
the source games enables an explicitly exposed-opening rematch; it is not an
independent strength estimate. No extra games to obtain a win. Follow the user's
conditional2800 request only after a played checkmate win against2600 without
operational failure. No long consistency study and no engine/training overlap.

Use candidates/compiled-local-descendant-v1, byte-identical to the fitted and
probed prototype. First perform the strict read-only package check:90s init,
two legal120000ms calls, no runtime filesystem mutation/network/subprocess,
existing optional Alien and elementary endgames verified. Preserve all failed
checks and abort games on an operational package failure. No unchanged retry.

Freeze candidate, package, config and sources. Hidden SystemPowerShell Normal4
launch;2048MiB disk/768MiB RAM directly before each agent/teacher launch and
each stage, capacity wait capped20minutes. If four games complete, audit actual
histories, both clocks, sources and outcomes; report separately from53 results.
Do not replace the best upload merely because of a higher isolated opponent win.
