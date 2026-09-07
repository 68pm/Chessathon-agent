# First-cycle builder and critic review

The first measured cycle is complete. The PVS candidate scored 5 wins, 1 draw and 2 losses against frozen v1.14 in four colour pairs at 120+0.5. All eight game records passed replay, clock and source audits. The pair-bootstrap 95% score interval is 50%–87.5%; it does not establish superiority by itself.

On 192 diagnostic training positions, accepted choices improved from 142 to 145 at 4000ms remaining and from 139 to 145 at 800ms; verified 200cp errors fell from 17 to 15 and 19 to 16. On the 96 validation positions, accepted choices changed from 72 to 71 and 71 to 69 respectively, with five blunders for each build in both modes. Fixed-node validation choices have identical aggregate quality. These are mixed results and host timing is not isolated.

The implementation passed the 83-test suite, including targeted capture/promotion generation and full-depth PVS equivalence checks. Both search variants retain the same network, classical evaluation, optional Alien preference and clock controller. The stored candidate remains immutable.

Decision: advance the single eligible PVS candidate under the predeclared ranking and freeze it before final tests. The optional second selective-search implementation is not used: it would introduce another search-quality tradeoff without resolving the current mixed validation evidence. The user has also requested a subsequent, separate elite-case learning experiment. Complete the fixed confirmation/rated/endgame schedule first. No test positions or final outcomes were consulted for this decision, and no rating or promotion is inferred from the development wins.
