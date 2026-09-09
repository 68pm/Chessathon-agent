# Review the selected bot's side of the exact-version comparison

The archive challenge's normal feedback pipeline reviewsv1.42's moves. Preserve
those records. Once all four comparison games are complete and audited, derive
separatev1.53-perspective records with the same authoritative PGNs, moves,
clock records and physical colours. Swap only candidate/opponent attribution,
invert candidate_white and candidate score, and attach the original result SHA.
Physical failed_colour and termination must remain unchanged. Revalidate each
derived record against the PGN and clock/outcome audit. Never replay the games.

After the ENTIRE archive challenge stops, and only with15minutes remaining
before06:40BST, run the existing feedback_batch pipeline on the derived records.
Use its existing80k/320k move labels and reward-policy fit, with extended Windows
paths, source hashes, capacity checks, STOP/deadline checks and a900second outer
bound. Runtime source/model files are frozen and unchanged. The resulting policy
checkpoint is experimental; no root reward becomes a descendant-value label.

An interrupted review stays partial, with complete prior rows retained. Do not
claim that partial work trained or improved the uploaded agent. If the remaining
time is insufficient, leave the prepared records for later authorised work.
