-- =============================================================================
-- Step 3 — Analytical SQL
-- =============================================================================
-- Executed by `scripts/03_analysis.py` against `data/processed/analytics.db`,
-- table `posts` (built by `scripts/02_clean_features.py`).
--
-- Conventions used everywhere below
--   * `is_vertical = 1`    -> sport / fitness / wellness vertical
--                             (category IN Fitness, Sports, Health)
--   * `rate_valid = 1`     -> engagement_total <= views, i.e. the row can carry
--                             a meaningful view-based rate (295 rows dropped)
--
-- Every block is delimited by `-- @name:<identifier>` so the runner can execute
-- them independently and key the JSON output. Blocks are plain SQLite and can be
-- pasted into any SQLite shell:
--
--     sqlite3 data/processed/analytics.db < sql/analysis_queries.sql
--
-- Central tendency: SQLite has no MEDIAN(), so it is derived with ROW_NUMBER()
-- over a partition and averaging the one or two middle rows
-- (`rn IN ((cnt+1)/2, (cnt+2)/2)`). Integer division in SQLite makes this exact
-- for both odd and even group sizes.
-- =============================================================================


-- @name:q01_overview
-- Headline KPI block: whole corpus -> vertical -> benchmark.
SELECT
    CASE WHEN is_vertical = 1 THEN 'vertical' ELSE 'benchmark' END AS scope,
    COUNT(*)                                            AS posts,
    SUM(views)                                          AS total_views,
    SUM(engagement_total)                               AS total_engagement,
    ROUND(AVG(er_view), 4)                              AS mean_er_view,
    ROUND(AVG(deep_rate), 4)                            AS mean_deep_rate,
    ROUND(AVG(reach_ratio), 4)                          AS mean_reach_ratio,
    ROUND(AVG(eng_per_1k_fans), 2)                      AS mean_eng_per_1k_fans,
    ROUND(AVG(follower_count), 0)                       AS mean_followers,
    ROUND(100.0 * SUM(shares + saves) / SUM(views), 4)  AS deep_rate_pooled,
    ROUND(100.0 * SUM(engagement_total) / SUM(views), 4) AS er_view_pooled
FROM posts
WHERE rate_valid = 1
GROUP BY is_vertical;


-- @name:q02_platform
-- Q1 · Which platform earns attention in the vertical?
-- median ER (primary), pooled rates and volume per platform.
WITH base AS (
    SELECT platform, er_view,
           ROW_NUMBER() OVER (PARTITION BY platform ORDER BY er_view) AS rn,
           COUNT(*)     OVER (PARTITION BY platform)                  AS cnt
    FROM posts WHERE is_vertical = 1 AND rate_valid = 1
)
SELECT
    p.platform                                              AS platform,
    COUNT(*)                                                AS n,
    ROUND(AVG(p.er_view), 4)                                AS mean_er_view,
    ROUND(AVG(p.deep_rate), 4)                              AS mean_deep_rate,
    ROUND(AVG(p.share_rate), 4)                             AS mean_share_rate,
    ROUND(AVG(p.save_rate), 4)                              AS mean_save_rate,
    ROUND(AVG(p.comment_rate), 4)                           AS mean_comment_rate,
    ROUND(AVG(p.reach_ratio), 4)                            AS mean_reach_ratio,
    ROUND(AVG(p.eng_per_1k_fans), 2)                        AS mean_eng_per_1k_fans,
    SUM(p.views)                                            AS total_views,
    SUM(p.engagement_total)                                 AS total_engagement,
    ROUND(100.0 * SUM(p.engagement_total) / SUM(p.views), 4) AS er_view_pooled,
    (SELECT ROUND(AVG(b.er_view), 4) FROM base b
      WHERE b.platform = p.platform AND b.rn IN ((b.cnt+1)/2, (b.cnt+2)/2)) AS median_er_view
FROM posts p
WHERE p.is_vertical = 1 AND p.rate_valid = 1
GROUP BY p.platform
ORDER BY median_er_view DESC;


-- @name:q03_tier
-- Q2 · Which creator tier delivers the best interaction per view?
WITH base AS (
    SELECT influencer_tier, er_view,
           ROW_NUMBER() OVER (PARTITION BY influencer_tier ORDER BY er_view) AS rn,
           COUNT(*)     OVER (PARTITION BY influencer_tier)                  AS cnt
    FROM posts WHERE is_vertical = 1 AND rate_valid = 1
)
SELECT
    t.influencer_tier                                        AS influencer_tier,
    t.tier_rank                                              AS tier_rank,
    COUNT(*)                                                 AS n,
    ROUND(AVG(t.follower_count), 0)                          AS mean_followers,
    ROUND(AVG(t.eng_per_1k_fans), 2)                         AS mean_eng_per_1k_fans,
    ROUND(AVG(t.reach_ratio), 4)                             AS mean_reach_ratio,
    ROUND(AVG(t.deep_rate), 4)                               AS mean_deep_rate,
    SUM(t.views)                                             AS total_views,
    SUM(t.engagement_total)                                  AS total_engagement,
    ROUND(AVG(t.engagement_total), 1)                        AS mean_engagement_per_post,
    ROUND(100.0 * SUM(t.engagement_total) / SUM(t.views), 4)  AS er_view_pooled,
    (SELECT ROUND(AVG(b.er_view), 4) FROM base b
      WHERE b.influencer_tier = t.influencer_tier
        AND b.rn IN ((b.cnt+1)/2, (b.cnt+2)/2))              AS median_er_view
