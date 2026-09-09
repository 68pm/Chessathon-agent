# Reservation repair before any antisymmetric training

antisymmetric-value-supervisor-01 stopped in preparation after 2.03 seconds.
No fitting, checkpoints or teacher analysis ran. Preserve that source and log.
The original two-per-ECO reservation limit could supply only 18 eligible distinct
positions after excluding all earlier daytime reservation groups and protected
positions. There are ten eligible new groups:

| Group | Eligible distinct positions |
|---|---:|
| A82 | 19 |
| C67 | 41 |
| E80 | 29 |
| E77 | 7 |
| A42 | 43 |
| E38 | 25 |
| A38 | 15 |
| C39 | 11 |
| E34 | 1 |
| A58 | 1 |

Create a new run, antisymmetric-value-02. Keep the architecture, training data,
seed, updates, metrics and pass thresholds from the original plan. Only change
reservation sampling: visit eligible new groups in rounds, selecting at most one
root per group per round, up to three per group, until 24 roots are reserved.
Require at least eight distinct groups. All earlier group, exact/mirror and
teacher-uncertainty exclusions remain. Three-per-group capacity is 26, so this
can supply 24 without reusing any previously reserved opening group.

This changes the sampling bound before any model result exists; it does not
relax a failed strength or value gate. All new reservations become exposed after
their eventual evaluation. If the repaired preparation fails, preserve it and
diagnose the actual failure before a new attempt.
