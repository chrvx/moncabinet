from functools import wraps

from flask import abort
from flask_login import LoginManager, UserMixin, current_user

from app.repositories import utilisateurs

# LoginManager gère la mécanique de session : il sait qui est connecté sur
# quelle requête, et redirige automatiquement vers la page de connexion
# (login_view) quand une route protégée par @login_required est visitée
# sans être authentifié.
login_manager = LoginManager()
login_manager.login_view = "auth.connexion"
login_manager.login_message = "Merci de vous connecter pour accéder à cette page."


class UtilisateurConnecte(UserMixin):
    """Habille notre dataclass Utilisateur pour Flask-Login.

    Flask-Login a besoin d'un objet qui sait dire son identifiant (get_id) et
    s'il est actif. UserMixin fournit des valeurs par défaut raisonnables
    pour le reste (is_authenticated, is_anonymous) ; on ne redéfinit que ce
    qui doit dépendre de nos propres données.
    """

    def __init__(self, utilisateur):
        self.utilisateur = utilisateur

    def get_id(self):
        return str(self.utilisateur.id)

    @property
    def id(self):
        return self.utilisateur.id

    @property
    def is_active(self):
        return self.utilisateur.actif

    @property
    def nom(self):
        return self.utilisateur.nom

    @property
    def role(self):
        return self.utilisateur.role


@login_manager.user_loader
def charger_utilisateur(utilisateur_id):
    """Appelée par Flask-Login à chaque requête pour retrouver l'utilisateur
    à partir de l'identifiant stocké dans la session (le cookie)."""
    utilisateur = utilisateurs.recuperer_par_id(int(utilisateur_id))
    if utilisateur is None:
        return None
    return UtilisateurConnecte(utilisateur)


def role_requis(*roles_autorises):
    """Restreint une route aux comptes dont le rôle figure dans
    roles_autorises. Première vérification de permission de l'application :
    le système complet (accès restreint aux dossiers pour un stagiaire,
    visibilité RGPD) reste un chantier séparé, à construire le moment venu."""

    def decorateur(fonction):
        @wraps(fonction)
        def enveloppe(*args, **kwargs):
            if current_user.role not in roles_autorises:
                abort(403)
            return fonction(*args, **kwargs)

        return enveloppe

    return decorateur
