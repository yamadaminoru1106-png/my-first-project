"""列名の対応表としきい値の設定。

TARGET frontier JV の CSV は出力設定によって列名が変わるため、
よく使われる列名の候補をここに並べておき、最初に見つかったものを使う。
自分の CSV に合わない場合は columns.json で上書きできる（README 参照）。
"""

# 内部で使う名前 -> TARGET の CSV で使われうる列名の候補
COLUMN_ALIASES = {
    "year": ["年", "開催年", "年度"],
    "date": ["日付", "年月日", "開催日"],
    "course": ["場所", "場名", "競馬場", "開催場"],
    "surface": ["芝・ダ", "芝ダ", "芝/ダ", "芝・ダ・障", "トラック", "コース"],
    "distance": ["距離"],
    "going": ["馬場状態", "馬場", "馬場状態(暫定)"],
    "finish": ["確定着順", "着順", "着"],
    "horse": ["馬名"],
    "sire": ["父馬名", "種牡馬", "種牡馬名", "父"],
    "damsire": ["母の父馬名", "母父馬名", "母父馬", "母父", "母の父"],
    "win_odds": ["単勝オッズ", "単オッズ", "オッズ", "単勝"],
    "win_payout": ["単勝配当"],
    "place_payout": ["複勝配当", "複勝払戻", "複勝"],
    "popularity": ["人気", "人気順", "単勝人気"],
}

# 必須の列（これがないと分析できない）
REQUIRED = ["course", "surface", "distance", "going", "finish", "sire", "damsire"]

# 距離区分（SMILE 区分）
DISTANCE_BANDS = [
    (0, 1300, "S(〜1300m)"),
    (1301, 1899, "M(1301〜1899m)"),
    (1900, 2100, "I(1900〜2100m)"),
    (2101, 2700, "L(2101〜2700m)"),
    (2701, 9999, "E(2701m〜)"),
]

# 集計に載せる最低出走数
MIN_STARTS = {
    "sire_total": 200,      # 種牡馬の総合ランキング
    "sire_condition": 50,   # 種牡馬 × 条件
    "damsire": 200,         # 母父の総合ランキング
    "damsire_condition": 50,
    "nick": 40,             # 父 × 母父
    "roi": 100,             # 回収率の狙い目
}

# 年代区分の幅（年）
ERA_SPAN = 5

# グラフで使う日本語フォントの候補（上から順に、PC に入っているものを使う）
JP_FONTS = [
    "Yu Gothic", "Meiryo", "MS Gothic",          # Windows
    "Hiragino Sans", "Hiragino Kaku Gothic ProN",  # Mac
    "Noto Sans CJK JP", "IPAexGothic", "IPAGothic", "WenQuanYi Zen Hei",
]
