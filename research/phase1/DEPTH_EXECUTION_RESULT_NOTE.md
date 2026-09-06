# Phase 1 — State-Conditioned Executable Depth and Slippage Result Note

## Status

**EMPIRICAL GATE PASS — descriptive result only.**

The frozen Phase 1 state-conditioned depth and deterministic simulated-sweep methodology was reproduced successfully over the five verified Kuru/Coinbase dual-WebSocket captures.

This result note records the observed evidence and its limitations.

It does not establish a trading edge, causal finality effect, execution probability, arbitrage opportunity, or protocol invariant.

## Dataset

Ordered five-capture dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

Deterministic generated report SHA256:

`1d87dd7802228988e3353e47feee01ecb571a124e8692778b6bda8739c3db01e`

The report reproduced byte-for-byte across two independent runs.

Kuru observations:

`8255`

Eligible complete four-state execution panels:

`8255`

Invalid execution-state panels:

`0`

Insufficient-source-evidence observations:

`0`

No additional structural attrition was introduced by the full-depth execution layer.

## Frozen Primary Methodology

Market:

`MON_USDC`

Simultaneous state views:

- proposed;
- voted;
- finalized;
- committed.

Sides:

- BUY consumes captured asks;
- SELL consumes captured bids.

Frozen displayed-depth bands:

- 5 bps;
- 10 bps;
- 25 bps;
- 50 bps.

Frozen simulated base-quantity targets:

- 200 MON;
- 2,000 MON;
- 20,000 MON;
- 200,000 MON.

This is a Kuru-only depth layer.

Coinbase reference-age thresholds are not applied to these Kuru-only measurements.

## Primary Fillability Result

Every frozen target fully filled inside every eligible captured book for every state and both sides.

For each state, side, and target:

`fully_filled_count = 8255`

`insufficient_captured_depth_count = 0`

Therefore the frozen primary target ladder did not differentiate the four state views through binary captured-book fillability.

This is not an execution-probability statement.

It describes only deterministic sweeps through the displayed levels present in the captured payloads.

## Primary Slippage Result

For 200 MON and 2,000 MON, pooled median simulated slippage was zero for every state on both sides.

For 20,000 MON, pooled median simulated slippage was also zero for every state on both sides.

For 200,000 MON, pooled median simulated slippage was approximately 7–8 bps depending on side and state.

The more important within-panel result was:

**paired median simulated-slippage delta was zero for every predefined state pair, side, and frozen target size.**

Positive, zero, and negative paired changes were all observed depending on the comparison and target.

The descriptive sample therefore does not support a robust claim that later state views systematically reduce simulated displayed-book slippage.

## Primary Depth Result

Marginal state-conditioned displayed-depth distributions differed numerically.

However, within-panel paired depth deltas had median zero for every predefined state pair and every frozen 5/10/25/50 bps depth band.

For the 25 bps band, the capture-level median depth delta was zero in each of the five capture windows for every predefined state pair on both BUY and SELL sides.

The descriptive sample therefore does not support a robust claim that later state views systematically increase displayed depth.

## Secondary Raw Full-Book Structural Diagnostic

This diagnostic was examined after the primary depth and simulated-slippage result.

It is therefore reported separately from the frozen primary economic metrics.

Exact raw bid-and-ask book equality was evaluated within the same Kuru observation.

Across all 8,255 observations:

### Proposed versus voted

- top-of-book exactly equal: `4383`;
- full raw bid-and-ask book exactly equal: `2934`;
- top exactly equal while deeper raw book differed: `1449`.

### Proposed versus finalized

- top-of-book exactly equal: `3057`;
- full raw bid-and-ask book exactly equal: `2057`;
- top exactly equal while deeper raw book differed: `1000`.

### Proposed versus committed

- top-of-book exactly equal: `3057`;
- full raw bid-and-ask book exactly equal: `2057`;
- top exactly equal while deeper raw book differed: `1000`.

