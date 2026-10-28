"""血統の集計。どの関数も出走数・勝率・複勝率・回収率をそろえた表を返す。"""

import pandas as pd

from .config import ERA_SPAN, MIN_STARTS


def stats(df, keys, min_starts=0):
    """keys ごとに成績をまとめる。"""
    df = df.assign(_w1=df["finish"] == 1, _w2=df["finish"] <= 2, _w3=df["finish"] <= 3)
    g = df.groupby(keys, dropna=True)
    out = pd.DataFrame({
        "出走": g.size(),
        "1着": g["_w1"].sum(),
        "2着内": g["_w2"].sum(),
        "3着内": g["_w3"].sum(),
    })
    out["勝率"] = out["1着"] / out["出走"] * 100
    out["連対率"] = out["2着内"] / out["出走"] * 100
    out["複勝率"] = out["3着内"] / out["出走"] * 100
    if df["win_return"].notna().any():
        out["単回収率"] = g["win_return"].sum() / out["出走"]
        # 1 本の大穴で回収率が跳ねていないかを見るため、最高配当を除いた値も出す
        out["単回収率(最高配当除く)"] = (g["win_return"].sum() - g["win_return"].max()) / out["出走"]
    if df["place_return"].notna().any():
        out["複回収率"] = g["place_return"].sum() / out["出走"]
    out = out[out["出走"] >= min_starts]
    return out.round(1).reset_index()


def baseline(df):
    """全体の平均（比較の基準）。"""
    return stats(df.assign(_all="全体"), ["_all"]).drop(columns="_all").iloc[0]


def sire_overall(df):
    return stats(df, ["sire"], MIN_STARTS["sire_total"]).sort_values("1着", ascending=False)


def sire_by(df, condition):
    """種牡馬 × 条件（surface / dist_band / course / going）。"""
    return stats(df, ["sire", condition], MIN_STARTS["sire_condition"])


def sire_surface_dist(df):
    return stats(df, ["sire", "surface", "dist_band"], MIN_STARTS["sire_condition"])


def damsire_overall(df):
    return stats(df, ["damsire"], MIN_STARTS["damsire"]).sort_values("1着", ascending=False)


def damsire_by(df, condition):
    return stats(df, ["damsire", condition], MIN_STARTS["damsire_condition"])


def nicks(df):
    """父 × 母父。父の全体成績と比べてどれだけ上積みがあるかも出す。"""
    nick = stats(df, ["sire", "damsire"], MIN_STARTS["nick"])
    sire = stats(df, ["sire"])[["sire", "複勝率", "勝率"]].rename(
        columns={"複勝率": "父の複勝率", "勝率": "父の勝率"})
    nick = nick.merge(sire, on="sire", how="left")
    nick["複勝率の上積み"] = (nick["複勝率"] - nick["父の複勝率"]).round(1)
    nick["勝率の上積み"] = (nick["勝率"] - nick["父の勝率"]).round(1)
    return nick.sort_values("複勝率の上積み", ascending=False)


def roi_targets(df):
    """回収率 100% 超えの「狙い目」を、いくつかの切り口でまとめて探す。"""
    if not df["win_return"].notna().any():
        return pd.DataFrame()
    cuts = {
        "父×芝ダ×距離": ["sire", "surface", "dist_band"],
        "父×競馬場×芝ダ": ["sire", "course", "surface"],
        "父×馬場状態×芝ダ": ["sire", "going", "surface"],
        "母父×芝ダ×距離": ["damsire", "surface", "dist_band"],
        "父×母父": ["sire", "damsire"],
    }
    rows = []
    for label, keys in cuts.items():
        t = stats(df, keys, MIN_STARTS["roi"])
        if t.empty:
            continue
        name = t[keys].astype(str).agg(" / ".join, axis=1)
        t = t.drop(columns=keys)
        t.insert(0, "条件", name)
        t.insert(0, "切り口", label)
        rows.append(t)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    hit = out["単回収率"] >= 100
    if "複回収率" in out:
        hit |= out["複回収率"] >= 100
    return out[hit].sort_values("単回収率(最高配当除く)", ascending=False)


def era_label(year, start):
    lo = start + (int(year) - start) // ERA_SPAN * ERA_SPAN
    return f"{lo}〜{lo + ERA_SPAN - 1}"


def sire_by_era(df, top=10):
    """年代ごとの勝利数ランキング（上位 top 頭）。"""
    start = int(df["year"].min())
    d = df.assign(era=df["year"].apply(lambda y: era_label(y, start)))
    t = stats(d, ["era", "sire"])
    t = t.sort_values(["era", "1着"], ascending=[True, False])
    t["順位"] = t.groupby("era").cumcount() + 1
    return t[t["順位"] <= top]


def sire_win_share_by_year(df, top=8):
    """年ごとの勝利シェア（全勝利のうち何%をその種牡馬の産駒が取ったか）。"""
    wins = df[df["finish"] == 1]
    per_year = wins.groupby(["year", "sire"]).size().unstack(fill_value=0)
    share = per_year.div(per_year.sum(axis=1), axis=0) * 100
    # どこかの年で上位に入った種牡馬を選ぶ
    leaders = share.apply(lambda r: r.nlargest(3).index.tolist(), axis=1).explode().value_counts()
    cols = share.max().loc[leaders.index].nlargest(top).index
    return share[cols].round(2)


def damsire_by_era(df, top=10):
    start = int(df["year"].min())
    d = df.assign(era=df["year"].apply(lambda y: era_label(y, start)))
    t = stats(d, ["era", "damsire"])
    t = t.sort_values(["era", "1着"], ascending=[True, False])
    t["順位"] = t.groupby("era").cumcount() + 1
    return t[t["順位"] <= top]
