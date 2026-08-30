from flask import Flask, render_template

from app import db
from app.commandes import enregistrer_commandes
from app.config import Config
from app.securite import login_manager


def create_app():
    """Construit et configure l'application Flask.

    On utilise le pattern "factory" (une fonction qui construit l'app) plutôt
    qu'un objet Flask créé directement au niveau du module. Ça permet de créer
    plusieurs instances de l'application (utile pour les tests automatisés
    plus tard) et d'éviter les problèmes d'import circulaire entre modules.
    """
    app = Flask(__name__)
    config = Config()
    app.config.from_object(config)

    db.init_pool(config.DB_CONNINFO)
    login_manager.init_app(app)

    from app.blueprints.accueil.routes import bp as accueil_bp
    from app.blueprints.auth.routes import bp as auth_bp
    from app.blueprints.contacts.routes import bp as contacts_bp
    from app.blueprints.documents.routes import bp as documents_bp
    from app.blueprints.dossiers.routes import bp as dossiers_bp
    app.register_blueprint(accueil_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(dossiers_bp)

    @app.errorhandler(403)
    def acces_refuse(erreur):
        return render_template("erreur_403.html"), 403

    enregistrer_commandes(app)

    return app