FROM posts t
WHERE t.is_vertical = 1 AND t.rate_valid = 1
GROUP BY t.influencer_tier, t.tier_rank
ORDER BY t.tier_rank;


-- @name:q04_content_family
-- Q3 · Which creative family works? (17 native labels folded into 5 families)
WITH base AS (
    SELECT content_family, er_view,
           ROW_NUMBER() OVER (PARTITION BY content_family ORDER BY er_view) AS rn,
           COUNT(*)     OVER (PARTITION BY content_family)                  AS cnt
    FROM posts WHERE is_vertical = 1 AND rate_valid = 1
)
SELECT
    c.content_family                                         AS content_family,
    COUNT(*)                                                 AS n,
    ROUND(AVG(c.deep_rate), 4)                               AS mean_deep_rate,
    ROUND(AVG(c.save_rate), 4)                               AS mean_save_rate,
    ROUND(AVG(c.share_rate), 4)                              AS mean_share_rate,
    ROUND(AVG(c.comment_rate), 4)                            AS mean_comment_rate,
    ROUND(AVG(c.views), 0)                                   AS mean_views,
    SUM(c.views)                                             AS total_views,
    SUM(c.engagement_total)                                  AS total_engagement,
    ROUND(100.0 * SUM(c.engagement_total) / SUM(c.views), 4)  AS er_view_pooled,
    (SELECT ROUND(AVG(b.er_view), 4) FROM base b
      WHERE b.content_family = c.content_family
        AND b.rn IN ((b.cnt+1)/2, (b.cnt+2)/2))              AS median_er_view
FROM posts c
WHERE c.is_vertical = 1 AND c.rate_valid = 1
GROUP BY c.content_family
ORDER BY median_er_view DESC;


-- @name:q05_content_type_detail
-- Same cut on the raw 17 native labels, for drill-down in the report appendix.
SELECT content_type,
       COUNT(*)                                              AS n,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled,
       ROUND(AVG(deep_rate), 4)                              AS mean_deep_rate
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY content_type
HAVING COUNT(*) >= 25
ORDER BY er_view_pooled DESC;


-- @name:q06_timing_weekday_slot
-- Q4 · When to publish: 7 weekdays x 4 day-parts (28 cells, ~40 posts each).
SELECT weekday,
       CASE WHEN weekday = 'Monday'    THEN 1 WHEN weekday = 'Tuesday'  THEN 2
            WHEN weekday = 'Wednesday' THEN 3 WHEN weekday = 'Thursday' THEN 4
            WHEN weekday = 'Friday'    THEN 5 WHEN weekday = 'Saturday' THEN 6
            ELSE 7 END                                       AS weekday_no,
       time_slot,
       COUNT(*)                                              AS n,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled,
       ROUND(100.0 * SUM(shares + saves) / SUM(views), 4)     AS deep_rate_pooled,
       ROUND(AVG(views), 0)                                  AS mean_views
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY weekday, time_slot
ORDER BY weekday_no, time_slot;


-- @name:q07_timing_hour
-- Hour-of-day profile (24 buckets, pooled rate so thin cells stay readable).
SELECT hour,
       COUNT(*)                                              AS n,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled,
       ROUND(100.0 * SUM(shares + saves) / SUM(views), 4)     AS deep_rate_pooled
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY hour
ORDER BY hour;


-- @name:q08_timing_weekend
SELECT CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       COUNT(*)                                              AS n,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled,
       ROUND(100.0 * SUM(shares + saves) / SUM(views), 4)     AS deep_rate_pooled
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY is_weekend;


-- @name:q09_budget_tier
-- Q5 · Budget model inputs by tier. Cost is NOT in the dataset: the runner
-- applies an explicit CPM assumption (see scripts/03_analysis.py, CPM_DEFAULT).
SELECT influencer_tier                                       AS influencer_tier,
       tier_rank                                             AS tier_rank,
       COUNT(*)                                              AS n,
       ROUND(AVG(follower_count), 0)                         AS mean_followers,
       ROUND(AVG(engagement_total), 1)                       AS mean_engagement_per_post,
       ROUND(AVG(views), 0)                                  AS mean_views,
       SUM(engagement_total)                                 AS total_engagement,
       SUM(views)                                            AS total_views
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY influencer_tier, tier_rank
ORDER BY tier_rank;


