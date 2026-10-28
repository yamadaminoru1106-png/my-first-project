"""使い方:
  python -m pedigree_analysis check --data data
  python -m pedigree_analysis run   --data data --out output [--from 2006 --to 2025]
"""

import argparse
import sys

from . import load, report


def main(argv=None):
    p = argparse.ArgumentParser(prog="pedigree_analysis", description="TARGET frontier JV の CSV から血統分析をする")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="CSV の列名と、どの列を使うかを確認する")
    c.add_argument("--data", default="data", help="CSV を置いたフォルダ")
    c.add_argument("--columns", help="列名を指定する JSON（任意）")

    r = sub.add_parser("run", help="分析して CSV・画像・記事下書きを出力する")
    r.add_argument("--data", default="data", help="CSV を置いたフォルダ")
    r.add_argument("--out", default="output", help="出力先フォルダ")
    r.add_argument("--columns", help="列名を指定する JSON（任意）")
    r.add_argument("--from", dest="year_from", type=int, help="この年から")
    r.add_argument("--to", dest="year_to", type=int, help="この年まで")

    a = p.parse_args(argv)
    overrides = load.load_overrides(a.columns)

    if a.cmd == "check":
        print(load.describe_columns(a.data, overrides))
        return 0

    df, info = load.load_all(a.data, overrides, a.year_from, a.year_to)
    print(f"読み込み: {len(info['files'])} ファイル / {info['rows_raw']:,} 行 -> 分析対象 {info['rows_used']:,} 行"
          f"（{info['year_min']}〜{info['year_max']}年）")
    if not info["has_win_return"]:
        print("注意: 単勝オッズ（または単勝配当）の列がないため、単勝回収率は出しません")
    if not info["has_place_return"]:
        print("注意: 複勝配当の列がないため、複勝回収率は出しません")
    font = report.build(df, info, a.out)
    if not font:
        print("注意: 日本語フォントが見つからず、グラフの文字が化ける可能性があります")
    print(f"完了: {a.out}/article_draft.md と {a.out}/images/, {a.out}/tables/ を確認してください")
    return 0


if __name__ == "__main__":
    sys.exit(main())
