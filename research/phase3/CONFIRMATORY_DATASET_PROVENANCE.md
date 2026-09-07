# Phase 3 Confirmatory Dataset Provenance

**Status: FROZEN BEFORE ECONOMIC ANALYSIS**

This record binds the fresh Phase 3 confirmatory capture set before any Phase 3 economic exposure, outcome, correlation, or support result is rendered.

## Research Binding

- Methodology preregistration commit: `a834e149e309fcae0e90ce3b213d5318aabf5e7c`
- Methodology contract SHA256: `1e3857d3d872d47a9b6e8056cec3cf6215eb1b2ad65c79eccce98ef492813419`
- Collection infrastructure commit: `5f0c7c0e45f59d4f9aad1347e1d23065a49c526d`
- Collection manifest: `phase3_confirmatory_20260907T163207518671Z.manifest.json`
- Collection manifest SHA256: `9d47d74da16ee2b2550d8f08497e70a9e975930c7c8457c62d446d047b9ef17a`
- Confirmatory dataset fingerprint: `ff29993a22743674edf13363957e7e5386b338d4e599027b4006089991f382e2`

## Frozen Collection Policy

- Capture duration: 120 seconds
- WebSocket timeout: 20 seconds
- Start-to-start cadence: 900 seconds
- Target qualifying captures: 10
- Qualification rule: existing dual-source `gate.overall == PASS` plus frozen identity, duration, persistence, and SHA256 checks.
- REVIEW attempts remain preserved but do not enter the ten-capture confirmatory sample.

## Series Summary

- Series started UTC: `2026-09-07T16:32:07.519279Z`
- Series completed UTC: `2026-09-07T21:05:55.184689Z`
- Total attempts: 11
- Qualifying captures: 10
- Non-qualifying REVIEW attempts: 1
- Qualifying attempt indices: `1, 3, 4, 5, 6, 7, 8, 9, 10, 11`
- REVIEW attempt indices: `2`

## Attempt-Level Provenance

| Attempt | Overall Gate | Qualifies | Capture File | SHA256 |
| ---: | --- | --- | --- | --- |
| 1 | PASS | true | `dual_ws_20260907T163207532367Z.json` | `1039dc601f4142a80a484bac82ac4b4496f9dfea50f98bf92198354bd5c21d1f` |
| 2 | REVIEW | false | `dual_ws_20260907T164728334983Z.json` | `d9700af6f7bf05993b9ab1ce2f59ba2597eb3b61f1d5203c1c16f510e531c0e4` |
| 3 | PASS | true | `dual_ws_20260907T170236660993Z.json` | `38bbaeccfe56d5857a74f0884705e3d7b244058bb1d1024e8cb19137b169b4fc` |
| 4 | PASS | true | `dual_ws_20260907T172557927291Z.json` | `4c85c427184213dec2cbdcb60d6d32c5d1359fe5195dd8ba35768cfc6d717bb5` |
| 5 | PASS | true | `dual_ws_20260907T174113784024Z.json` | `619c3d65d2b902c5b09d7fd71be35cd1adb9adebbe9ba2728e361f047e014677` |
| 6 | PASS | true | `dual_ws_20260907T194349594005Z.json` | `4d215697e54646660cae04a474a0174d1bd8ae3e6248651e5136e0d6b19d472c` |
| 7 | PASS | true | `dual_ws_20260907T200052664833Z.json` | `641324dd383f66857ffc1461d7caaca41717e8fd51198d1f2cc889adc38b1532` |
| 8 | PASS | true | `dual_ws_20260907T201619732398Z.json` | `feae4de3ba4b2cbf67f884afd0e20d48b400a167f26f08cd5ec928365aa90955` |
| 9 | PASS | true | `dual_ws_20260907T203148414934Z.json` | `d5f4886e73da9d683e18cd92ecd74b275ddfc7a7912c87c0e55935f4879d7d54` |
| 10 | PASS | true | `dual_ws_20260907T204820782554Z.json` | `e196db96d61bc791966c29630af1f023c721a1131ef1ad96b96c255aa40dc986` |
| 11 | PASS | true | `dual_ws_20260907T210347101461Z.json` | `e2d3190238803a2e4b0a9c8fd13e7be26a833a7edbc54043ec41a0017106a492` |

## Freeze Decision

The confirmatory Phase 3 dataset is defined as the first ten chronologically observed attempts satisfying the preregistered technical acceptance rule.

No capture was added, removed, ranked, or substituted using Phase 3 economic values.

Attempt 2 remains preserved as a technical REVIEW and is excluded from the qualifying confirmatory sample according to the pre-registered rule.

The ten qualifying capture SHA256 values, in chronological order, produce the frozen dataset fingerprint `ff29993a22743674edf13363957e7e5386b338d4e599027b4006089991f382e2`.

## Claim Boundary

This provenance record establishes technical dataset identity and collection integrity only.

It does not establish any relationship between Kuru state disagreement and subsequent Coinbase market movement.

No Phase 3 price, return, volatility, correlation, predictive, trading, or causal result is reported here.
