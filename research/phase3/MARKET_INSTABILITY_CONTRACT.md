# Phase 3 — State-Conditioned Market Instability Contract

## Status

**PRE-REGISTERED METHODOLOGY — confirmatory Phase 3 economic values have not yet been collected or inspected.**

This contract must be committed before collection of the fresh Phase 3
confirmatory dataset.

The five dual-WebSocket captures used in Phases 1 and 2 may be used only for:

- technical feasibility;
- schema verification;
- architecture reuse;
- source-integrity verification.

They are not eligible for the confirmatory Phase 3 economic analysis.

## Research Question

Phase 3 asks:

> Is the magnitude of the simultaneous Kuru proposed-versus-finalized midpoint
> disagreement observed at `t0` descriptively associated with the magnitude of
> subsequent Coinbase MON-USD midpoint movement?

The question concerns future market-instability magnitude.

It does not ask:

- which direction Coinbase will move;
- whether Kuru predicts Coinbase;
- whether Kuru leads Coinbase;
- whether the relationship is causal;
- whether a trading strategy is profitable;
- whether a finality premium exists.

## Markets

Kuru / Monad:

`MON_USDC`

Coinbase:

`MON-USD`

The common base asset is MON.

USD and USDC are not assumed to be economically identical.

The primary future outcome is entirely Coinbase-to-Coinbase, so the future
return itself does not require treating USD and USDC as identical.

## Unit of Observation

One complete Kuru four-state panel is one Phase 3 observation.

Required simultaneous Kuru state views:

- proposed;
- voted;
- finalized;
- committed.

The four views are simultaneous captured market-state views.

They are not interpreted as a temporal progression through consensus states.

One panel must not generate four duplicated Phase 3 observations.

## Time Anchor

`t0` is the Kuru record's same-process:

`received_monotonic_ns`

This is a local observation timestamp.

It is not:

- protocol-finality latency;
- network latency;
- exchange latency;
- consensus transition time.

## Baseline Coinbase Reference

Phase 3 reuses the established point-in-time backward-as-of Coinbase alignment
semantics.

For each Kuru observation, the baseline Coinbase record is the greatest
eligible target Coinbase Level2 record satisfying:

`coinbase_received_monotonic_ns <= kuru_received_monotonic_ns`

Future Coinbase information is prohibited from baseline selection.

Interpolation is prohibited.

The same baseline Coinbase state applies to the complete Kuru panel.

## Baseline Freshness

Frozen Coinbase baseline-freshness thresholds:

- 250 ms;
- 500 ms;
- 1000 ms.

The **250 ms** population is primary.

The 500 ms and 1000 ms populations are nested freshness sensitivities.

They are not independent samples.

## Primary Exposure

The primary Phase 3 exposure is the absolute simultaneous Kuru
proposed-versus-finalized midpoint gap.

Using exact Decimal arithmetic:

`kuru_pf_gap_bps = (proposed_mid / finalized_mid - 1) * 10000`

Primary exposure:

`kuru_pf_abs_gap_bps = abs(kuru_pf_gap_bps)`

This is a magnitude measure.

The sign of the proposed-versus-finalized gap is not part of the primary Phase
3 hypothesis.

No minimum absolute-gap threshold is imposed.

No post-hoc "large disagreement" cutoff may be promoted from the confirmatory
dataset.

## Zero-Disagreement Panels

Panels satisfying:

`kuru_pf_abs_gap_bps == 0`

remain eligible for the primary analysis.

They are not discarded.

The report must separately preserve the zero-exposure count.

Zero disagreement is a valid observed market state.

## Future Coinbase State

Frozen future horizons:

- 250 ms;
- 1000 ms;
- 5000 ms;
- 10000 ms.

Primary horizons:

- 250 ms;
- 1000 ms;
- 5000 ms.

The 10000 ms horizon is an extended sensitivity only.

For horizon `h`, the future Coinbase state is the greatest eligible target
Level2 record satisfying:

`coinbase_received_monotonic_ns <= t0 + h`

The first record after the horizon is never substituted.

Interpolation is prohibited.

## Capture-End Continuity

A future observation is eligible only when the capture provides source
continuity through the requested horizon.

Cross-capture stitching is prohibited.

If the capture does not continue through the horizon, the observation is
classified as:

`RIGHT_CENSORED_CAPTURE_END`

A persistent Coinbase book state at the horizon is valid when capture
continuity exists.

An unchanged book is not automatically missing evidence.

## Primary Outcome

The primary Phase 3 outcome is the absolute Coinbase midpoint movement from the
baseline Coinbase state to the future Coinbase state.

