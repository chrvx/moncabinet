from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required
from psycopg.errors import UniqueViolation

from app.blueprints.parametres.forms import NouveauBarreauForm, NouvelleMatiereForm
from app.repositories import matieres, reference
from app.securite import role_requis

bp = Blueprint("parametres", __name__, url_prefix="/parametres")


# --- Administration des barreaux (réservé avocat / collaborateur) ----------


@bp.route("/barreaux")
@login_required
@role_requis("avocat", "collaborateur")
def liste_barreaux():
    return render_template(
        "parametres/barreaux.html",
        barreaux=reference.lister_barreaux(actifs_seulement=False),
        formulaire=NouveauBarreauForm(),
    )


@bp.route("/barreaux", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def creer_barreau():
    formulaire = NouveauBarreauForm()
    if formulaire.validate_on_submit():
        try:
            reference.creer_barreau(formulaire.libelle.data)
            flash("Barreau ajouté.", "succes")
        except UniqueViolation:
            flash("Ce barreau existe déjà.", "erreur")
    return redirect(url_for("parametres.liste_barreaux"))


@bp.route("/barreaux/<int:barreau_id>/basculer", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def basculer_barreau(barreau_id):
    reference.basculer_actif_barreau(barreau_id)
    return redirect(url_for("parametres.liste_barreaux"))


# --- Matières (réservé avocat / collaborateur) ------------------------------


@bp.route("/matieres")
@login_required
@role_requis("avocat", "collaborateur")
def liste_matieres():
    formulaire = NouvelleMatiereForm()
    return render_template(
        "parametres/matieres.html",
        matieres=matieres.lister(actives_seulement=False),
        formulaire=formulaire,
    )


@bp.route("/matieres", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def creer_matiere():
    formulaire = NouvelleMatiereForm()
    if formulaire.validate_on_submit():
        try:
            matieres.creer(formulaire.libelle.data)
            flash("Matière ajoutée.", "succes")
        except UniqueViolation:
            flash("Cette matière existe déjà.", "erreur")
    return redirect(url_for("parametres.liste_matieres"))


@bp.route("/matieres/<int:matiere_id>/basculer", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def basculer_matiere(matiere_id):
    matieres.basculer_actif(matiere_id)
    return redirect(url_for("parametres.liste_matieres"))
