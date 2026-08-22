import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .deals import DATA_DIR, load_deals


def build_df():
    import pandas as pd

    rows = load_deals()
    if not rows:
        return pd.DataFrame(
            columns=["site", "title", "used_price", "new_price", "pct_off", "quality"]
        )
    df = pd.DataFrame(rows)
    df["savings"] = df["new_price"] - df["used_price"]
    df["pct"] = (df["pct_off"] * 100).round(1)
    df["quality_flag"] = df["quality"].fillna(False)
    return df


def _style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def plot_discount_hist(df, path):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    df["pct"].hist(bins=25, ax=ax, color="#3b7dd8", edgecolor="white")
    ax.axvline(70, color="#d84b3b", linestyle="--", label="deal floor 70%")
    ax.set_xlabel("% off new price")
    ax.set_ylabel("deals")
    ax.set_title("Discount distribution")
    _style(ax)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_top_savings(df, path, n=15):
    top = df.nlargest(n, "pct")[::-1]
    fig, ax = plt.subplots(figsize=(9, 0.45 * n + 1.5))
    colors = ["#2e7d32" if q else "#3b7dd8" for q in top["quality_flag"]]
    ax.barh(top["title"].str[:60], top["pct"], color=colors)
    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r["pct"] + 1, i, f"{r['pct']:.0f}%", va="center", fontsize=8)
    ax.set_xlabel("% off")
    ax.set_title(f"Top {n} discounts")
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_by_site(df, path):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    counts = (
        df.assign(q=lambda d: d["quality_flag"].map({True: "curated", False: "other"}))
        .groupby(["site", "q"])
        .size()
        .unstack(fill_value=0)
    )
    counts.plot(kind="bar", ax=ax, color=["#2e7d32", "#3b7dd8"])
    ax.set_ylabel("deals")
    ax.set_title("Deals by site")
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def summary(df):
    from . import theme as T

    q = df["quality_flag"].sum()
    total_savings = df["savings"].sum()
    avg = df["pct"].mean()
    best = df.nlargest(5, "pct")[["site", "title", "pct", "used_price"]]
    print(T.frame(
        "shelf overview",
        T.dim(f"{len(df)} deals · {int(q)} curated · avg {avg:.1f}% off · {T.money(total_savings)} total saved"),
    ))
    for _, r in best.iterrows():
        print(f"  {T.pct_colored(r['pct']/100)}  {T.money(r['used_price'])}  {T.site_tag(r['site'])}  {r['title'][:52]}")
    print(T.whisper("charts written to data/viz_*.png"))


def cmd_viz(args):
    df = build_df()
    if df.empty:
        print("no deals yet (run: wob scan), nothing to chart")
        return
    summary(df)
    paths = {
        "hist": DATA_DIR / "viz_discount_hist.png",
        "top": DATA_DIR / "viz_top_deals.png",
        "site": DATA_DIR / "viz_by_site.png",
    }
    plot_discount_hist(df, paths["hist"])
    plot_top_savings(df, paths["top"], args.top)
    plot_by_site(df, paths["site"])
    print("charts: " + ", ".join(str(p) for p in paths.values()))
    if not args.png:
        from IPython import embed

        print("\nloaded: df (all deals). try: df.head(), df[df.quality].")
        embed(colors="Neutral")