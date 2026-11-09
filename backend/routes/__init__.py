"""Registers every group of API endpoints (called Blueprints in Flask)."""
from .common_routes import bp as common_bp
from .medicine_routes import bp as medicine_bp
from .report_routes import bp as report_bp
from .summary_routes import bp as summary_bp
from .symptom_routes import bp as symptom_bp


def register_routes(app):
    for blueprint in (common_bp, report_bp, symptom_bp, medicine_bp, summary_bp):
        app.register_blueprint(blueprint)
