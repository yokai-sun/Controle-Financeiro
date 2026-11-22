"""Controle Financeiro - servidor Flask.

Execute:  python app.py   (ou dê dois cliques em iniciar.bat) e abra http://localhost:5050
"""
import os

from flask import Flask, render_template, send_from_directory

from database import DB_PATH, init_db
from routes.api import api


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DB_PATH
    app.config["JSON_AS_ASCII"] = False
    app.json.ensure_ascii = False
    init_db(app.config["DB_PATH"])
    app.register_blueprint(api)

    @app.after_request
    def cors(resp):
        # Permite que um futuro app mobile/outro front acesse a API.
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        # Sempre conferir com o servidor: evita página nova com servidor velho (ou vice-versa)
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/manifest.json")
    def manifest():
        return send_from_directory(app.static_folder, "manifest.json")

    @app.get("/sw.js")
    def service_worker():
        resp = send_from_directory(app.static_folder, "sw.js")
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    return app


if __name__ == "__main__":
    # 5050 para não conflitar com outros projetos que usam a porta 5000
    port = int(os.environ.get("PORT", 5050))
    print(f"\n  Controle Financeiro rodando em http://localhost:{port}\n  (feche esta janela para desligar)\n")
    create_app().run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
