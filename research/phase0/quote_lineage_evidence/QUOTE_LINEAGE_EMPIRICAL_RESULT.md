# Quote-Lineage Empirical Result

## Scope

This artifact summarizes five captured Kuru `mon_usdc@monadDepth` observation windows using the episode-aware quote-lineage methodology implemented in this repository.

Dataset fingerprint:

`a25f99463438853fbc4c27f7531cc1904e36ca4fb323f05405089d10d5727445`

The analysis uses a minimum unresolved follow-up window of **1000 ms**.

## Evidence Base

- Capture windows: **5**
- Captured WebSocket messages: **6159**
- Sum of within-capture unique `U` counts: **781**

- `kuru_ws_20260905T233039949275Z.json` — SHA256 `58f438312459808d54dd8e423adcf7adf0e7f71f2dc49153a35d7aec5d67227e`; 1109 messages
- `kuru_ws_20260905T233212584800Z.json` — SHA256 `f479bcf8f12a0b88f390834dda357283661c559e0beb12c9bd6fa2f8efd8abb9`; 1209 messages
- `kuru_ws_20260905T233345251807Z.json` — SHA256 `43dee779f8b2049dda4f71aa4b75e6cd3ccbfd6674e7886a3b686b7fb743b532`; 1132 messages
- `kuru_ws_20260905T233517872935Z.json` — SHA256 `95b7485f9c2e66ae2520424880dd6c469d5036bc0df7ba641103d0d5e7c6ab66`; 1243 messages
- `kuru_ws_20260905T233650736812Z.json` — SHA256 `c831ffd505206bfd776cfc50830d4ebdcafb74d18e083f707973a50443071d59`; 1466 messages

Raw capture payloads are not embedded in this evidence bundle. Reproducing the calculations requires the listed source capture files to be available and to pass SHA256 verification against the hashes above.

## Exact Price + Quantity Identity

Across the five windows, **491** episodes remained evaluable after conservative ambiguity and censoring exclusions. **305** were observed in ordered proposed → voted → finalized → committed state views.

The pooled ordered proportion is **62.12%**, but this value is **descriptive only**.

Across individual capture windows, the ordered proportion ranged from **47.16%** to **74.32%**, with a capture-level median of **69.23%**.

There were **58** evaluable later-observed progressions. For those observations, the pooled client-observed first-sighting median was **95.418 ms** for voted and **381.161 ms** for finalized. Committed had the same pooled median of **381.161 ms** in this sample.

## Price-Level Identity

When quote identity is relaxed to price only, **425** episodes remained evaluable and **289** were observed in ordered state views.

The pooled ordered proportion is **68.00%**, again **descriptive only**.

Across individual capture windows, the ordered proportion ranged from **54.81%** to **76.71%**, with a capture-level median of **72.00%**.

There were **45** evaluable later-observed progressions. Their pooled client-observed first-sighting median was **112.447 ms** for voted and **383.701 ms** for finalized. Committed had a pooled median of **383.701 ms**.

## Interpretation

The captures demonstrate that state-specific top-of-book representations can be observed across Kuru's proposed, voted, finalized, and committed views, and that some conservatively evaluable quote episodes are observed in ordered progression across those views.

The capture-level variation is material, so a single pooled proportion should not be interpreted as a stable population survival probability. The observation windows are not assumed to be statistically independent.

## Claim Boundary

`U` is retained only as an observed stream grouping field; no block-number or undocumented protocol semantics are assigned to it.

Quote identity does not establish individual order identity, ownership, execution, or economic intent. Re-entry-ambiguous episodes are excluded from evaluable statistics.

A quote not observed in a later state is not classified as a finality failure or execution failure.

Reported latency values are client-observed first-sighting differences within the captured WebSocket stream. They are **not** measurements of Monad consensus latency or protocol finality latency.

These results do not establish a trading edge, arbitrage opportunity, finality premium, causal relationship, or profitability claim.
