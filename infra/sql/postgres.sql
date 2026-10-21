CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    randomization_unit TEXT NOT NULL,
    primary_metric TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS experiment_variants (
    experiment_id TEXT REFERENCES experiments(experiment_id),
    variant TEXT NOT NULL,
    allocation_basis_points INTEGER NOT NULL CHECK (allocation_basis_points BETWEEN 0 AND 10000),
    PRIMARY KEY (experiment_id, variant)
);

CREATE TABLE IF NOT EXISTS model_releases (
    model_version TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,
    artifact_uri TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

