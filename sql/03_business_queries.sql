-- Supporting business queries used during exploration.

-- 1. Monthly revenue and active customers
SELECT
    strftime('%Y-%m', order_date)   AS month,          -- MySQL: DATE_FORMAT(order_date, '%Y-%m')
    COUNT(DISTINCT customer_id)     AS active_customers,
    COUNT(*)                        AS orders,
    ROUND(SUM(net_amount), 0)       AS revenue
FROM orders
WHERE status = 'Delivered'
GROUP BY month
ORDER BY month;

-- 2. Revenue by acquisition channel
SELECT
    c.acquisition_channel,
    COUNT(DISTINCT c.customer_id)               AS customers,
    ROUND(SUM(o.net_amount), 0)                 AS revenue,
    ROUND(SUM(o.net_amount) / COUNT(DISTINCT c.customer_id), 0) AS revenue_per_customer
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'Delivered'
GROUP BY c.acquisition_channel
ORDER BY revenue_per_customer DESC;

-- 3. Top 10 customers by lifetime value with their rank
SELECT customer_id, lifetime_value,
       RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_rank
FROM (
    SELECT customer_id, ROUND(SUM(net_amount), 0) AS lifetime_value
    FROM orders
    WHERE status = 'Delivered'
    GROUP BY customer_id
) t
ORDER BY ltv_rank
LIMIT 10;

-- 4. Repeat purchase rate
SELECT
    ROUND(AVG(CASE WHEN n_orders > 1 THEN 1.0 ELSE 0 END), 3) AS repeat_rate
FROM (
    SELECT customer_id, COUNT(*) AS n_orders
    FROM orders
    WHERE status = 'Delivered'
    GROUP BY customer_id
) t;
