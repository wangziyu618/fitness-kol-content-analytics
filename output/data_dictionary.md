# Data dictionary — `posts_clean.csv`

Source: `data/raw/social_media_engagement_dataset.csv`
(Kaggle · aviral342 · Social Media Engagement Dataset · CC0 1.0)
One row = one published post.

## 1. Raw fields carried through

| Field | Type | Definition |
|---|---|---|
| `post_id` | text | Unique post identifier (primary key) |
| `posted_at` | datetime | Publish timestamp, `YYYY-MM-DD HH:MM:SS` |
| `platform` | text | Instagram / TikTok / YouTube / Twitter / Facebook / LinkedIn |
| `content_type` | text | Creative format (Photo, Video, Reel, Carousel, Story, …) |
| `category` | text | Content category; `Fitness` / `Sports` / `Health` = project vertical |
| `follower_count` | int | Creator follower base at publish time |
| `engagement_rate` (raw) | float | **Follower-based**, see §3 |
| `hashtag_count` | int | Hashtags attached to the post |
| `content_length` | int | Caption characters, or video seconds |
| `content_type` | text | 17 platform-native format labels (Reel, Tweet, Stitch, Document, …) |
| `sentiment` | text | Positive / Neutral / Negative (author-side label) |
| `influencer_tier` | text | Nano / Micro / Mid-tier / Macro |
| `has_media`, `is_verified` | 0/1 | Booleans |

## 2. Engineered fields

| Field | Definition |
|---|---|
| `date`, `year_month`, `hour`, `weekday`, `is_weekend` | Calendar decomposition of `posted_at` |
| `time_slot` | `00-05 Late night` / `06-11 Morning` / `12-17 Afternoon` / `18-23 Evening` |
| `is_vertical` | 1 when `category` ∈ {Fitness, Sports, Health} |
| `vertical_segment` | Fitness / Sports / Health / Other |
| `tier_rank` | 0=Nano … 3=Macro, for ordered comparisons |
| `follower_band` | `<10k` / `10k-50k` / `50k-200k` / `200k-1M` / `1M+` |
| `hashtag_bucket` | `0` / `1-5` / `6-10` / `11-20` / `21-30` / `30+` |
| `content_family` | 17 platform-native `content_type` labels folded into 5 cross-platform families: **Short video** (Video, Reel, Short, Stitch, Duet) · **Static image** (Photo, Carousel) · **Live** · **Story / interactive** (Story, Poll) · **Text / long-form** (Post, Tweet, Thread, Retweet, Article, Document, Community Post). Without this folding, a "best format" comparison would mostly restate which platform the format belongs to. |
| `rate_valid` | 1 when `engagement_total` ≤ `Views`. 295 rows (5.9%) violate this; they stay in the table for volume accounting but are excluded from every rate metric. |

## 3. Metric definitions (口径) — the important part

The raw column `Engagement_Rate` was reverse-engineered during profiling and
resolves to `(Likes + Comments + Shares) / Follower_Count × 100`. It is a
**follower-based** rate and **excludes Saves**, so it is not comparable with the
view-based rates used in media planning. It is retained as
`er_follower_reported` for audit only.

| Metric | Formula | Reading |
|---|---|---|
| `engagement_total` | Likes + Comments + Shares + Saves | Absolute interaction volume |
| `er_view` | `engagement_total / Views × 100` | **Primary KPI** — interaction per 100 views |
| `er_follower` | `engagement_total / Follower_Count × 100` | Fan-base activation |
| `deep_rate` | `(Shares + Saves) / Views × 100` | High-intent / "value" interactions |
| `save_rate` | `Saves / Views × 100` | Save-for-later intent |
| `share_rate` | `Shares / Views × 100` | Organic amplification |
| `comment_rate` | `Comments / Views × 100` | Conversation intensity |
| `eng_per_1k_fans` | `engagement_total / (Follower_Count / 1000)` | Efficiency of a creator's fan base |
| `reach_ratio` | `Views / Follower_Count` | Algorithmic amplification vs. own fans |

## 4. Central tendency and uncertainty

Engagement-rate distributions are strongly right-skewed, so every headline
figure is a **median** with a **95% bootstrap percentile interval**
(2,000 resamples, seed fixed). Means are available in the dashboard tooltips.
