-- One row per run; aggregate before joining to preserve customer grain.
SELECT run_id, COUNT(*) AS customers, AVG(pd_1m) AS mean_monthly_pd,
       AVG(observed_default) AS observed_default_rate
FROM risk.customer_scores
GROUP BY run_id;
