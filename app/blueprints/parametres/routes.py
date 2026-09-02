from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required
from psycopg.errors import UniqueViolation

from app.blueprints.parametres.forms import (
    NouveauBarreauForm,
    NouveauModeleEcheanceForm,
    NouvelleCategorieEcheanceForm,
    NouvelleMatiereForm,
)
from app.repositories import categories_echeance
from app.repositories import echeances as echeances_repo
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


# --- Modèles d'échéance (réservé avocat / collaborateur) --------------------


def _choix_categories_echeance():
    return [(c.id, c.libelle) for c in categories_echeance.lister()]


@bp.route("/modeles-echeance")
@login_required
@role_requis("avocat", "collaborateur")
def liste_modeles_echeance():
    formulaire = NouveauModeleEcheanceForm()
    formulaire.matiere_id.choices = [
        (m.id, m.libelle) for m in matieres.lister(actives_seulement=False)
    ]
    formulaire.categorie_id.choices = _choix_categories_echeance()
    return render_template(
        "parametres/modeles_echeance.html",
        modeles=echeances_repo.lister_tous_modeles(),
        categorie_libelles={c.id: c.libelle for c in categories_echeance.lister(actives_seulement=False)},
        formulaire=formulaire,
    )


@bp.route("/modeles-echeance", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def creer_modele_echeance():
    formulaire = NouveauModeleEcheanceForm()
    formulaire.matiere_id.choices = [
        (m.id, m.libelle) for m in matieres.lister(actives_seulement=False)
    ]
    formulaire.categorie_id.choices = _choix_categories_echeance()
    if formulaire.validate_on_submit():
        echeances_repo.creer_modele(
            matiere_id=int(formulaire.matiere_id.data),
            libelle=formulaire.libelle.data,
            categorie_id=int(formulaire.categorie_id.data),
            delai_jours=formulaire.delai_jours.data,
        )
        flash("Modèle d'échéance ajouté.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("parametres.liste_modeles_echeance"))


@bp.route("/modeles-echeance/<int:modele_id>/basculer", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def basculer_modele_echeance(modele_id):
    echeances_repo.basculer_actif_modele(modele_id)
    return redirect(url_for("parametres.liste_modeles_echeance"))


# --- Catégories d'échéance (réservé avocat / collaborateur) -----------------


@bp.route("/categories-echeance")
@login_required
@role_requis("avocat", "collaborateur")
def liste_categories_echeance():
    return render_template(
        "parametres/categories_echeance.html",
        categories=categories_echeance.lister(actives_seulement=False),
        formulaire=NouvelleCategorieEcheanceForm(),
    )


@bp.route("/categories-echeance", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def creer_categorie_echeance():
    formulaire = NouvelleCategorieEcheanceForm()
    if formulaire.validate_on_submit():
        try:
            categories_echeance.creer(formulaire.libelle.data)
            flash("Catégorie ajoutée.", "succes")
        except UniqueViolation:
            flash("Cette catégorie existe déjà.", "erreur")
    return redirect(url_for("parametres.liste_categories_echeance"))


@bp.route("/categories-echeance/<int:categorie_id>/basculer", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def basculer_categorie_echeance(categorie_id):
    categories_echeance.basculer_actif(categorie_id)
    return redirect(url_for("parametres.liste_categories_echeance"))
