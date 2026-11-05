-- Analyst queries over the loaded PostgreSQL schema (docker/postgres/init.sql).
-- Each query reads the latest verified run. CI executes this file against the fresh
-- database after the real-data pipeline, so every query is checked on real outputs.

-- 1. Risk deciles on the untouched holdout: observed vs predicted default rate,
--    cumulative capture of defaulters and the KS statistic per cut-off.
WITH latest AS (
    SELECT run_id FROM risk.runs ORDER BY created_at DESC LIMIT 1
), holdout AS (
    SELECT s.pd_1m, s.observed_default,
           NTILE(10) OVER (ORDER BY s.pd_1m DESC, s.customer_id) AS risk_decile
    FROM risk.customer_scores s
    JOIN latest USING (run_id)
    WHERE s.prediction_type = 'holdout'
), deciles AS (
    SELECT risk_decile, COUNT(*) AS clients, SUM(observed_default) AS defaults,
           AVG(observed_default) AS observed_rate, AVG(pd_1m) AS mean_pd
    FROM holdout
    GROUP BY risk_decile
)
SELECT risk_decile,                                     -- 1 = highest predicted risk
       clients, defaults,
       ROUND(observed_rate::numeric, 4) AS observed_rate,
       ROUND(mean_pd::numeric, 4) AS mean_pd,
       ROUND((SUM(defaults) OVER w / SUM(defaults) OVER ())::numeric, 4) AS cum_share_bads,
       ROUND((SUM(clients - defaults) OVER w / SUM(clients - defaults) OVER ())::numeric, 4)
           AS cum_share_goods,
       ROUND((SUM(defaults) OVER w / SUM(defaults) OVER ()
              - SUM(clients - defaults) OVER w / SUM(clients - defaults) OVER ())::numeric, 4)
           AS ks_at_cutoff
FROM deciles
WINDOW w AS (ORDER BY risk_decile)
ORDER BY risk_decile;

-- 2. Approval cut-off simulation on the holdout: approve clients below a PD threshold
--    and report approval rate and the bad rate among approved clients.
WITH latest AS (
    SELECT run_id FROM risk.runs ORDER BY created_at DESC LIMIT 1
), holdout AS (
    SELECT s.pd_1m, s.observed_default
    FROM risk.customer_scores s
    JOIN latest USING (run_id)
    WHERE s.prediction_type = 'holdout'
)
SELECT cutoff,
       ROUND(AVG((pd_1m < cutoff)::int)::numeric, 4) AS approval_rate,
       ROUND((SUM(observed_default) FILTER (WHERE pd_1m < cutoff)::numeric
              / NULLIF(COUNT(*) FILTER (WHERE pd_1m < cutoff), 0)), 4) AS approved_bad_rate,
       ROUND((SUM(observed_default) FILTER (WHERE pd_1m >= cutoff)::numeric
              / NULLIF(SUM(observed_default), 0)), 4) AS share_of_bads_declined
FROM holdout
CROSS JOIN (VALUES (0.10), (0.15), (0.20), (0.30), (0.50)) AS c(cutoff)
GROUP BY cutoff
ORDER BY cutoff;

-- 3. Expected loss, exposure and scenario NPV by predicted-risk decile (all clients).
WITH latest AS (
    SELECT run_id FROM risk.runs ORDER BY created_at DESC LIMIT 1
), joined AS (
    SELECT s.pd_1m, s.limit_twd, e.expected_loss_twd, e.npv_twd,
           NTILE(10) OVER (ORDER BY s.pd_1m, s.customer_id) AS risk_decile
    FROM risk.customer_scores s
    JOIN risk.customer_economics e USING (run_id, customer_id)
    JOIN latest USING (run_id)
)
SELECT risk_decile,                                     -- 10 = highest predicted risk
       COUNT(*) AS clients,
       ROUND(AVG(pd_1m)::numeric, 4) AS mean_pd_1m,
       ROUND((SUM(limit_twd) / 1e6)::numeric, 1) AS limits_m_twd,
       ROUND((SUM(expected_loss_twd) / 1e6)::numeric, 1) AS el_m_twd,
       ROUND((SUM(npv_twd) / 1e6)::numeric, 1) AS npv_m_twd,
       ROUND((SUM(expected_loss_twd) / SUM(SUM(expected_loss_twd)) OVER ())::numeric, 4)
           AS share_of_el
FROM joined
GROUP BY risk_decile
ORDER BY risk_decile;

-- 4. Limit strategy: how many clients move to each limit multiplier and what it changes.
WITH latest AS (
    SELECT run_id FROM risk.runs ORDER BY created_at DESC LIMIT 1
)
SELECT ROUND((l.scenario_limit_twd / s.limit_twd)::numeric, 2) AS limit_multiplier,
       COUNT(*) AS clients,
       ROUND(AVG(s.pd_1m)::numeric, 4) AS mean_pd_before,
       ROUND(AVG(l.scenario_pd_1m)::numeric, 4) AS mean_pd_after,
       ROUND((SUM(l.npv_twd - e.npv_twd) / 1e6)::numeric, 2) AS npv_change_m_twd,
       ROUND((SUM(l.expected_loss_twd - e.expected_loss_twd) / 1e6)::numeric, 2)
           AS el_change_m_twd
FROM risk.limit_strategy l
JOIN risk.customer_scores s USING (run_id, customer_id)
JOIN risk.customer_economics e USING (run_id, customer_id)
JOIN latest USING (run_id)
GROUP BY 1
ORDER BY 1;

-- 5. LendingClub vintages from the versioned aggregate store: eligible monthly cohorts,
--    charge-off rate and its moving average over the current and two prior calendar months
--    (a RANGE frame, so gaps between eligible cohorts are not bridged).
WITH latest AS (
    SELECT run_id FROM risk.additional_runs
    WHERE case_number = 6 ORDER BY created_at DESC LIMIT 1
), vintages AS (
    SELECT (a.payload->>'issue_month')::date AS issue_month,
           (a.payload->>'n')::int AS loans,
           (a.payload->>'terminal_chargeoff_rate')::numeric AS chargeoff_rate
    FROM risk.aggregate_results a
    JOIN latest USING (run_id)
    WHERE a.artifact = 'case06_vintages.csv' AND (a.payload->>'eligible')::boolean
)
SELECT issue_month, loans,
       ROUND(chargeoff_rate, 4) AS chargeoff_rate,
       ROUND(AVG(chargeoff_rate) OVER (ORDER BY issue_month
                                       RANGE BETWEEN INTERVAL '2 months' PRECEDING
                                             AND CURRENT ROW), 4)
           AS chargeoff_rate_3m_avg
FROM vintages
ORDER BY issue_month;
