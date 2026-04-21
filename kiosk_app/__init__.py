import logging
import os
import re
import secrets
from logging.handlers import RotatingFileHandler

from flask import Flask, Response, render_template, session

from kiosk_app.extensions import bcrypt, csrf, limiter
from kiosk_app.blueprints.admin import admin_bp
from kiosk_app.blueprints.announcements import announcements_bp
from kiosk_app.blueprints.campus import campus_bp
from kiosk_app.blueprints.events import events_bp
from kiosk_app.blueprints.main import main_bp
from kiosk_app.blueprints.offices import offices_bp
from kiosk_app.i18n import get_translator

_KIOSK_SCRIPTS = (
    '<script src="/static/js/kiosk-scale.js"></script>'
    '<script src="/static/js/kiosk-idle.js"></script>'
)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)


def _inject_kiosk_scripts(response: Response) -> Response:
    ctype = response.content_type or ""
    if not ctype.startswith("text/html") or response.direct_passthrough:
        return response

    html = response.get_data(as_text=True)
    if _KIOSK_SCRIPTS in html:
        return response

    lower = html.lower()
    if "</body>" in lower:
        idx = lower.rfind("</body>")
        html = html[:idx] + _KIOSK_SCRIPTS + html[idx:]
    elif "</head>" in lower:
        idx = lower.rfind("</head>")
        html = html[:idx] + _KIOSK_SCRIPTS + html[idx:]
    else:
        html = html + _KIOSK_SCRIPTS

    response.set_data(html)
    return response


def _configure_logging(app: Flask) -> None:
    logs_dir = os.path.join(_PROJECT_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    handler = RotatingFileHandler(
        os.path.join(logs_dir, "kiosk.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(429)
    def too_many_requests(_e):
        return render_template("429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("500 error: %s", e)
        return render_template("500.html"), 500


def _resolve_secret_key() -> str:
    key = os.environ.get("KIOSK_SECRET_KEY")
    if key:
        return key
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "KIOSK_SECRET_KEY must be set when FLASK_ENV=production."
        )
    return secrets.token_hex(32)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.secret_key = _resolve_secret_key()

    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(campus_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(offices_bp)
    app.register_blueprint(admin_bp)

    _configure_logging(app)
    _register_error_handlers(app)

    app.after_request(_inject_kiosk_scripts)

    @app.context_processor
    def inject_i18n():
        lang = session.get("lang", "en")
        return {"t": get_translator(lang), "lang": lang}

    return app
