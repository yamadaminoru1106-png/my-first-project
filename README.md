# JRA 血統分析（TARGET frontier JV の CSV 用）

TARGET frontier JV から出力した CSV を読み込み、次の分析をまとめて出力します。

1. 種牡馬別の成績（芝/ダート・距離・競馬場・馬場状態ごと）
2. 母父の傾向
3. 父×母父のニックス
4. 回収率（単勝・複勝）で見た狙い目の血統
5. 年代ごとの勢力の変化

出力は、Excel で開ける集計表（CSV）、note に貼るための画像（PNG）、記事の下書き（Markdown）の 3 種類です。
note の記事では表が使えないので、表もすべて画像にしています。

## 準備（初回だけ）

1. Python 3.9 以上をインストールする（Windows なら https://www.python.org/ から。インストール時に「Add Python to PATH」にチェック）
2. このフォルダでコマンドプロンプト（またはターミナル）を開き、次を実行する

```
pip install -r requirements.txt
```

## TARGET から出力する CSV

1 行が「1 頭の 1 走」になる形で、次の列を含めて CSV 出力してください（ヘッダー行付き）。

| 必須 | 列の例 |
|---|---|
| 必須 | 年（または日付）、場所、芝・ダ、距離、馬場状態、確定着順（着順）、父馬名（種牡馬）、母の父馬名（母父） |
| 回収率に必要 | 単勝オッズ（または単勝配当）、複勝配当 |
| あると便利 | 馬名、人気 |

- 20 年分を 1 ファイルにしても、年ごとに分けても大丈夫です。`data` フォルダに全部入れてください（サブフォルダも読みます）。
- 文字コードは Shift_JIS のままで構いません。
- 複勝配当の列がない場合、複勝回収率は出さずにスキップします（推計はしません）。

## 使い方

### 1. 列名の確認

```
python -m pedigree_analysis check --data data
```

どの列を使うかが表示されます。`=> OK` なら次へ進めます。
「足りない必須列」が出たら、`columns.json` を作って自分の CSV の列名を指定します。

```json
{
  "sire": "父",
  "damsire": "母父名",
  "finish": "着順"
}
```

```
python -m pedigree_analysis check --data data --columns columns.json
```

指定できる名前: `year` `date` `course` `surface` `distance` `going` `finish` `horse`
`sire` `damsire` `win_odds` `win_payout` `place_payout` `popularity`

### 2. 分析の実行

```
python -m pedigree_analysis run --data data --out output
```

期間を絞る場合は `--from 2006 --to 2025` を付けます。

### 3. 出力されるもの

```
output/
  article_draft.md   note 記事の下書き（【考察】の部分を書き足して使う）
  images/            note に貼る画像（グラフ・表）
  tables/            全集計の CSV（Excel で開ける）
```

## 集計のルール

- 対象は JRA 平地（障害は除外）。取消・除外など着順が数字でない行は除外。
- 距離区分は SMILE 区分（S:〜1300m、M:1301〜1899m、I:1900〜2100m、L:2101〜2700m、E:2701m〜）。
- 回収率は 100 円ずつ買い続けた場合の払戻率（%）。単勝はオッズ×100 で計算（単勝配当の列があればそちらを使う）。
- 1 頭の大穴で回収率が跳ねていないか見るため、「最高配当を 1 本除いた単回収率」も出しています。
- ランキングに載せる最低出走数は `pedigree_analysis/config.py` の `MIN_STARTS` で変えられます。

## 動作確認用のダミーデータ

実データがなくても動きを試せます（中身はランダムで、実際の成績ではありません）。

```
python tools/make_sample_data.py sample_data
python -m pedigree_analysis run --data sample_data --out output
```

## 注意

JRA-VAN のデータは再配布が規約で制限されています。`data/` と `output/` は `.gitignore` に入れてあり、
リポジトリには入らないようにしています。note に載せるのは集計結果だけにしてください。
