"""集計結果を CSV・画像・note 用の記事下書きに書き出す。

note の記事エディタは表に対応していないため、表は PNG 画像にして貼る前提にしている。
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402

from . import analyze as A  # noqa: E402
from .config import DISTANCE_BANDS, JP_FONTS  # noqa: E402

GOING_ORDER = ["良", "稍重", "重", "不良"]
BAND_ORDER = [b[2] for b in DISTANCE_BANDS]
COURSE_ORDER = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]
NAMES = {"sire": "種牡馬", "damsire": "母父", "surface": "芝ダ", "dist_band": "距離",
         "course": "競馬場", "going": "馬場", "era": "年代"}


def setup_font():
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in JP_FONTS:
        if name in installed:
            plt.rcParams["font.family"] = name
            return name
    return None


class Writer:
    def __init__(self, out_dir):
        self.out = Path(out_dir)
        (self.out / "tables").mkdir(parents=True, exist_ok=True)
        (self.out / "images").mkdir(parents=True, exist_ok=True)

    def csv(self, df, name):
        # Excel でそのまま開けるよう BOM 付き UTF-8 で保存
        df.rename(columns=NAMES).to_csv(self.out / "tables" / f"{name}.csv", index=False, encoding="utf-8-sig")

    def save(self, fig, name):
        path = self.out / "images" / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return f"images/{name}.png"


def table_image(w, df, name, title, cols, max_rows=20):
    df = df.head(max_rows).rename(columns=NAMES)
    cols = [NAMES.get(c, c) for c in cols if NAMES.get(c, c) in df.columns]
    df = df[cols]
    cells = [[_fmt(v) for v in row] for row in df.itertuples(index=False)]
    # 列幅は一番長い文字列に合わせる（全角は 2 文字分として数える）
    widths = [max(_text_width(s) for s in [c] + [r[i] for r in cells]) + 2 for i, c in enumerate(cols)]
    total = sum(widths)
    fig, ax = plt.subplots(figsize=(max(6, total * 0.085), 0.3 * (len(cells) + 1) + 0.6))
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", loc="left")
    t = ax.table(cellText=cells, colLabels=cols, cellLoc="center", bbox=[0, 0, 1, 1],
                 colWidths=[x / total for x in widths])
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    for (r, _), cell in t.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if r == 0:
            cell.set_facecolor("#2f4f6f")
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#f3f6f9")
    return w.save(fig, name)


def _text_width(s):
    return sum(2 if ord(ch) > 0x2000 else 1 for ch in str(s))


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.1f}"
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    return str(v)


def bar_chart(w, df, label_col, value_col, name, title, xlabel):
    d = df.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(d[label_col], d[value_col], color="#3b6ea5")
    for y, v in enumerate(d[value_col]):
        ax.text(v, y, f" {v:,.0f}", va="center", fontsize=8)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.spines[["top", "right"]].set_visible(False)
    return w.save(fig, name)


def heatmap(w, pivot, name, title, center):
    """複勝率のヒートマップ。全体平均より高いと赤、低いと青。"""
    pivot = pivot.dropna(how="all").dropna(axis=1, how="all")
    if pivot.empty:
        return None  # 最低出走数を満たす条件がない
    fig, ax = plt.subplots(figsize=(1.2 * pivot.shape[1] + 3, 0.4 * pivot.shape[0] + 1.5))
    data = pivot.values.astype(float)
    span = np.nanmax(np.abs(data - center)) if np.isfinite(data).any() else 1
    im = ax.imshow(data, cmap="RdBu_r", vmin=center - span, vmax=center + span, aspect="auto")
    ax.set_xticks(range(pivot.shape[1]), pivot.columns, rotation=30, ha="right")
    ax.set_yticks(range(pivot.shape[0]), pivot.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if np.isfinite(data[i, j]):
                ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center", fontsize=8)
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.colorbar(im, ax=ax, label="複勝率(%)", shrink=0.8)
    return w.save(fig, name)


def condition_pivot(table, key, condition, order, leaders):
    p = table[table[key].isin(leaders)].pivot(index=key, columns=condition, values="複勝率")
    p = p.reindex(index=leaders, columns=[c for c in order if c in p.columns])
    return p


def line_chart(w, share, name, title):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for col in share.columns:
        ax.plot(share.index.astype(int), share[col], marker="o", markersize=3, label=col)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel("勝利シェア(%)")
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    return w.save(fig, name)


def build(df, info, out_dir):
    font = setup_font()
    w = Writer(out_dir)
    base = A.baseline(df)
    img = {}
    facts = {}

    # 1. 種牡馬の総合成績
    sire = A.sire_overall(df)
    w.csv(sire, "01_種牡馬_総合")
    img["sire_bar"] = bar_chart(w, sire, "sire", "1着", "01_種牡馬_勝利数", "種牡馬別 勝利数 TOP15", "勝利数")
    rate_cols = ["sire", "出走", "1着", "勝率", "連対率", "複勝率"] + \
        [c for c in ("単回収率", "複回収率") if c in sire.columns]
    img["sire_table"] = table_image(w, sire, "01_種牡馬_総合表", "種牡馬別 総合成績（勝利数順）", rate_cols)
    facts["sire_top"] = sire.head(3)

    # 2. 種牡馬 × 芝ダ × 距離
    sd = A.sire_surface_dist(df)
    w.csv(sd, "02_種牡馬_芝ダ_距離")
    for surface in ("芝", "ダート"):
        s = df[df["surface"] == surface]
        leaders = A.sire_overall(s).head(15)["sire"].tolist()
        p = condition_pivot(sd[sd["surface"] == surface], "sire", "dist_band", BAND_ORDER, leaders)
        img[f"dist_{surface}"] = heatmap(w, p, f"02_距離_{surface}", f"{surface}・距離区分別 複勝率（勝利数上位15頭）",
                                         A.baseline(s)["複勝率"])
        facts[f"top_{surface}"] = A.sire_overall(s).head(3)

    # 3. 種牡馬 × 競馬場
    sc = A.stats(df, ["sire", "surface", "course"], A.MIN_STARTS["sire_condition"])
    w.csv(sc, "03_種牡馬_競馬場")
    for surface in ("芝", "ダート"):
        s = df[df["surface"] == surface]
        leaders = A.sire_overall(s).head(15)["sire"].tolist()
        p = condition_pivot(sc[sc["surface"] == surface], "sire", "course", COURSE_ORDER, leaders)
        img[f"course_{surface}"] = heatmap(w, p, f"03_競馬場_{surface}", f"{surface}・競馬場別 複勝率（勝利数上位15頭）",
                                           A.baseline(s)["複勝率"])

    # 4. 種牡馬 × 馬場状態（道悪巧者）
    sg = A.stats(df, ["sire", "surface", "going"], A.MIN_STARTS["sire_condition"])
    w.csv(sg, "04_種牡馬_馬場状態")
    heavy = df.assign(going2=df["going"].map({"良": "良", "稍重": "道悪", "重": "道悪", "不良": "道悪"}))
    hv = A.stats(heavy, ["sire", "surface", "going2"], A.MIN_STARTS["sire_condition"])
    hv = hv.pivot_table(index=["sire", "surface"], columns="going2", values="複勝率").dropna().reset_index()
    hv["道悪での上積み"] = (hv["道悪"] - hv["良"]).round(1)
    hv = hv.sort_values("道悪での上積み", ascending=False)
    w.csv(hv, "04_道悪巧者")
    img["going_table"] = table_image(w, hv, "04_道悪巧者", "道悪（稍重〜不良）で複勝率が上がる種牡馬",
                                     ["sire", "surface", "良", "道悪", "道悪での上積み"])
    facts["heavy_top"] = hv.head(3)

    # 5. 母父
    ds = A.damsire_overall(df)
    w.csv(ds, "05_母父_総合")
    w.csv(A.stats(df, ["damsire", "surface", "dist_band"], A.MIN_STARTS["damsire_condition"]), "05_母父_芝ダ_距離")
    img["damsire_bar"] = bar_chart(w, ds, "damsire", "1着", "05_母父_勝利数", "母父別 勝利数 TOP15", "勝利数")
    img["damsire_table"] = table_image(w, ds.sort_values("複勝率", ascending=False), "05_母父_複勝率",
                                       "母父別 複勝率ランキング", ["damsire", "出走", "1着", "勝率", "複勝率"]
                                       + [c for c in ("単回収率", "複回収率") if c in ds.columns])
    facts["damsire_top"] = ds.head(3)

    # 6. ニックス
    nk = A.nicks(df)
    w.csv(nk, "06_ニックス")
    img["nick_table"] = table_image(w, nk, "06_ニックス", "父×母父 ニックス（父の平均より複勝率が上がる組み合わせ）",
                                    ["sire", "damsire", "出走", "勝率", "複勝率", "父の複勝率", "複勝率の上積み"])
    facts["nick_top"] = nk.head(3)

    # 7. 回収率の狙い目
    roi = A.roi_targets(df)
    if len(roi):
        w.csv(roi, "07_回収率_狙い目")
        cols = ["切り口", "条件", "出走", "勝率", "単回収率", "単回収率(最高配当除く)"] + \
            (["複回収率"] if "複回収率" in roi.columns else [])
        img["roi_table"] = table_image(w, roi, "07_回収率_狙い目", "回収率100%超えの狙い目（最高配当を除いた単回収率順）", cols, 25)
        facts["roi_top"] = roi.head(3)

    # 8. 年代ごとの勢力
    share = A.sire_win_share_by_year(df)
    w.csv(share.reset_index(), "08_種牡馬_年別勝利シェア")
    img["era_line"] = line_chart(w, share, "08_勝利シェア推移", "主要種牡馬の勝利シェア推移")
    era = A.sire_by_era(df)
    w.csv(era, "08_種牡馬_年代別TOP10")
    era_wide = era.pivot(index="順位", columns="era", values="sire")
    img["era_table"] = table_image(w, era_wide.reset_index(), "08_年代別TOP10", "年代別 種牡馬リーディング（勝利数）",
                                   ["順位"] + list(era_wide.columns))
    dera = A.damsire_by_era(df)
    w.csv(dera, "08_母父_年代別TOP10")
    dera_wide = dera.pivot(index="順位", columns="era", values="damsire")
    img["damsire_era_table"] = table_image(w, dera_wide.reset_index(), "08_母父_年代別TOP10",
                                           "年代別 母父リーディング（勝利数）", ["順位"] + list(dera_wide.columns))
    facts["era"] = era

    draft = article(info, base, facts, img)
    (w.out / "article_draft.md").write_text(draft, encoding="utf-8")
    return font


def _names(df, col, extra=None):
    parts = []
    for _, r in df.iterrows():
        s = f"{r[col]}"
        if extra:
            s += f"（{extra(r)}）"
        parts.append(s)
    return "、".join(parts)


def _img(lines, path):
    if path:
        lines.append(f"![]({path})\n")


def _wins(r):
    return "{:,}勝".format(int(r["1着"]))


def _heavy(r):
    return "{} +{:.1f}pt".format(r["surface"], r["道悪での上積み"])


def _nick(r):
    return "母父{} +{:.1f}pt".format(r["damsire"], r["複勝率の上積み"])


def article(info, base, f, img):
    y0, y1 = info["year_min"], info["year_max"]
    L = []
    L.append(f"# 【{y1 - y0 + 1}年分のデータで検証】JRA血統分析 — 種牡馬・母父・ニックス・回収率\n")
    L.append("> ※この下書きは集計から自動で作ったものです。【考察】の部分を自分の言葉で書き足してから公開してください。\n")
    L.append("## はじめに\n")
    L.append(f"{y0}年〜{y1}年のJRA平地競走、のべ{info['rows_used']:,}頭の出走データを集計しました。"
             f"全体の勝率は{base['勝率']:.1f}%、複勝率は{base['複勝率']:.1f}%です。"
             "この数字を基準に、血統ごとの得意・不得意を見ていきます。\n")
    L.append("【考察】この記事を書いた目的・読者に伝えたいこと\n")

    L.append("## 1. 種牡馬の総合成績\n")
    _img(L, img.get('sire_bar'))
    L.append(f"勝利数の上位は{_names(f['sire_top'], 'sire', _wins)}でした。\n")
    _img(L, img.get('sire_table'))
    L.append("【考察】\n")

    L.append("## 2. 芝・ダート × 距離\n")
    for s in ("芝", "ダート"):
        L.append(f"### {s}\n")
        L.append(f"{s}の勝利数上位は{_names(f['top_' + s], 'sire')}。\n")
        _img(L, img.get('dist_' + s))
        L.append("赤いマスは全体平均より複勝率が高い条件、青いマスは低い条件です。\n")
        L.append("【考察】\n")

    L.append("## 3. 競馬場別\n")
    for s in ("芝", "ダート"):
        _img(L, img.get('course_' + s))
    L.append("【考察】\n")

    L.append("## 4. 馬場状態（道悪巧者）\n")
    L.append(f"良馬場より道悪（稍重〜不良）で複勝率が上がる種牡馬の上位は"
             f"{_names(f['heavy_top'], 'sire', _heavy)}でした。\n")
    _img(L, img.get('going_table'))
    L.append("【考察】\n")

    L.append("## 5. 母父の傾向\n")
    _img(L, img.get('damsire_bar'))
    _img(L, img.get('damsire_table'))
    L.append("【考察】\n")

    L.append("## 6. 父×母父のニックス\n")
    L.append("父の産駒全体の複勝率と比べて、特定の母父と組んだときにどれだけ上がるかを見ました。\n")
    L.append(f"上積みが大きかったのは"
             f"{_names(f['nick_top'], 'sire', _nick)}です。\n")
    _img(L, img.get('nick_table'))
    L.append("【考察】出走数が少ない組み合わせは偶然の影響も大きいので、出走数とあわせて見てください。\n")

    if "roi_table" in img:
        L.append("## 7. 回収率で見た狙い目\n")
        L.append("単勝回収率は1頭の大穴で大きく跳ねることがあるため、最高配当を1本除いた回収率でも並べています。"
                 "除いても100%を超えている条件ほど、再現性が期待できます。\n")
        _img(L, img.get('roi_table'))
        L.append("【考察】\n")

    L.append("## 8. 年代ごとの勢力の変化\n")
    _img(L, img.get('era_line'))
    _img(L, img.get('era_table'))
    _img(L, img.get('damsire_era_table'))
    L.append("【考察】\n")

    L.append("## まとめ\n")
    L.append("【考察】特に伝えたいポイントを3つほど\n")
    L.append("---\n")
    L.append(f"集計条件：{y0}〜{y1}年 JRA平地（障害を除く）／取消・除外は除外／データ：TARGET frontier JV。"
             "回収率は100円ずつ買い続けた場合の払戻率です。\n")
    return "\n".join(L)
