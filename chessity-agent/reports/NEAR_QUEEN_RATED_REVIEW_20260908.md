# Bounded review of v1.53 rated games

All four predeclared 120s + 0.5s games completed: nominal2400 gave0W1D1L,
nominal2600 gave0W0D2L. One threefold draw and three checkmate losses, no failures
on either side. The results describe this tiny E90 opening sample, not an Elo.

Review all160 candidate moves (80/19/31/30 by game) with the existing20k best/played
screen and80k/320k verification of suspicious choices. Maximum requested work is
134.4million nodes before identical-move reuse,840k per own move. Freeze the
actual source/hash/count before the first teacher call. Preserve every candidate
move and actual history, both budgets, mate-scored cases and errors in the draw.
Then reuse these labels for phase reporting with zero additional teacher nodes.
Separate where losses first developed from the stage where the games ended.

Launch only after the rated task and owned processes finish, with no other heavy
work. Require2048MiB disk/768MiB RAM directly before the teacher, at most20 minutes
capacity wait, hidden Normal priority4 and STOP checks before every analysis.
The fresh output directory is created explicitly before its preparation file.
No games, candidate JIT, training, source changes or automatic selection here.

Engine improvements remain first: compare any king-defence or exchange errors
with the earlier Rd4/h3 warning and independently reviewed exchange endings.
Useful learning is second: identify actual counterfactual descendants and a
compatible objective before fitting, rather than putting root labels on leaves.
These four games supply targeted data; broad game downloads and unchanged extra
epochs are not justified by this review. Keep the long study cancelled.
