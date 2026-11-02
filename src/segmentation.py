"""
Customer segmentation with RFM features and K-Means clustering.

Pipeline
--------
1. Extract customer-level features from the database with SQL
2. Log-transform skewed features and standardise them
3. Choose k using the elbow method and silhouette score
4. Fit K-Means, profile each cluster and give it a business name
5. Save segment assignments, profiles and charts

Usage:
    python src/segmentation.py
"""
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"
FEATURE_SQL = ROOT / "sql" / "02_customer_features.sql"
FIG_DIR = ROOT / "reports" / "figures"
REPORT_DIR = ROOT / "reports"

FEATURES = ["recency_days", "frequency", "monetary", "avg_order_value", "coupon_rate"]
LOG_FEATURES = ["recency_days", "frequency", "monetary", "avg_order_value"]
RANDOM_STATE = 42

sns.set_theme(style="whitegrid")


def load_features() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query(FEATURE_SQL.read_text(), con)


def prepare(df: pd.DataFrame) -> np.ndarray:
    X = df[FEATURES].copy()
    X[LOG_FEATURES] = np.log1p(X[LOG_FEATURES])
    return StandardScaler().fit_transform(X)


def evaluate_k(X: np.ndarray, k_range=range(2, 10)) -> pd.DataFrame:
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
        rows.append({"k": k, "inertia": km.inertia_,
                     "silhouette": silhouette_score(X, km.labels_, sample_size=3000,
                                                    random_state=RANDOM_STATE)})
    return pd.DataFrame(rows)


def name_segments(profile: pd.DataFrame) -> dict:
    """Assign business-friendly names to clusters based on their average behaviour."""
    names = {}
    p = profile.copy()
    remaining = set(p.index)

    def pick(col, largest=True):
        cand = p.loc[list(remaining), col]
        idx = cand.idxmax() if largest else cand.idxmin()
        remaining.discard(idx)
        return idx

    names[pick("monetary")] = "Champions"
    names[pick("recency_days")] = "At-Risk / Lapsed"
    names[pick("coupon_rate")] = "Discount Seekers"
    names[pick("tenure_days", largest=False)] = "New Customers"
    for idx in remaining:
        names[idx] = "Loyal Regulars"
    return names


def plot_k_selection(scores: pd.DataFrame, k: int) -> None:
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(scores["k"], scores["inertia"], "o-", color="#1F6F78", label="Inertia (elbow)")
    ax1.set_xlabel("Number of clusters (k)"); ax1.set_ylabel("Inertia")
    ax2 = ax1.twinx()
    ax2.plot(scores["k"], scores["silhouette"], "s--", color="#D98E04", label="Silhouette")
    ax2.set_ylabel("Silhouette score"); ax2.grid(False)
    ax1.axvline(k, color="grey", linestyle=":")
    fig.legend(loc="upper right", bbox_to_anchor=(0.88, 0.88))
    ax1.set_title("Choosing k: Elbow Method and Silhouette Score")
    fig.tight_layout(); fig.savefig(FIG_DIR / "01_k_selection.png", dpi=130); plt.close(fig)


def plot_pca(X, df) -> None:
    coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.scatterplot(x=coords[:, 0], y=coords[:, 1], hue=df["segment"], s=12, alpha=0.6,
                    palette="Set2", ax=ax)
    ax.set_title("Customer Segments (PCA projection)")
    ax.set_xlabel("Principal component 1"); ax.set_ylabel("Principal component 2")
    ax.legend(title="Segment", markerscale=2)
    fig.tight_layout(); fig.savefig(FIG_DIR / "02_segments_pca.png", dpi=130); plt.close(fig)


def plot_profile_heatmap(profile: pd.DataFrame) -> None:
    cols = ["recency_days", "frequency", "monetary", "avg_order_value", "coupon_rate"]
    z = (profile[cols] - profile[cols].mean()) / profile[cols].std()
    z[["recency_days", "coupon_rate"]] *= -1  # lower is better for these, so flip the colour
    labels = profile[cols].copy().astype(object)
    for c in cols:
        labels[c] = profile[c].map("{:.0%}".format if c == "coupon_rate" else "{:,.0f}".format)
    fig, ax = plt.subplots(figsize=(11, 5))
    sns.heatmap(z, annot=labels, fmt="", cmap="RdYlGn", center=0, ax=ax,
                cbar_kws={"label": "worse  <-  vs average  ->  better"})
    ax.set_xticklabels(["Recency\n(days)", "Frequency\n(orders)", "Monetary\n(INR)",
                        "Avg order\nvalue (INR)", "Coupon\nusage"], rotation=0)
    ax.set_title("Segment Profiles (cell values = segment averages)")
    ax.set_ylabel("")
    fig.tight_layout(); fig.savefig(FIG_DIR / "03_segment_profiles.png", dpi=130); plt.close(fig)


def plot_revenue_share(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    s = summary[["customer_share", "revenue_share"]].sort_values("revenue_share")
    s.plot.barh(ax=ax, color=["#9BC1BC", "#1F6F78"])
    ax.set_title("Share of Customers vs Share of Revenue by Segment")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax.set_ylabel(""); ax.legend(["% of customers", "% of revenue"])
    fig.tight_layout(); fig.savefig(FIG_DIR / "04_customers_vs_revenue.png", dpi=130); plt.close(fig)


def run(k: int = 5, verbose: bool = True):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = load_features()
    X = prepare(df)

    scores = evaluate_k(X)
    plot_k_selection(scores, k)

    km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE).fit(X)
    df["cluster"] = km.labels_
    sil = silhouette_score(X, km.labels_)

    profile = df.groupby("cluster")[FEATURES + ["tenure_days"]].mean()
    df["segment"] = df["cluster"].map(name_segments(profile))

    seg_profile = df.groupby("segment")[FEATURES + ["tenure_days"]].mean()
    summary = df.groupby("segment").agg(customers=("customer_id", "count"),
                                        revenue=("monetary", "sum"))
    summary["customer_share"] = summary["customers"] / summary["customers"].sum()
    summary["revenue_share"] = summary["revenue"] / summary["revenue"].sum()
    summary = summary.join(seg_profile.round(2)).sort_values("revenue", ascending=False)

    plot_pca(X, df)
    plot_profile_heatmap(seg_profile)
    plot_revenue_share(summary)

    df[["customer_id", "segment"] + FEATURES].to_csv(REPORT_DIR / "customer_segments.csv",
                                                     index=False)
    summary.to_csv(REPORT_DIR / "segment_summary.csv")
    scores.to_csv(REPORT_DIR / "k_selection_scores.csv", index=False)

    if verbose:
        print("k selection\n", scores.round(3).to_string(index=False))
        print(f"\nFinal model: k={k}, silhouette={sil:.3f}")
        print("\nSegment summary\n", summary.round(3).to_string())
    return df, summary, scores, sil


if __name__ == "__main__":
    run()
