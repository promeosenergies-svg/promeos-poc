# SGE4.5 — Retarget Existing Enedis Raw Pipeline To `flux_data.db`

> **Status**: BUILD
> **Depends on**: SF1-SF4 complete
> **Goal**: keep the current Enedis raw ingestion pipeline intact while moving its raw archive/control tables out of `promeos.db`

## Summary

This step does not create a second ingestion system.

It keeps the existing Enedis CLI/API/parsers/idempotence/retry/republication flow and changes only the persistence boundary:

- raw Enedis archive tables move to `flux_data.db`
- `promeos.db` stays focused on product-facing and promoted data
- later promotion reads raw rows from `flux_data.db` and writes functional rows to `promeos.db`

## Key Decisions

- Reuse the existing pipeline; do not fork or dual-write it
- Introduce `FLUX_DATA_DATABASE_URL` for the raw archive
- Keep `DATABASE_URL` as the main app DB contract
- Adopt legacy `enedis.db` by rename when `flux_data.db` is absent
- Keep promotion/audit/product tables in `promeos.db`

## Result

After SGE4.5:

- `python -m data_ingestion.enedis.cli ingest` behaves the same for the user
- `/api/enedis/*` raw-ingestion endpoints behave the same for the user
- raw tables bootstrap in `flux_data.db`
- raw tables are no longer recreated in `promeos.db`
