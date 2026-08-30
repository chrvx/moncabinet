from flask import Blueprint, render_template
from flask_login import login_required

from app import db

# Un "blueprint" regroupe un ensemble de routes qui vont ensemble (ici, les
# pages d'accueil). Chaque futur domaine métier (contacts, dossiers...) aura
# le sien, enregistré dans app/__init__.py comme celui-ci.
bp = Blueprint("accueil", __name__)


@bp.route("/")
@login_required
def index():
    """Page de test : prouve que Flask est bien connecté à PostgreSQL."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version_postgres = cur.fetchone()[0]

    return render_template("accueil/index.html", version_postgres=version_postgres)
