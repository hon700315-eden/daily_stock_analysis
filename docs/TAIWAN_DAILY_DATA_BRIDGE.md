# Taiwan Daily Data Bridge

This bridge lets `daily_stock_analysis` read the existing
`TW_Stock_Dashboard_Clean` daily outputs without changing that upstream system.

## Data Products

Read priority:

1. `06_dashboard_sync/latest_screening_package.json`
2. `dashboard-app/public/dashboard-data/latest_screening_package.json`
3. `01_market_data/daily_snapshot/trade_date=YYYY-MM-DD/daily_market_normalized.csv`

The snapshot fallback only uses directories that contain both
`daily_market_normalized.csv` and `snapshot_manifest.json`; empty holiday
directories are ignored.

## Configuration

`TW_STOCK_DATA_ROOT` is optional. It can point to the synchronized
`TW_Stock_Dashboard_Clean` root, a Drive root with the same contracts, or a
single `latest_screening_package.json` file.

When unset, the bridge checks:

`/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean`

## Symbol Mapping

Only explicit upstream markets are mapped:

- `market=TWSE`, `code=2330` -> `2330.TW`
- `market=TPEX`, `code=6488` -> `6488.TWO`

Codes already ending in `.TW` or `.TWO` are left unchanged. Unknown markets are
not guessed. Bare codes such as `2330` are resolved only when the existing
package or snapshot contains exactly one matching market/code row; ambiguous
matches fail clearly.

The public helper accepts both `(market, code)` and `(code, market)` argument
orders so external smoke checks can verify the same explicit mapping without
changing the bridge's internal row-reading call sites.

## `pct_chg`

`pct_chg` is a percentage-point number, matching the existing
`daily_stock_analysis` `pct_chg` / `change_pct` contract.

Source priority:

1. Existing package percentage fields: `pct_chg`, `change_pct`,
   `changePercent`, `change_pct_value`
2. Latest two `chartSeries` closes:
   `((latest_close - previous_close) / previous_close) * 100`
3. For snapshot fallback, latest close and the previous valid snapshot close:
   `((latest_close - previous_close) / previous_close) * 100`
4. `None` when previous close is missing, zero, or invalid

The upstream snapshot `change` field is a price delta and is not used as
`pct_chg`.

## Missing Data

If a stock is absent from the package/snapshot, the bridge returns no result and
the existing provider fallback continues. Damaged package/snapshot files or
missing required snapshot columns raise a provider error so fake market data is
not produced.

Snapshot `volume_shares` is preserved as shares. Package `volumeShares` is used
when present; no conversion to lots is performed by this bridge.

## Upstream Contract

This bridge is read-only. It does not modify `TW_Stock_Dashboard_Clean`, its L2,
L3, L5, L6, or L7 jobs, Drive layout, dashboard package schema, snapshots, or
published fields.
