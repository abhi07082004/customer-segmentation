"""
Generate a realistic customer + orders dataset and load it into a SQLite database.

Customers are drawn from hidden behaviour profiles (frequent high spenders,
occasional buyers, lapsed customers, new sign-ups, discount seekers), so the
clustering step has genuine structure to discover. The profiles are NOT stored
in the database; the model has to find them from purchase behaviour alone.

Usage:
    python src/generate_data.py
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "ecommerce.db"
SCHEMA = ROOT / "sql" / "01_schema.sql"

rng = np.random.default_rng(SEED)
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")

CITIES = {
    "Tier 1": ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune", "Kolkata"],
    "Tier 2": ["Nagpur", "Jaipur", "Lucknow", "Indore", "Surat", "Kochi", "Bhopal", "Vadodara"],
    "Tier 3": ["Nashik", "Raipur", "Dehradun", "Mysuru", "Guwahati", "Ranchi"],
}
ACQ_CHANNELS = ["Instagram Ads", "Google Search", "Referral", "Marketplace", "Organic"]
CATEGORIES = ["Men's Socks", "Women's Socks", "Kids' Socks", "Gift Sets", "Accessories"]

# profile: share, orders range, avg basket (INR), discount usage, recency window (days before END)
PROFILES = {
    "high_value_loyal": dict(share=0.12, orders=(8, 20), basket=(1800, 3200), disc=0.15, last=(1, 45)),
    "regular":          dict(share=0.25, orders=(4, 9),  basket=(900, 1600),  disc=0.25, last=(10, 120)),
    "discount_seeker":  dict(share=0.15, orders=(3, 7),  basket=(450, 800),   disc=0.85, last=(20, 200)),
    "new":              dict(share=0.18, orders=(1, 2),  basket=(700, 1500),  disc=0.40, last=(1, 60)),
    "lapsed":           dict(share=0.30, orders=(1, 3),  basket=(500, 1200),  disc=0.35, last=(240, 700)),
}


def make_customers(n: int) -> tuple[pd.DataFrame, np.ndarray]:
    names = list(PROFILES)
    profiles = rng.choice(names, size=n, p=[PROFILES[p]["share"] for p in names])
    tiers = rng.choice(list(CITIES), size=n, p=[0.55, 0.32, 0.13])
    cities = [rng.choice(CITIES[t]) for t in tiers]
    signup = []
    for p in profiles:
        if p == "new":
            signup.append(END - pd.Timedelta(days=int(rng.integers(5, 90))))
        else:
            signup.append(START + pd.Timedelta(days=int(rng.integers(0, 300))))
    customers = pd.DataFrame({
        "customer_id": [f"C{i:05d}" for i in range(1, n + 1)],
        "signup_date": pd.to_datetime(signup).strftime("%Y-%m-%d"),
        "city": cities,
        "city_tier": tiers,
        "age_group": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], size=n,
                                p=[0.18, 0.38, 0.24, 0.13, 0.07]),
        "acquisition_channel": rng.choice(ACQ_CHANNELS, size=n, p=[0.32, 0.22, 0.14, 0.17, 0.15]),
    })
    return customers, profiles


def make_orders(customers: pd.DataFrame, profiles: np.ndarray) -> pd.DataFrame:
    rows, oid = [], 500000
    for cust, signup, prof in zip(customers["customer_id"],
                                  pd.to_datetime(customers["signup_date"]), profiles):
        cfg = PROFILES[prof]
        n_orders = int(rng.integers(cfg["orders"][0], cfg["orders"][1] + 1))
        last = END - pd.Timedelta(days=int(rng.integers(*cfg["last"])))
        last = max(last, signup)
        span = max((last - signup).days, 1)
        offsets = np.sort(rng.integers(0, span + 1, size=n_orders - 1))
        dates = [signup + pd.Timedelta(days=int(o)) for o in offsets] + [last]
        for d in dates:
            items = int(rng.choice([1, 2, 3, 4], p=[0.5, 0.3, 0.14, 0.06]))
            gross = round(rng.uniform(*cfg["basket"]) * (0.7 + 0.15 * items), 2)
            used_coupon = rng.random() < cfg["disc"]
            disc = round(gross * rng.choice([0.10, 0.15, 0.20, 0.30]), 2) if used_coupon else 0.0
            status = rng.choice(["Delivered", "Cancelled", "Returned"], p=[0.92, 0.05, 0.03])
            rows.append((f"O{oid}", cust, d.strftime("%Y-%m-%d"),
                         rng.choice(CATEGORIES, p=[0.35, 0.3, 0.12, 0.15, 0.08]),
                         items, gross, disc, round(gross - disc, 2), int(used_coupon), status))
            oid += 1
    return pd.DataFrame(rows, columns=["order_id", "customer_id", "order_date", "category",
                                       "items", "gross_amount", "discount_amount",
                                       "net_amount", "coupon_used", "status"])


def main() -> None:
    customers, profiles = make_customers(5_000)
    orders = make_orders(customers, profiles)

    DATA_DIR.mkdir(exist_ok=True)
    customers.to_csv(DATA_DIR / "customers.csv", index=False)
    orders.to_csv(DATA_DIR / "orders.csv", index=False)

    DB_PATH.unlink(missing_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(SCHEMA.read_text())
        customers.to_sql("customers", con, if_exists="append", index=False)
        orders.to_sql("orders", con, if_exists="append", index=False)
    print(f"customers: {len(customers):,}  orders: {len(orders):,}  -> {DB_PATH}")


if __name__ == "__main__":
    main()
