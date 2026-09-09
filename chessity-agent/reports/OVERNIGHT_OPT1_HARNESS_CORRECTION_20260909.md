# Fixed-depth probe request-key correction

Preserve opt1-startup-01 as a rejected preflight. Inspection found that its
request used the key depth, which would collide with the worker's returned
depth keyword in dict construction. An isolated Python reproduction confirmed
the TypeError before any compilation, timing, game or training was launched.

The separate opt1-startup-02 harness calls that input max_depth. The candidate
engine, compiler level,24 checks,65-second startup gate,26 fixed-depth references
and104 timed quality probes are unchanged. No earlier result is overwritten.
