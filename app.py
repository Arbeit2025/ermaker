"""かんたんER図メーカー ermaker

テーブル定義を簡単なテキスト記法で書くと、ER図（SVG）を描くツール。

記法（1行に1テーブル）:
    users(id PK, name, email)
    posts(id PK, user_id FK->users.id, title, body)

- "PK" を付けた列が主キー、"FK->テーブル.列" が外部キー。
- サーバー側で SVG を組み立てる。DB なし。
単一ファイル Flask。
"""
import os
import re
from html import escape

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

TABLE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$")
FK_RE = re.compile(r"^FK->([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")

SAMPLE = """users(id PK, name, email)
posts(id PK, user_id FK->users.id, title, body)
comments(id PK, post_id FK->posts.id, user_id FK->users.id, body)"""

BOX_W = 190
HEADER_H = 26
ROW_H = 19
GAP_X = 90
GAP_Y = 50
COLS = 2


def parse_definitions(text):
    """定義テキストを (tables, errors) に変換する。

    tables: [{"name": str, "columns": [{"name","pk","fk"}...]}...]
      fk は None か (参照テーブル, 参照列) のタプル。
    errors: 解釈できなかった行の説明（文字列）のリスト。
    """
    tables = []
    errors = []
    for lineno, raw in enumerate((text or "").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        m = TABLE_RE.match(line)
        if not m:
            errors.append(f"{lineno}行目： 「{line}」は解釈できませんでした（記法： テーブル名(列, 列, ...)）")
            continue
        name, inside = m.group(1), m.group(2).strip()
        columns = []
        ok = True
        if inside:
            for part in inside.split(","):
                tokens = part.strip().split()
                if not tokens:
                    ok = False
                    break
                col = {"name": tokens[0], "pk": False, "fk": None}
                for tok in tokens[1:]:
                    if tok == "PK":
                        col["pk"] = True
                    else:
                        fm = FK_RE.match(tok)
                        if fm:
                            col["fk"] = (fm.group(1), fm.group(2))
                        else:
                            ok = False
                columns.append(col)
        if not ok or not columns:
            errors.append(f"{lineno}行目： 「{line}」の列の書き方が解釈できませんでした")
            continue
        tables.append({"name": name, "columns": columns})
    return tables, errors


def layout(tables):
    """各テーブルに (x, y, height) を割り当てる（2列グリッド、列ごとに縦積み）。"""
    positions = {}
    col_y = [10] * COLS
    for i, t in enumerate(tables):
        c = i % COLS
        h = HEADER_H + ROW_H * len(t["columns"]) + 6
        x = 10 + c * (BOX_W + GAP_X)
        y = col_y[c]
        positions[t["name"]] = (x, y, h)
        col_y[c] = y + h + GAP_Y
    width = 10 + COLS * BOX_W + (COLS - 1) * GAP_X + 10
    height = max(col_y) - GAP_Y + 10 if tables else 40
    return positions, width, height


def render_svg(tables):
    positions, width, height = layout(tables)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="background:#fff;border:1px solid #ccc">'
    ]
    # FK の線を先に描く（箱の下に来ないよう順序は線→箱）
    for t in tables:
        x1, y1, h1 = positions[t["name"]]
        for col in t["columns"]:
            if col["fk"] and col["fk"][0] in positions:
                x2, y2, h2 = positions[col["fk"][0]]
                parts.append(
                    f'<line x1="{x1 + BOX_W}" y1="{y1 + h1 // 2}" x2="{x2}" y2="{y2 + h2 // 2}" '
                    f'stroke="#7a7" stroke-width="1.5"/>'
                )
    for t in tables:
        x, y, h = positions[t["name"]]
        parts.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" fill="#fdfdf5" stroke="#555"/>')
        parts.append(
            f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{HEADER_H}" fill="#dceadc" stroke="#555"/>'
        )
        parts.append(
            f'<text x="{x + 8}" y="{y + 18}" font-size="13" font-weight="bold">{escape(t["name"])}</text>'
        )
        for j, col in enumerate(t["columns"]):
            cy = y + HEADER_H + 15 + j * ROW_H
            label = col["name"]
            marks = []
            if col["pk"]:
                marks.append("PK")
            if col["fk"]:
                marks.append(f"FK→{col['fk'][0]}.{col['fk'][1]}")
            if marks:
                label += " (" + ", ".join(marks) + ")"
            parts.append(f'<text x="{x + 8}" y="{cy}" font-size="12">{escape(label)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>かんたんER図メーカー</title>
<style>body{font-family:sans-serif;max-width:860px;margin:2em auto;padding:0 1em}
textarea{width:100%}code{background:#f0f0f0;padding:.1em .3em}
.err{background:#fdecea;border:1px solid #c66;padding:.5em 1em;border-radius:8px}</style>
</head><body>
<h1>かんたんER図メーカー</h1>
<p>テーブル定義を1行に1テーブルで書くと、ER図を描きます。<br>
記法：<code>テーブル名(列名, 列名 PK, 列名 FK->参照テーブル.参照列)</code>（PK＝主キー、FK＝外部キー）</p>
<form method="post" action="/">
  <textarea name="definitions" rows="6">{{ definitions }}</textarea><br>
  <button type="submit">ER図を描く</button>
</form>

{% if errors %}
<div class="err"><p>解釈できない行がありました：</p><ul>{% for e in errors %}<li>{{ e }}</li>{% endfor %}</ul></div>
{% endif %}

{% if svg %}
<h2>ER図</h2>
{{ svg | safe }}
<h2>読み取ったテーブル</h2>
<ul>
{% for t in tables %}
<li><strong>{{ t.name }}</strong>：{% for c in t.columns %}{{ c.name }}{% if c.pk %}（PK）{% endif %}{% if c.fk %}（FK→{{ c.fk[0] }}.{{ c.fk[1] }}）{% endif %}{% if not loop.last %}、{% endif %}{% endfor %}</li>
{% endfor %}
</ul>
{% endif %}
</body></html>"""


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        definitions = request.form.get("definitions") or ""
    else:
        definitions = SAMPLE
    tables, errors = parse_definitions(definitions)
    svg = render_svg(tables) if tables else ""
    return render_template_string(
        PAGE, definitions=definitions, tables=tables, errors=errors, svg=svg
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
