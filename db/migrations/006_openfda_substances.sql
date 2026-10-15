
-- 006: raw table for openFDA substance dictionary.

create table raw.openfda_substances (
    spl_id        text,
    substance_name text,
    rxcui          text,
    _batch_id      uuid        not null references meta.ingestion_batch (batch_id),
    _source_name   text        not null,
    _ingested_at   timestamptz not null default now(),
    _row_hash      text        not null,
    _payload       jsonb
);

create unique index openfda_substances_row_hash_uq
    on raw.openfda_substances (_row_hash);

create index openfda_substances_batch_id_idx
    on raw.openfda_substances (_batch_id);

comment on table raw.openfda_substances is
    'Raw dictionary of substance names extracted from openFDA drug labels.';
comment on column raw.openfda_substances.substance_name is
    'JSON text array of substance names as returned by openFDA.';
comment on column raw.openfda_substances.rxcui is
    'JSON text array of RxCUI identifiers; nullable when absent from source.';
