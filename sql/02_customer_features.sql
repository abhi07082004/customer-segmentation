-- Customer-level behavioural features for segmentation (RFM + extras).
-- Snapshot date: 2026-01-01 (day after the last order in the data).
-- Only delivered orders count towards spend and frequency.

WITH delivered AS (
    SELECT *
    FROM orders
    WHERE status = 'Delivered'
),
customer_orders AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id)                         AS frequency,
        ROUND(SUM(net_amount), 2)                        AS monetary,
        ROUND(AVG(net_amount), 2)                        AS avg_order_value,
        MAX(order_date)                                  AS last_order_date,
        MIN(order_date)                                  AS first_order_date,
        ROUND(AVG(coupon_used), 3)                       AS coupon_rate,
        ROUND(SUM(discount_amount) / SUM(gross_amount), 3) AS discount_share,
        COUNT(DISTINCT category)                         AS categories_bought
    FROM delivered
    GROUP BY customer_id
),
returns AS (
    SELECT
        customer_id,
        ROUND(AVG(CASE WHEN status = 'Returned' THEN 1.0 ELSE 0 END), 3) AS return_rate
    FROM orders
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.city_tier,
    c.age_group,
    c.acquisition_channel,
    CAST(julianday('2026-01-01') - julianday(co.last_order_date)  AS INT) AS recency_days,
    CAST(julianday('2026-01-01') - julianday(c.signup_date)       AS INT) AS tenure_days,
    co.frequency,
    co.monetary,
    co.avg_order_value,
    co.coupon_rate,
    co.discount_share,
    co.categories_bought,
    COALESCE(r.return_rate, 0) AS return_rate
FROM customers c
JOIN customer_orders co ON co.customer_id = c.customer_id
LEFT JOIN returns r     ON r.customer_id  = c.customer_id;

-- MySQL equivalent for the date maths:
--   DATEDIFF('2026-01-01', co.last_order_date) AS recency_days