-- @name:q10_budget_platform
SELECT platform                                              AS platform,
       COUNT(*)                                              AS n,
       ROUND(AVG(follower_count), 0)                         AS mean_followers,
       ROUND(AVG(engagement_total), 1)                       AS mean_engagement_per_post,
       ROUND(AVG(views), 0)                                  AS mean_views
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY platform
ORDER BY n DESC;


-- @name:q11_segment
-- Inside the vertical: Fitness vs Sports vs Health.
WITH base AS (
    SELECT vertical_segment, er_view,
           ROW_NUMBER() OVER (PARTITION BY vertical_segment ORDER BY er_view) AS rn,
           COUNT(*)     OVER (PARTITION BY vertical_segment)                  AS cnt
    FROM posts WHERE is_vertical = 1 AND rate_valid = 1
)
SELECT s.vertical_segment                                    AS vertical_segment,
       COUNT(*)                                              AS n,
       ROUND(AVG(s.deep_rate), 4)                            AS mean_deep_rate,
       ROUND(AVG(s.eng_per_1k_fans), 2)                      AS mean_eng_per_1k_fans,
       SUM(s.views)                                          AS total_views,
       SUM(s.engagement_total)                               AS total_engagement,
       ROUND(100.0 * SUM(s.engagement_total) / SUM(s.views), 4) AS er_view_pooled,
       (SELECT ROUND(AVG(b.er_view), 4) FROM base b
         WHERE b.vertical_segment = s.vertical_segment
           AND b.rn IN ((b.cnt+1)/2, (b.cnt+2)/2))           AS median_er_view
FROM posts s
WHERE s.is_vertical = 1 AND s.rate_valid = 1
GROUP BY s.vertical_segment
ORDER BY median_er_view DESC;


-- @name:q12_hashtag
-- Does hashtag volume still buy reach?
SELECT hashtag_bucket                                        AS hashtag_bucket,
       CASE hashtag_bucket WHEN '0' THEN 0 WHEN '1-5' THEN 1 WHEN '6-10' THEN 2
                           WHEN '11-20' THEN 3 WHEN '21-30' THEN 4 ELSE 5 END AS bucket_no,
       COUNT(*)                                              AS n,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled,
       ROUND(100.0 * SUM(shares + saves) / SUM(views), 4)     AS deep_rate_pooled
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY hashtag_bucket
ORDER BY bucket_no;


-- @name:q13_monthly_trend
-- 24 months of posting volume and efficiency.
SELECT year_month                                            AS year_month,
       COUNT(*)                                              AS n,
       SUM(views)                                            AS total_views,
       SUM(engagement_total)                                 AS total_engagement,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY year_month
ORDER BY year_month;


-- @name:q14_verified
SELECT CASE WHEN is_verified = 1 THEN 'Verified' ELSE 'Not verified' END AS verified,
       COUNT(*)                                              AS n,
       ROUND(AVG(follower_count), 0)                         AS mean_followers,
       ROUND(100.0 * SUM(engagement_total) / SUM(views), 4)   AS er_view_pooled,
       ROUND(100.0 * SUM(shares + saves) / SUM(views), 4)     AS deep_rate_pooled
FROM posts
WHERE is_vertical = 1 AND rate_valid = 1
GROUP BY is_verified;


-- @name:q15_follower_band
-- Complementary cut to the skewed tier column: a continuous fan-base split.
WITH base AS (
    SELECT follower_band, er_view,
           ROW_NUMBER() OVER (PARTITION BY follower_band ORDER BY er_view) AS rn,
           COUNT(*)     OVER (PARTITION BY follower_band)                  AS cnt
    FROM posts WHERE is_vertical = 1 AND rate_valid = 1
)
SELECT f.follower_band                                       AS follower_band,
       CASE f.follower_band WHEN '<10k' THEN 1 WHEN '10k-50k' THEN 2
                            WHEN '50k-200k' THEN 3 WHEN '200k-1M' THEN 4 ELSE 5 END AS band_no,
       COUNT(*)                                              AS n,
       ROUND(AVG(f.eng_per_1k_fans), 2)                      AS mean_eng_per_1k_fans,
       ROUND(AVG(f.reach_ratio), 4)                          AS mean_reach_ratio,
       SUM(f.views)                                          AS total_views,
       SUM(f.engagement_total)                               AS total_engagement,
       ROUND(100.0 * SUM(f.engagement_total) / SUM(f.views), 4) AS er_view_pooled,
       (SELECT ROUND(AVG(b.er_view), 4) FROM base b
         WHERE b.follower_band = f.follower_band
           AND b.rn IN ((b.cnt+1)/2, (b.cnt+2)/2))           AS median_er_view
FROM posts f
WHERE f.is_vertical = 1 AND f.rate_valid = 1
GROUP BY f.follower_band
ORDER BY band_no;
