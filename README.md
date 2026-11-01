# かんたんER図メーカー（ermaker）

テーブル定義を簡単なテキスト記法で書くと、ER 図（SVG）を描く小さな Web ツールです。

## 記法

1行に1テーブル、次の形式で書きます。

```
users(id PK, name, email)
posts(id PK, user_id FK->users.id, title, body)
comments(id PK, post_id FK->posts.id, user_id FK->users.id, body)
```

- 列名の後に `PK` と書くと主キーになります。
- `FK->参照テーブル.参照列` と書くと外部キーになり、参照先テーブルへ線が引かれます。
- 解釈できない行があると、どの行がおかしいかメッセージで知らせます（落ちたりはしません）。

最初の表示ではサンプル定義の図が出ているので、そのまま書き換えて「ER図を描く」を押せば自分の設計で試せます。図の下には、読み取ったテーブルの一覧（列・PK・FK）もテキストで表示されます。

データベースは持たず、入力は保存されません。

## ローカル実行

```bash
pip install -r requirements.txt
python app.py
# http://localhost:5000
```

## テスト

```bash
python -m unittest discover -s tests
```

## Render へのデプロイ

`render.yaml` 同梱。無料プラン（free）の Web Service としてデプロイできます（healthCheckPath: `/healthz`）。

## 制限事項（正直なところ）

- 配置は2列の単純なグリッドです。テーブルが多いと線が交差しますし、ドラッグでの並べ替えもできません。
- 型（VARCHAR など）や NULL 可否、リレーションの多重度（1:N の表記）には対応していません。PK と FK だけの最小記法です。
- SVG のダウンロードボタンはありません（ブラウザの機能で保存してください）。
- ログイン機能はありません。

## ライセンス

MIT License
