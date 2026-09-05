# Kuru MON-USDC Normalization Evidence

## Objective

Establish the deterministic relationship between Kuru REST order-book values and the same-block on-chain OrderBook representation without inferring units from Coinbase.

## Observation

Committed Monad block:

`102218987`

### REST committed snapshot

- best bid raw: `25184000000000000`
- best ask raw: `25189000000000000`
- best bid quantity raw: `992530000000000`
- best ask quantity raw: `992490000000000`

### Same-block `getL2Book(1,1)`

Decoded values:

- block number: `102218987`
- bid internal price: `2518400`
- bid raw size: `992530000000000`
- separator: `0`
- ask internal price: `2518900`
- ask raw size: `992490000000000`

### Market parameters

- price precision: `100000000` (`1e8`)
- size precision: `10000000000` (`1e10`)
- base asset: native MON
- base asset decimals: `18`
- quote asset: USDC
- quote asset decimals: `6`

## Price verification

For the bid:

`2518400 / 1e8 = 0.025184`

`25184000000000000 / 1e18 = 0.025184`

For the ask:

`2518900 / 1e8 = 0.025189`

`25189000000000000 / 1e18 = 0.025189`

Therefore, for this market and representation:

`human_price = REST_price_raw / 1e18`

which is equivalent to:

`human_price = internal_L2_price / pricePrecision`

## Quantity verification

REST quantities matched the raw sizes returned by `getL2Book` exactly.

Bid:

`992530000000000 / 1e10 = 99253 MON`

Ask:

`992490000000000 / 1e10 = 99249 MON`

Therefore:

`human_base_size = REST_quantity_raw / sizePrecision`

## Claim boundary

This experiment establishes numeric representation and normalization for the observed MON-USDC L2 data.

It does not establish whether an individual displayed level originates exclusively from resting limit orders, integrated backstop-AMM liquidity, or a combination of liquidity sources.

Coinbase data was not used to determine Kuru units.