### Voted versus finalized

- top-of-book exactly equal: `4821`;
- full raw bid-and-ask book exactly equal: `4066`;
- top exactly equal while deeper raw book differed: `755`.

### Finalized versus committed

- top-of-book exactly equal: `8255 / 8255`;
- full raw bid-and-ask book exactly equal: `8255 / 8255`;
- raw bid book exactly equal: `8255 / 8255`;
- raw ask book exactly equal: `8255 / 8255`;
- top equal while deeper raw book differed: `0`.

Therefore:

**Across these five captured windows, every observed finalized and committed MON_USDC state view contained exactly identical raw bid-and-ask books.**

This is a dataset-specific empirical observation.

It is not evidence that finalized and committed have identical protocol semantics, and it must not be presented as a universal Kuru invariant.

The other state pairs also demonstrate that top-of-book equality does not imply full-book equality.

## Secondary 200,000 MON SELL Tail Forensic

The primary 200,000 MON SELL result contained a maximum simulated slippage of approximately:

`2233.086909820222916369401506 bps`

A post-result forensic threshold of:

`1000 bps`

was used only to investigate this tail.

This threshold is not part of the frozen primary methodology.

All such extreme observations occurred in one capture:

`dual_ws_20260906T011600173225Z.json`

Observed state-record counts at or above 1000 bps:

- proposed: `27`;
- voted: `23`;
- finalized: `38`;
- committed: `38`.

These row counts are not interpreted as independent economic events.

Within the extreme observations:

- proposed used 6 distinct raw-book hashes and 4 observed `U` values;
- voted used 2 distinct raw-book hashes and 3 observed `U` values;
- finalized used 2 distinct raw-book hashes and 4 observed `U` values;
- committed used 2 distinct raw-book hashes and 4 observed `U` values.

For finalized and committed, the same 38 record keys were present and their raw-book hashes, slippage values, final-level fills, and final-level prices matched exactly.

A representative extreme 200,000 MON SELL sweep had:

- best bid: approximately `0.02523`;
- levels touched: `8`;
- base quantity filled before the final consumed level: `156534.6952841596 MON`;
- remaining quantity filled at the final level: `43465.3047158404 MON`;
- final displayed level price: `0.000001`;
- final displayed level available quantity: `100000 MON`;
- resulting VWAP: `0.019595921726523577582`;
- simulated slippage: `2233.086909820222916369401506 bps`.

The extreme value is therefore reproducible from the captured displayed-book sweep arithmetic.

The evidence does not identify the economic origin of the `0.000001` displayed level.

It must not be attributed to a specific limit order, AMM component, market maker, protocol mechanism, or participant without separate evidence.

The level is retained in the primary result and is not deleted, winsorized, capped, or silently treated as bad data.

## Interpretation

The main empirical result is neutral rather than positive.

In these five capture windows:

- the frozen size ladder was fully fillable across all state views;
- paired median simulated-slippage differences were zero;
- paired median displayed-depth differences were zero;
- later state views did not show a robust systematic displayed-liquidity improvement under the frozen metrics;
- finalized and committed raw books were exactly identical throughout the observed dataset.

This does not imply that consensus/finality state is economically irrelevant in other periods, markets, sizes, or execution settings.

It means that this sample does not support a stronger claim.

## Claim Boundaries

The analysis concerns captured displayed Kuru MON_USDC books and deterministic static-book simulations.

It does not measure or establish:

- realized execution;
- execution probability;
- queue position;
- cancellation risk during execution;
- market impact caused by an order;
- gas or trading costs;
- MEV;
- network latency;
- consensus latency;
- protocol-finality latency;
- arbitrage;
- alpha;
- expected or realized profit;
- a causal finality premium;
- universal superiority of any state;
- universal equivalence of finalized and committed books.

Repeated `U` values are not classified as duplicates and `U` is not asserted to be a block identifier or finality identifier.
