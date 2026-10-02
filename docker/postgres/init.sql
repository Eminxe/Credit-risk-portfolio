BEGIN;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE TABLE IF NOT EXISTS risk.runs (
    run_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    source_sha256 text NOT NULL,
    score_sha256 text NOT NULL,
    assumptions jsonb NOT NULL,
    metadata jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS risk.customer_scores (
    run_id text NOT NULL REFERENCES risk.runs(run_id),
    customer_id integer NOT NULL,
    pd_1m double precision NOT NULL CHECK (pd_1m BETWEEN 0 AND 1),
    observed_default smallint NOT NULL CHECK (observed_default IN (0,1)),
    prediction_type text NOT NULL CHECK (prediction_type IN ('holdout','out_of_fold')),
    limit_twd double precision NOT NULL CHECK (limit_twd > 0),
    PRIMARY KEY (run_id, customer_id)
);
CREATE TABLE IF NOT EXISTS risk.customer_economics (
    run_id text NOT NULL,
    customer_id integer NOT NULL,
    npv_twd double precision NOT NULL,
    expected_loss_twd double precision NOT NULL CHECK (expected_loss_twd >= 0),
    PRIMARY KEY (run_id, customer_id),
    FOREIGN KEY (run_id, customer_id) REFERENCES risk.customer_scores(run_id, customer_id)
);
CREATE TABLE IF NOT EXISTS risk.limit_strategy (
    run_id text NOT NULL,
    customer_id integer NOT NULL,
    scenario_limit_twd double precision NOT NULL CHECK (scenario_limit_twd >= 0),
    scenario_pd_1m double precision NOT NULL CHECK (scenario_pd_1m BETWEEN 0 AND 1),
    npv_twd double precision NOT NULL,
    expected_loss_twd double precision NOT NULL CHECK (expected_loss_twd >= 0),
    PRIMARY KEY (run_id, customer_id),
    FOREIGN KEY (run_id, customer_id) REFERENCES risk.customer_scores(run_id, customer_id)
);
COMMIT;
