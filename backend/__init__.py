"""
MediAI backend package.  `create_app()` builds the Flask application:
  * serves the website files from /frontend  (so you only run ONE server)
  * exposes the JSON API under /api/...
"""
import logging

from flask import Flask, send_from_directory

from .config import Config
from .routes import register_routes
from .utils.errors import register_error_handlers


def create_app() -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # static_url_path="" means /css/style.css is served straight from frontend/css/style.css
    app = Flask(__name__, static_folder=str(Config.FRONTEND_DIR), static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
    app.json.ensure_ascii = False  # keep Hindi/Telugu/Tamil readable in JSON

    register_error_handlers(app)
    register_routes(app)

    @app.get("/")
    def home():
        return send_from_directory(app.static_folder, "index.html")

    @app.after_request
    def add_safety_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        # Never let the browser cache medical answers.
        if response.mimetype == "application/json":
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
