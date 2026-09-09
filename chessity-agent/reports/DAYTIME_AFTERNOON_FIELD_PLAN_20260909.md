# Refresh actual completed competition games

The recent exact-table and immediate-mate experiments failed their declared gates.
Keep selected v1.55 unchanged. Obtain a fresh public leaderboard and the newest
three completed games of our team and the uniquely advertised current leader.
Use direct no-cache requests because the web tool's cached team pages were stale.
Preserve the observed leader UUID, URLs, timestamps and page/PGN hashes.

Deduplicate against completed field03, field04 and field06 observations and the
earlier field manifest. Skip unfinished or void games; validate every PGN move,
candidate colour and final position. Public submission hashes remain unknown,
so these games cannot be called performances of a particular selected version.

Review every newly downloaded completed game through the existing history-aware
feedback batch, including wins, draws and losses. Preserve uncertain and mate
labels. Any reward-policy fits remain experimental and do not modify the playing
model. Summarise turning points and phases only after the controller closes.

Keep this bounded 1800-second fetch/review job serial with all heavy work, under
the existing capacity, STOP, owned-process and daytime deadline guards. No new
training architecture, independent validation or release is inferred from a
field refresh alone. Use the observations to choose the next concrete weakness.
