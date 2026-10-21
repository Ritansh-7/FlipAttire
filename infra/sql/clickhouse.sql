CREATE DATABASE IF NOT EXISTS hm;

CREATE TABLE IF NOT EXISTS hm.customer_events
(
    event_id UUID,
    event_type LowCardinality(String),
    customer_id String,
    article_id Nullable(String),
    surface LowCardinality(String),
    request_id Nullable(String),
    experiment_id Nullable(String),
    variant Nullable(String),
    event_time DateTime64(3, 'UTC'),
    metadata_json String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, experiment_id, customer_id, event_time);

CREATE TABLE IF NOT EXISTS hm.recommendation_exposures
(
    event_id UUID,
    customer_id String,
    article_id String,
    surface LowCardinality(String),
    position UInt16,
    experiment_id String,
    variant String,
    model_version String,
    policy_version String,
    request_id String,
    event_time DateTime64(3, 'UTC')
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (experiment_id, variant, customer_id, event_time);

