"""動作確認用のダミー CSV を作る。中身はランダムで、実際の成績ではない。

  python tools/make_sample_data.py sample_data
"""

import csv
import random
import sys
from pathlib import Path

SIRES = [f"種牡馬{c}" for c in "ABCDEFGHIJKLMNOPQRST"]
DAMSIRES = [f"母父{c}" for c in "ABCDEFGHIJKLMNO"]
COURSES = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]
HEADER = ["年", "月", "日", "場所", "芝・ダ", "距離", "馬場状態", "馬名", "確定着順",
          "人気", "単勝オッズ", "複勝配当", "父馬名", "母の父馬名"]


def main(out_dir, years=range(2006, 2026), races_per_year=400, seed=1):
    rnd = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    strength = {s: rnd.uniform(0.6, 1.6) for s in SIRES + DAMSIRES}
    for y in years:
        rows = []
        # 年によって勢力が変わるように、種牡馬ごとに活躍期間をずらす
        active = [s for i, s in enumerate(SIRES) if (i - (y - 2006)) % 20 < 12]
        for _ in range(races_per_year):
            surface = rnd.choice(["芝", "ダ"])
            dist = rnd.choice([1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 3000])
            going = rnd.choices(["良", "稍重", "重", "不良"], [70, 15, 10, 5])[0]
            n = rnd.randint(8, 18)
            field = [(rnd.choice(active), rnd.choice(DAMSIRES)) for _ in range(n)]
            score = [rnd.random() * strength[s] * strength[d] for s, d in field]
            order = sorted(range(n), key=lambda i: -score[i])
            odds = [round(1.8 * 1.45 ** k * rnd.uniform(0.9, 1.1), 1) for k in range(n)]
            pop = sorted(range(n), key=lambda i: -(score[i] + rnd.random()))
            for rank, i in enumerate(order, 1):
                p = pop.index(i) + 1
                place = int(odds[p - 1] * 100 / 3.5) // 10 * 10 + 100 if rank <= 3 else 0
                rows.append([y % 100, 1, 1, rnd.choice(COURSES), surface, dist, going, f"馬{y}_{i}",
                             rank, p, odds[p - 1], place, field[i][0], field[i][1]])
        with open(out / f"sample_{y}.csv", "w", encoding="cp932", newline="") as f:
            csv.writer(f).writerows([HEADER] + rows)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample_data")
