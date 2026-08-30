from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from app.blueprints.auth.forms import ConnexionForm
from app.repositories import utilisateurs
from app.securite import UtilisateurConnecte

bp = Blueprint("auth", __name__)


@bp.route("/connexion", methods=["GET", "POST"])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for("accueil.index"))

    formulaire = ConnexionForm()

    if formulaire.validate_on_submit():
        utilisateur = utilisateurs.recuperer_par_nom(formulaire.nom.data)
        mot_de_passe_correct = utilisateur is not None and check_password_hash(
            utilisateur.mot_de_passe_hash, formulaire.mot_de_passe.data
        )

        if not mot_de_passe_correct:
            flash("Nom ou mot de passe incorrect.", "erreur")
        elif not utilisateur.actif:
            flash("Ce compte est désactivé.", "erreur")
        else:
            login_user(UtilisateurConnecte(utilisateur))
            return redirect(url_for("accueil.index"))

    return render_template("auth/connexion.html", formulaire=formulaire)


@bp.route("/deconnexion")
@login_required
def deconnexion():
    logout_user()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("auth.connexion"))
