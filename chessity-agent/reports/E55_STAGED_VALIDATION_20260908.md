# Identify startup separately from move-check time

The first experimental rematch controller stopped in the original package
validator. Its single90s subprocess watchdog covered startup, optional Alien
and table checks, plus two120000ms move requests. It emitted no stage telemetry.
Preserve its failure and all logs. This does not establish whether initialization
alone exceeded90s. No rated game started in that attempt.

The corrected validator keeps the SAME strict runtime audit and probe program,
adding a ready event immediately after import. An external90s watchdog starts
at child launch and ends only on ready; the measured import must also be<90s.
The subsequent two move/feature checks have their own30s watchdog. File mutation,
network, subprocess, archive-size and peak-memory restrictions are preserved.
Every stage is saved even on failure; timeout terminates only the owned child
tree. Three small subprocess tests verify the deadlines and phase separation.

This is a changed validation harness, not an unchanged training/game retry or
an increased initialization allowance. The fitted candidate and ZIP are byte-
identical. A fresh controller then runs the already requested four diagnostic
games2400/2600 at120s+0.5s, with2800only after a played2600win. Its failed position
gate remains failed and53 remains the best upload. No promotion from this screen.