First compute the signed Coinbase midpoint return:

`coinbase_forward_mid_return_bps = (future_mid / baseline_mid - 1) * 10000`

Then define:

`coinbase_abs_forward_mid_move_bps = abs(coinbase_forward_mid_return_bps)`

The primary outcome therefore measures movement magnitude, not direction.

It is not:

- realized PnL;
- realized execution;
- market impact;
- adverse selection actually suffered by a trader;
- a strategy return.

## Primary Association Statistic

The primary descriptive association statistic is Spearman rank correlation
between:

`kuru_pf_abs_gap_bps`

and:

`coinbase_abs_forward_mid_move_bps`

Spearman correlation is selected before confirmatory data collection because
the question concerns monotonic association and does not require a linear
relationship.

Ties must be handled deterministically using average ranks.

## Undefined Correlation Handling

A Spearman correlation is undefined when:

- fewer than two evaluable observation pairs are available; or
- the exposure has zero rank variance; or
- the outcome has zero rank variance.

Undefined correlations must not be coerced to zero.

They must be reported explicitly as unavailable together with a reason code.

For capture-level reporting:

- every qualifying capture remains in the dataset even when its correlation is
  undefined;
- defined and undefined capture-level correlation counts must both be
  preserved;
- the capture-level median is computed only across defined capture-level
  correlations;
- at least six of the ten qualifying captures must have a defined
  capture-level correlation for the capture-level robustness condition to be
  available.

If fewer than six qualifying captures have a defined capture-level correlation
at a horizon, that horizon cannot satisfy the Phase 3 descriptive support
rule.

If the pooled or deterministic non-overlapping Spearman correlation is
undefined, that horizon also cannot satisfy the descriptive support rule.

These rules are frozen before confirmatory data collection.

No outcome-driven transformation may be selected after viewing the data.

## Primary Reporting Hierarchy

For the primary 250 ms baseline-freshness population, each primary future
horizon must report:

1. pooled Spearman rank correlation;
2. capture-level Spearman rank correlation for every qualifying capture;
3. median capture-level Spearman correlation;
4. deterministic non-overlapping sensitivity Spearman correlation;
5. exposure and outcome descriptive distributions;
6. zero-exposure count;
7. eligibility and censoring counts.

Pooled correlation alone is not sufficient for a robust conclusion.

## Descriptive Support Rule

At an individual primary horizon, evidence is considered
**directionally supportive of a positive instability association** only when
all three of the following are defined and positive:

- pooled Spearman correlation;
- median capture-level Spearman correlation, with at least six of the ten
  qualifying captures contributing defined capture-level correlations;
- deterministic non-overlapping-sensitivity Spearman correlation.

Cross-horizon support is considered robust only if this condition holds at least two of the three primary horizons:

- 250 ms;
- 1000 ms;
- 5000 ms.

If this pre-specified condition is not met, the primary Phase 3 relationship is
reported as:

**NOT ESTABLISHED**

This rule is descriptive.

It is not a statistical-significance test.

No minimum correlation magnitude is introduced after results are observed.

## Non-Overlapping Sensitivity

The deterministic within-capture non-overlapping sensitivity reuses the
established greedy selection rule.

For horizon `h`:

- sort eligible observations by Kuru `t0`;
- select the earliest eligible observation;
- select the next observation only when its `t0` is at or after the previous
  selected observation's `t0 + h`;
- continue through the capture.

This reduces mechanical horizon overlap.

It does not make the observations statistically independent.

## Freshness Sensitivity

The complete analysis is repeated for baseline freshness thresholds:

- 250 ms;
- 500 ms;
- 1000 ms.

The 250 ms population remains primary.

Results from the 500 ms and 1000 ms populations are sensitivity analyses and
must not replace an unfavorable primary result.

## Extended Horizon

The 10000 ms horizon is an extended sensitivity.

It must not override or rescue the conclusion from the three primary horizons.

## Source Integrity

Every confirmatory capture must satisfy the established dual-WebSocket source
gate.

Required source identity:

Kuru market:

`MON_USDC`

Coinbase market:

`MON-USD`

Coinbase channel:

`level2`

The analysis requires:

- complete raw Kuru records;
- complete raw Coinbase records;
- same-process monotonic receive timestamps;
- complete Kuru four-state panels;
- valid Coinbase snapshot/update reconstruction;
- target-product Level2 evidence;
- source-gate PASS.

Source-integrity failures are not repaired using inferred market values.

## Outcome Statuses

Phase 3 must preserve explicit outcome states including:

- `EVALUABLE`;
- `NO_PRIOR_REFERENCE`;
- `STALE_REFERENCE`;
- `RIGHT_CENSORED_CAPTURE_END`;
- `INSUFFICIENT_SOURCE_EVIDENCE`;
- `INVALID_KURU_PANEL`;
- `COINBASE_RECONSTRUCTION_FAILURE`.

Non-evaluable observations must not carry Phase 3 economic values.

## Collection Protocol

Phase 3 confirmatory collection must begin only after:

1. this methodology contract has been committed and pushed;
2. the dedicated Phase 3 collection wrapper has passed its synthetic and
   repository regression tests.

The collection wrapper is acquisition infrastructure only.

It must not compute or display Phase 3 economic exposures, outcomes,
correlations, or conclusions.

### Underlying dual-WebSocket capture

Each attempt must use the established concurrent Kuru / Coinbase dual-WebSocket
capture path represented by:

`scripts/capture_dual_ws.py`

and the existing:

`phase0.dual_ws_capture.v1`

capture schema.

Each attempt must use:

- requested capture duration: **120 seconds**;
- WebSocket receive timeout: **20 seconds**;
- Kuru stream: `mon_usdc@monadDepth`;
- Kuru market: `MON_USDC`;
- Coinbase market: `MON-USD`;
- Coinbase channel: `level2`.

### Attempt cadence

The first attempt begins when the automated Phase 3 series wrapper is started.

Subsequent attempts use a frozen **900-second start-to-start interval**.

For each attempt:

- the target next start time is 900 seconds after the previous attempt start;
- if the previous attempt completes before that time, the wrapper waits the
  remaining interval;
- if the previous attempt takes 900 seconds or longer, the next attempt begins
  as soon as the previous attempt has completed and its evidence has been
  persisted.

Attempts must never overlap.

The cadence must not be changed in response to observed market conditions.

The operator must not manually accelerate, delay, skip, or repeat a scheduled
attempt because of observed Kuru or Coinbase market behavior.

The ten qualifying capture windows remain separate capture windows and are not
claimed to be statistically independent.

### Technical acceptance rule

The authoritative technical acceptance condition for an individual attempt is:

`capture["gate"]["overall"] == "PASS"`

The existing dual-source gate must not be manually overridden.

A qualifying Phase 3 capture must additionally preserve:

- `schema_version == "phase0.dual_ws_capture.v1"`;
- `requested_duration_seconds == 120`;
- the expected Kuru and Coinbase source identities;
- the raw JSON capture;
- a verified SHA256 sidecar produced from the persisted capture bytes.

The existing overall source gate requires its Kuru, Coinbase, and temporal
overlap components to pass.

A `REVIEW` attempt is not a qualifying confirmatory capture.

A `REVIEW` attempt must not be upgraded manually.

### First-ten rule

The confirmatory dataset is the **first ten chronologically observed attempts
that satisfy the frozen technical acceptance rule**.

Qualifying captures must not be ranked, substituted, or selected according to
their market values or eventual Phase 3 results.

A technically non-qualifying attempt remains part of the collection audit
trail but does not count toward the ten qualifying captures.

Collection continues on the same frozen cadence until ten qualifying captures
have been persisted.

Collection stops after the tenth qualifying capture has been persisted.

No additional capture may be added to the confirmatory dataset because the
economic result from the first ten qualifying captures appears unfavorable.

### Collection-time information boundary

During confirmatory collection, the series wrapper may display only technical
or operational information required to supervise acquisition, including:

- attempt index;
- capture filename;
- capture SHA256;
- source gate status;
- technical source-status counts;
- connection or persistence errors;
- number of qualifying captures accumulated.

The collection wrapper must not display:

- Kuru prices;
- Coinbase prices;
- best bid or offer values;
- midpoint values;
- spread values;
- proposed-versus-finalized disagreement values;
- future returns;
- absolute future moves;
- volatility statistics;
- correlation statistics;
- Phase 3 support classifications.

The existing single-capture summary output is therefore not used as the
operator-facing output for the automated confirmatory series.

### Attempt preservation

Every attempted capture must be persisted before another attempt begins.

For every attempt, the collection audit trail must preserve:

- chronological attempt index;
- session start UTC;
- session completion UTC;
- raw capture filename;
- SHA256 sidecar filename;
- verified capture SHA256;
- overall gate status;
- Kuru gate status;
- Coinbase gate status;
- temporal-overlap gate status;
- whether the attempt qualifies for the confirmatory sample.

Technical `REVIEW` attempts must remain preserved.

They must not be deleted merely because they failed to qualify.

### Ordered manifest

The collection wrapper must create a deterministic ordered manifest with schema:

