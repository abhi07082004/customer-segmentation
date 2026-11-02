-- Schema for the e-commerce customer database (works in SQLite and MySQL)

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id          VARCHAR(10) PRIMARY KEY,
    signup_date          DATE        NOT NULL,
    city                 VARCHAR(50),
    city_tier            VARCHAR(10),
    age_group            VARCHAR(10),
    acquisition_channel  VARCHAR(30)
);

CREATE TABLE orders (
    order_id         VARCHAR(10) PRIMARY KEY,
    customer_id      VARCHAR(10) NOT NULL,
    order_date       DATE        NOT NULL,
    category         VARCHAR(30),
    items            INT,
    gross_amount     DECIMAL(10, 2),
    discount_amount  DECIMAL(10, 2),
    net_amount       DECIMAL(10, 2),
    coupon_used      INT,           -- 1 = coupon applied
    status           VARCHAR(15),   -- Delivered / Cancelled / Returned
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_date     ON orders (order_date);
