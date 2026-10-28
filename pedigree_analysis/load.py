"""TARGET の CSV を読み込み、分析しやすい形にそろえる。"""

import json
from pathlib import Path

import pandas as pd

from .config import COLUMN_ALIASES, DISTANCE_BANDS, REQUIRED

ENCODINGS = ["cp932", "utf-8-sig", "utf-8"]


def read_csv_any(path):
    """TARGET の CSV は Shift_JIS(cp932) が多いので順に試す。"""
    last_error = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, dtype=str, low_memory=False)
        except UnicodeDecodeError as e:
            last_error = e
    raise last_error


def list_csv_files(data_dir):
    files = sorted(p for p in Path(data_dir).rglob("*") if p.suffix.lower() in (".csv", ".txt"))
    if not files:
        raise FileNotFoundError(f"{data_dir} に CSV が見つかりません")
    return files


def resolve_columns(header, overrides=None):
    """CSV の列名から、内部名 -> 実際の列名 の対応を作る。"""
    header = [h.strip() for h in header]
    mapping = {}
    for key, candidates in COLUMN_ALIASES.items():
        if overrides and key in overrides:
            if overrides[key] in header:
                mapping[key] = overrides[key]
            continue
        for c in candidates:
            if c in header:
                mapping[key] = c
                break
    return mapping


def load_overrides(path):
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _to_num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def _year(df, mapping):
    if "year" in mapping:
        y = _to_num(df[mapping["year"]])
        # TARGET は年を2桁で出すことがある（05 -> 2005）
        y = y.where(y >= 100, y + 2000)
        return y
    if "date" in mapping:
        digits = df[mapping["date"]].astype(str).str.extract(r"(\d{2,4})")[0]
        y = pd.to_numeric(digits, errors="coerce")
        return y.where(y >= 100, y + 2000)
    raise ValueError("年（または日付）の列が見つかりません")


def _surface(s):
    s = s.astype(str).str.strip()
    out = pd.Series("その他", index=s.index)
    out[s.str.startswith("芝")] = "芝"
    out[s.str.startswith("ダ")] = "ダート"
    out[s.str.contains("障")] = "障害"
    return out


def _going(s):
    s = s.astype(str).str.strip()
    out = pd.Series(None, index=s.index, dtype=object)
    out[s.str.startswith("良")] = "良"
    out[s.str.startswith("稍")] = "稍重"
    out[s.str.startswith("重")] = "重"
    out[s.str.startswith("不")] = "不良"
    return out


def _course(s):
    # "1回東京2日" のような表記でも競馬場名だけを取り出す
    names = "札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉"
    extracted = s.astype(str).str.extract(f"({names})")[0]
    return extracted.fillna(s.astype(str).str.strip())


def _distance_band(d):
    out = pd.Series(None, index=d.index, dtype=object)
    for lo, hi, label in DISTANCE_BANDS:
        out[(d >= lo) & (d <= hi)] = label
    return out


def _clean_name(s):
    return s.astype(str).str.strip().str.replace(r"\s+", "", regex=True).replace({"nan": None, "": None})


def normalize(raw, mapping):
    missing = [k for k in REQUIRED if k not in mapping]
    if missing:
        raise ValueError(f"必須の列が見つかりません: {missing}（columns.json で列名を指定してください）")

    df = pd.DataFrame(index=raw.index)
    df["year"] = _year(raw, mapping)
    df["course"] = _course(raw[mapping["course"]])
    df["surface"] = _surface(raw[mapping["surface"]])
    df["distance"] = _to_num(raw[mapping["distance"]])
    df["dist_band"] = _distance_band(df["distance"])
    df["going"] = _going(raw[mapping["going"]])
    df["finish"] = _to_num(raw[mapping["finish"]])
    df["sire"] = _clean_name(raw[mapping["sire"]])
    df["damsire"] = _clean_name(raw[mapping["damsire"]])
    if "horse" in mapping:
        df["horse"] = _clean_name(raw[mapping["horse"]])
    if "popularity" in mapping:
        df["popularity"] = _to_num(raw[mapping["popularity"]])

    # 単勝の払戻（100円あたり）: 単勝配当があればそれ、なければ オッズ×100
    win = df["finish"] == 1
    if "win_payout" in mapping:
        df["win_return"] = _to_num(raw[mapping["win_payout"]]).where(win, 0).fillna(0)
    elif "win_odds" in mapping:
        df["win_return"] = (_to_num(raw[mapping["win_odds"]]) * 100).where(win, 0).fillna(0)
    else:
        df["win_return"] = None

    # 複勝の払戻: 複勝配当の列があるときだけ計算する（推計はしない）
    if "place_payout" in mapping:
        df["place_return"] = _to_num(raw[mapping["place_payout"]]).where(df["finish"] <= 3, 0).fillna(0)
    else:
        df["place_return"] = None

    return df


def load_all(data_dir, overrides=None, year_from=None, year_to=None, include_jump=False):
    """フォルダ内の CSV をすべて読み込んで 1 つの表にする。"""
    frames, log = [], []
    for path in list_csv_files(data_dir):
        raw = read_csv_any(path)
        raw.columns = [c.strip() for c in raw.columns]
        mapping = resolve_columns(raw.columns, overrides)
        df = normalize(raw, mapping)
        frames.append(df)
        log.append((path.name, len(df)))
    df = pd.concat(frames, ignore_index=True)

    n_raw = len(df)
    # 取消・除外・中止など着順が数字でない行は除く
    df = df[df["finish"].notna() & (df["finish"] > 0)]
    df = df[df["sire"].notna() & df["damsire"].notna()]
    if not include_jump:
        df = df[df["surface"].isin(["芝", "ダート"])]
    if year_from:
        df = df[df["year"] >= year_from]
    if year_to:
        df = df[df["year"] <= year_to]
    info = {
        "files": log,
        "rows_raw": n_raw,
        "rows_used": len(df),
        "has_win_return": df["win_return"].notna().any(),
        "has_place_return": df["place_return"].notna().any(),
        "year_min": int(df["year"].min()) if len(df) else None,
        "year_max": int(df["year"].max()) if len(df) else None,
    }
    return df.reset_index(drop=True), info


def describe_columns(data_dir, overrides=None):
    """各 CSV の列名と、どの列を使うかを表示する（check コマンド用）。"""
    lines = []
    for path in list_csv_files(data_dir):
        raw = read_csv_any(path)
        cols = [c.strip() for c in raw.columns]
        mapping = resolve_columns(cols, overrides)
        lines.append(f"■ {path.name}（{len(raw):,} 行）")
        lines.append("  列名: " + ", ".join(cols))
        for key in COLUMN_ALIASES:
            mark = "必須" if key in REQUIRED else "任意"
            lines.append(f"  [{mark}] {key:13s} -> {mapping.get(key, '（見つからない）')}")
        missing = [k for k in REQUIRED if k not in mapping]
        lines.append("  => OK" if not missing else f"  => 足りない必須列: {missing}")
    return "\n".join(lines)