`phase3.confirmatory_capture_series.v1`

The manifest must bind:

- the Phase 3 methodology contract SHA256;
- the Git commit containing the committed methodology;
- the frozen duration and cadence;
- every attempted capture in chronological order;
- every capture SHA256;
- every technical gate status;
- the exact ten qualifying capture identities;
- qualifying and non-qualifying attempt counts;
- the UTC series start and completion times.

The manifest itself must be serialized deterministically and receive its own
SHA256 sidecar.

The ordered set of ten qualifying capture hashes must be used to derive the
frozen Phase 3 confirmatory dataset fingerprint.

### Interruption handling

If collection is interrupted before ten qualifying captures exist, Phase 3
confirmatory economics must not be inspected.

Collection may resume only by preserving the already recorded attempt history
and continuing the same confirmatory series.

Previously persisted attempts must not be discarded in order to restart from a
more favorable market period.

If the collection protocol itself must be changed, the existing confirmatory
series is abandoned before economic inspection and a new methodology revision
must be committed before a replacement confirmatory series begins.

## Confirmatory Dataset

The confirmatory Phase 3 dataset must be collected only after this methodology
contract has been committed.

Target dataset:

**10 qualifying dual-WebSocket capture windows**

Target duration per qualifying capture:

**120 seconds**

A capture is qualifying only through pre-specified technical/source-integrity
criteria.

Capture acceptance must not depend on:

- Kuru disagreement magnitude;
- Coinbase future movement;
- correlation;
- volatility;
- whether the result appears favorable.

Collection continues until ten technically qualifying captures exist.

Failed technical captures must remain auditable and must not be silently
replaced because of economic behavior.

The ten qualifying windows are separate capture windows.

They are not claimed to be statistically independent.

## Out-of-Sample Rule

The following five historical captures are explicitly excluded from the Phase
3 confirmatory economic sample:

- `dual_ws_20260906T011119618860Z.json`
- `dual_ws_20260906T011253398169Z.json`
- `dual_ws_20260906T011426627600Z.json`
- `dual_ws_20260906T011600173225Z.json`
- `dual_ws_20260906T011733287613Z.json`

They were already used for Phase 1 and Phase 2 research and have already had
economic outcomes inspected.

They remain feasibility evidence only.

## No Post-Hoc Rescue

After confirmatory Phase 3 economic outcomes are inspected, the following may
not be promoted as confirmatory evidence unless separately pre-registered on a
new out-of-sample dataset:

- a new future horizon;
- a minimum disagreement threshold;
- a maximum disagreement threshold;
- a hand-selected exposure bucket;
- a selected capture subset;
- a selected market regime;
- an alternative state pair;
- signed directional rules;
- regression specifications;
- nonlinear transformations selected because they improve results;
- alternative outcome definitions selected because they improve results.

Exploratory follow-up is permitted only when explicitly labelled exploratory.

## Statistical Boundary

The initial Phase 3 analysis is descriptive.

The initial confirmatory report does not introduce:

- p-values;
- hypothesis-test significance thresholds;
- confidence intervals;
- regression coefficients;
- predictive-accuracy statistics;
- trading-performance statistics.

Any later inferential analysis requires a separately defined methodology.

## Claim Boundaries

Phase 3 may describe:

- observed simultaneous Kuru state disagreement magnitude;
- subsequent Coinbase midpoint-movement magnitude;
- descriptive rank association;
- capture-level consistency;
- frozen-horizon sensitivity;
- baseline-freshness sensitivity;
- censoring and source-integrity evidence.

Phase 3 does not establish:

- prediction;
- alpha;
- arbitrage;
- profitability;
- venue leadership;
- causal finality effects;
- protocol-finality latency;
- realized adverse selection;
- execution probability;
- a price of finality;
- a universal relationship between Kuru and Coinbase.

## Reproducibility Requirements

The final confirmatory analysis must preserve:

- ordered source capture identities;
- source SHA256 hashes;
- deterministic dataset fingerprint;
- methodology schema version;
- exact Decimal arithmetic for market values;
- frozen threshold and horizon grid;
- capture-level eligibility counts;
- right-censoring counts;
- source-integrity failures;
- deterministic report serialization;
- deterministic report SHA256;
- full synthetic and repository regression tests.

## Research Decision

The Phase 3 result will be interpreted only after:

1. this contract is committed;
2. fresh confirmatory data is collected;
3. implementation is tested against synthetic cases;
4. source-integrity and reconstruction gates pass;
5. the deterministic report is generated from the frozen confirmatory dataset.

No economic result may alter this contract retroactively.
