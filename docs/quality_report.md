# Báo cáo chất lượng dữ liệu

> File sinh tự động bởi `make quality` (quality/runner.py). Không sửa tay.

- Lần chạy: `1be486c2-97f5-41e5-b238-b0bf02b00daf` lúc 2026-10-05 13:42 UTC
- Tổng check: 22 · error fail: **0** · warning fail: **0**
- Kết luận: Đạt — pipeline được đi tiếp

| Kết quả | Mức | Nguồn | Check | Đo được | Ngưỡng |
|---|---|---|---|---|---|
| PASS | error | dbt | `dbt:not_null_dim_entity_entity_id` | 0 | == 0 |
| PASS | error | dbt | `dbt:not_null_dim_entity_entity_key` | 0 | == 0 |
| PASS | error | dbt | `dbt:not_null_fct_main_entity_key` | 0 | == 0 |
| PASS | error | dbt | `dbt:not_null_fct_main_event_date` | 0 | == 0 |
| PASS | error | dbt | `dbt:not_null_fct_main_record_id` | 0 | == 0 |
| PASS | error | dbt | `dbt:not_null_stg_source_demo__records_row_hash` | 0 | == 0 |
| PASS | error | dbt | `dbt:relationships_fct_main_entity_key__entity_key__ref_dim_entity_` | 0 | == 0 |
| PASS | error | dbt | `dbt:unique_dim_entity_entity_id` | 0 | == 0 |
| PASS | error | dbt | `dbt:unique_dim_entity_entity_key` | 0 | == 0 |
| PASS | error | dbt | `dbt:unique_fct_main_record_id` | 0 | == 0 |
| PASS | error | dbt | `dbt:unique_stg_source_demo__records_row_hash` | 0 | == 0 |
| PASS | error | rules | `dim_entity_pk_unique_not_null` | 0 | == 0 |
| PASS | error | rules | `fct_main_grain_unique` | 0 | == 0 |
| PASS | error | rules | `fct_main_no_orphan_entity` | 0 | == 0 |
| PASS | error | rules | `fct_main_not_empty` | 4926 | > 0 |
| PASS | error | rules | `raw_to_core_row_reconciliation` | 0.0148 | <= 0.05 |
| PASS | warning | dbt | `dbt:accepted_values_dim_entity_category__A__B__C__D` | 0 | == 0 |
| PASS | warning | rules | `fct_main_event_date_in_range` | 0 | == 0 |
| PASS | warning | rules | `fct_main_measure_outlier_rate` | 0.0019 | <= 0.005 |
| PASS | warning | rules | `fct_main_null_rate_measure` | 0.0177 | <= 0.05 |
| PASS | warning | rules | `fct_main_unknown_entity_rate` | 0.0049 | <= 0.01 |
| PASS | warning | rules | `latest_batch_freshness_days` | 0.0004 | <= 7 |
