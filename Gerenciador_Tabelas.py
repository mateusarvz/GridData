import os
import tempfile
import threading
import webbrowser

import pandas as pd
from flask import Flask, render_template_string, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

ALLOWED_EXTENSIONS = {"csv", "parquet", "xls", "xlsx", "json"}
TABLES_STORE = {}


@app.before_request
def clear_table_state():
    TABLES_STORE.clear()

HTML_TEMPLATE = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Visualizador de Tabelas</title>
  <style>
    :root {
      --bg: #07111f;
      --panel: #101b2d;
      --panel-2: #14233a;
      --text: #f2f6ff;
      --muted: #8ea2bf;
      --accent: #4fd1c5;
      --accent-2: #6c7cff;
      --border: rgba(255,255,255,0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: linear-gradient(135deg, var(--bg), #0f1729 60%, #121f34);
      color: var(--text);
      min-height: 100vh;
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 32px 20px 60px; }
    .hero {
      background: linear-gradient(120deg, rgba(79,209,197,0.16), rgba(108,124,255,0.12));
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 16px 45px rgba(0,0,0,0.22);
    }
    .hero h1 { margin: 0 0 10px; font-size: 32px; }
    .hero p { margin: 0; color: var(--muted); max-width: 700px; line-height: 1.6; }
    .card {
      margin-top: 22px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 20px;
    }
    form { display: flex; flex-direction: column; gap: 14px; }
    .upload-box {
      border: 1px dashed rgba(79,209,197,0.5);
      border-radius: 16px;
      padding: 18px;
      background: rgba(79,209,197,0.06);
    }
    input[type="file"] { color: var(--muted); }
    button {
      border: none;
      border-radius: 999px;
      padding: 11px 16px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      color: white;
      font-weight: 600;
      cursor: pointer;
      width: fit-content;
    }
    .message {
      padding: 12px 14px;
      border-radius: 12px;
      margin-top: 12px;
      background: rgba(255,255,255,0.05);
      color: var(--text);
      border: 1px solid var(--border);
    }
    .message.error { border-color: rgba(255,109,109,0.4); color: #ffd2d2; }
    .table-card { margin-top: 22px; }
    .meta { color: var(--muted); margin-bottom: 10px; }
    table {
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 12px;
      background: var(--panel-2);
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      text-align: left;
      font-size: 14px;
    }
    th { background: rgba(79,209,197,0.12); color: #dffcf8; }
    tbody tr:hover { background: rgba(255,255,255,0.04); }
    .footer { color: var(--muted); margin-top: 20px; font-size: 13px; }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Visualizador de Tabelas</h1>
      <p>Carregue arquivos CSV, Parquet, Excel ou JSON e veja suas tabelas em uma interface limpa e profissional.</p>
    </section>

    <section class="card">
      <form method="post" enctype="multipart/form-data">
        <div class="upload-box">
          <label for="files">Escolha um ou mais arquivos</label><br><br>
          <input id="files" name="files" type="file" multiple accept=".csv,.parquet,.xls,.xlsx,.json">
        </div>
        <button type="submit">Carregar</button>
      </form>

      {% for message in messages %}
        <div class="message {% if 'não foi possível' in message or 'Selecione' in message %}error{% endif %}">{{ message }}</div>
      {% endfor %}
    </section>

    {% for table in tables %}
    <section class="card table-card">
      <h3>{{ table.name }}</h3>
      <div class="meta">Linhas: {{ table.rows }} · Colunas: {{ table.columns }}</div>
      {{ table.html|safe }}
    </section>
    {% endfor %}

    <div class="footer">Formato suportado: CSV, Parquet, Excel (.xls/.xlsx) e JSON.</div>
  </div>
</body>
</html>
"""


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def read_table(uploaded_file):
    extension = uploaded_file.filename.rsplit(".", 1)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
        uploaded_file.save(temp_file.name)
        temp_path = temp_file.name

    try:
        if extension == "csv":
            return pd.read_csv(temp_path)
        if extension == "parquet":
            return pd.read_parquet(temp_path)
        if extension in {"xls", "xlsx"}:
            return pd.read_excel(temp_path)
        if extension == "json":
            return pd.read_json(temp_path)
        raise ValueError("Formato não suportado")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route("/", methods=["GET", "POST"])
def index():
    tables = []
    messages = []

    if request.method == "POST":
        uploaded_files = request.files.getlist("files")
        if not uploaded_files or all(item.filename == "" for item in uploaded_files):
            messages.append("Selecione pelo menos um arquivo para continuar.")
        else:
            for item in uploaded_files:
                if item.filename == "":
                    continue
                if not allowed_file(item.filename):
                    messages.append(f"Formato não suportado: {item.filename}")
                    continue
                try:
                    dataframe = read_table(item)
                    TABLES_STORE[item.filename] = dataframe
                    preview = dataframe.head(50)
                    tables.append({
                        "name": item.filename,
                        "rows": len(dataframe),
                        "columns": len(dataframe.columns),
                        "html": preview.to_html(index=False, border=0),
                    })
                except Exception as error:
                    messages.append(f"Não foi possível carregar {item.filename}: {error}")

    return render_template_string(HTML_TEMPLATE, tables=tables, messages=messages)


def open_browser():
    webbrowser.open_new_tab("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
