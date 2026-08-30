from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from psycopg.errors import UniqueViolation

from app.blueprints.dossiers.forms import (
    AjouterIntervenantForm,
    AjouterRoleForm,
    ModifierDossierForm,
    NouveauDossierForm,
    NouvelleMatiereForm,
    OuvrirDossierForm,
)
from app.repositories import documents as documents_repo
from app.repositories import dossiers, matieres, reference
from app.repositories.roles import RegleRoleViolee, attribuer_role, retirer_role
from app.securite import role_requis
from app.services import modeles_documents

bp = Blueprint("dossiers", __name__, url_prefix="/dossiers")


def _choix_avec_vide(items, cle, libelle):
    return [("", "—")] + [(getattr(i, cle), getattr(i, libelle)) for i in items]


def _bloquer_si_clos(dossier_id):
    """Un dossier clos n'accepte plus aucune action, à part sa réouverture
    (voir dossiers.rouvrir) : renvoie une redirection avec message d'erreur
    si c'est le cas, sinon None. Vérifié côté serveur en plus de l'affichage
    conditionnel du template, qui masque déjà ces actions à l'écran mais ne
    protège pas contre un POST forgé directement."""
    dossier = dossiers.recuperer(dossier_id)
    if dossier is not None and dossier.statut == "clos":
        flash("Ce dossier est clos : rouvrez-le avant d'agir dessus.", "erreur")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))
    return None


def _grouper_intervenants(intervenants):
    """Regroupe les lignes role_contact par contact : un même contact peut
    porter plusieurs rôles sur un même dossier (ex: client ET demandeur)
    sans qu'il faille le rajouter en double — voir _preparer_formulaire_role
    pour le formulaire qui permet d'ajouter un rôle de plus à un contact
    déjà présent."""
    groupes = {}
    ordre = []
    for i in intervenants:
        contact_id = i["contact_id"]
        if contact_id not in groupes:
            groupes[contact_id] = {
                "contact_id": contact_id,
                "nom_contact": i["nom_contact"],
                "roles": [],
            }
            ordre.append(contact_id)
        groupes[contact_id]["roles"].append(i)
    return sorted((groupes[cid] for cid in ordre), key=lambda g: g["nom_contact"])


def _preparer_formulaire_role(intervenants):
    """Formulaire minimal pour ajouter un rôle de plus à un contact déjà
    intervenant sur ce dossier : pas de recherche de contact (il est déjà
    connu, voir dossiers.ajouter_role), donc pas de champ contact_id — ce
    qui évite aussi tout risque de collision d'id avec le champ caché
    contact_id du formulaire de recherche principal (voir historique)."""
    formulaire = AjouterRoleForm()
    formulaire.type_role_id.choices = [(t.id, t.libelle) for t in reference.lister_types_role()]
    formulaire.contact_lie_id.choices = [("", "—")] + [
        (str(i["contact_id"]), i["nom_contact"]) for i in intervenants
    ]
    return formulaire


# --- Création ---------------------------------------------------------------


@bp.route("/nouveau", methods=["POST"])
@login_required
def nouveau():
    formulaire = NouveauDossierForm()
    if formulaire.validate_on_submit():
        dossier = dossiers.creer_brouillon(
            contact_id=int(formulaire.contact_id.data),
            utilisateur_id=current_user.id,
        )
        flash("Dossier créé en brouillon.", "succes")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier.id))
    flash("Impossible de créer le dossier.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=formulaire.contact_id.data))


# --- Liste ----------------------------------------------------------------


def _libelles_categorie():
    """Libellés humains ("Juridique (conseil)"...) des valeurs de
    categorie, dérivés des choix du formulaire de modification pour ne pas
    dupliquer cette correspondance ailleurs."""
    return dict(ModifierDossierForm().categorie.choices)


def _libelles_matiere():
    """Toutes les matières, actives ou non : un dossier ancien peut
    référencer une matière depuis désactivée, qu'il faut quand même savoir
    afficher."""
    return {m.id: m.libelle for m in matieres.lister(actives_seulement=False)}


@bp.route("/")
@login_required
def liste():
    resultats = dossiers.lister_ouverts()
    dossiers_avec_nom = [(d, dossiers.nom_calcule(d.id)) for d in resultats]
    return render_template(
        "dossiers/liste.html",
        dossiers=dossiers_avec_nom,
        categorie_libelles=_libelles_categorie(),
        matiere_libelles=_libelles_matiere(),
    )


@bp.route("/clos")
@login_required
def liste_clos():
    resultats = dossiers.lister_clos()
    dossiers_avec_nom = [(d, dossiers.nom_calcule(d.id)) for d in resultats]
    return render_template(
        "dossiers/liste_clos.html",
        dossiers=dossiers_avec_nom,
        categorie_libelles=_libelles_categorie(),
        matiere_libelles=_libelles_matiere(),
    )


@bp.route("/brouillons")
@login_required
def liste_brouillons():
    resultats = dossiers.lister_brouillons()
    dossiers_avec_nom = [(d, dossiers.nom_calcule(d.id)) for d in resultats]
    return render_template("dossiers/liste_brouillons.html", dossiers=dossiers_avec_nom)


# --- Fiche ------------------------------------------------------------------


@bp.route("/<int:dossier_id>")
@login_required
def fiche(dossier_id):
    dossier = dossiers.recuperer(dossier_id)
    if dossier is None:
        flash("Ce dossier n'existe pas.", "erreur")
        return redirect(url_for("dossiers.liste"))

    nom = dossiers.nom_calcule(dossier_id)
    intervenants = dossiers.lister_intervenants(dossier_id)

    formulaire_ouvrir = OuvrirDossierForm(reference=dossiers.proposer_reference())

    formulaire_modif = ModifierDossierForm(obj=dossier)
    formulaire_modif.matiere_id.choices = _choix_avec_vide(
        matieres.lister(), "id", "libelle"
    )
    if request.method == "GET":
        formulaire_modif.categorie.data = dossier.categorie or ""
        formulaire_modif.matiere_id.data = str(dossier.matiere_id) if dossier.matiere_id else ""

    formulaire_intervenant = AjouterIntervenantForm()
    formulaire_intervenant.type_role_id.choices = [
        (t.id, t.libelle) for t in reference.lister_types_role()
    ]
    # contact_lie ne propose que les contacts déjà présents sur ce dossier :
    # "l'avocat de l'adversaire" ou "l'enfant de tel client" n'ont de sens
    # que par rapport à quelqu'un déjà attaché à la même affaire.
    formulaire_intervenant.contact_lie_id.choices = [("", "—")] + [
        (str(i["contact_id"]), i["nom_contact"]) for i in intervenants
    ]

    intervenants_groupes = _grouper_intervenants(intervenants)
    formulaire_role = _preparer_formulaire_role(intervenants)

    return render_template(
        "dossiers/fiche.html",
        dossier=dossier,
        nom=nom,
        intervenants_groupes=intervenants_groupes,
        formulaire_ouvrir=formulaire_ouvrir,
        formulaire_modif=formulaire_modif,
        formulaire_intervenant=formulaire_intervenant,
        formulaire_role=formulaire_role,
        documents=documents_repo.lister_pour_dossier(dossier_id),
        modeles_documents=modeles_documents.lister(),
    )


@bp.route("/<int:dossier_id>/ouvrir", methods=["POST"])
@login_required
def ouvrir(dossier_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = OuvrirDossierForm()
    if formulaire.validate_on_submit():
        try:
            dossiers.ouvrir(dossier_id, formulaire.reference.data, current_user.id)
            flash("Dossier ouvert.", "succes")
        except UniqueViolation:
            flash("Cette référence est déjà utilisée par un autre dossier.", "erreur")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/clore", methods=["POST"])
@login_required
def clore(dossier_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    dossiers.clore(dossier_id, current_user.id)
    flash("Dossier clôturé.", "succes")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/rouvrir", methods=["POST"])
@login_required
def rouvrir(dossier_id):
    dossiers.rouvrir(dossier_id, current_user.id)
    flash("Dossier rouvert.", "succes")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/modifier", methods=["POST"])
@login_required
def modifier(dossier_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = ModifierDossierForm()
    formulaire.matiere_id.choices = _choix_avec_vide(matieres.lister(), "id", "libelle")
    if formulaire.validate_on_submit():
        matiere_id = int(formulaire.matiere_id.data) if formulaire.matiere_id.data else None
        categorie = formulaire.categorie.data or None
        dossiers.modifier(dossier_id, current_user.id, categorie, matiere_id)
        flash("Dossier mis à jour.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/intervenants", methods=["POST"])
@login_required
def ajouter_intervenant(dossier_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = AjouterIntervenantForm()
    formulaire.type_role_id.choices = [(t.id, t.libelle) for t in reference.lister_types_role()]
    intervenants = dossiers.lister_intervenants(dossier_id)
    formulaire.contact_lie_id.choices = [("", "—")] + [
        (str(i["contact_id"]), i["nom_contact"]) for i in intervenants
    ]

    if formulaire.validate_on_submit():
        contact_lie_id = int(formulaire.contact_lie_id.data) if formulaire.contact_lie_id.data else None
        try:
            attribuer_role(
                contact_id=int(formulaire.contact_id.data),
                type_role_id=int(formulaire.type_role_id.data),
                utilisateur_id=current_user.id,
                dossier_id=dossier_id,
                contact_lie_id=contact_lie_id,
            )
            flash("Intervenant ajouté.", "succes")
        except RegleRoleViolee as e:
            flash(str(e), "erreur")
    else:
        flash("Choisissez un contact et un rôle valides.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/intervenants/<int:contact_id>/role", methods=["POST"])
@login_required
def ajouter_role(dossier_id, contact_id):
    """Ajoute un rôle de plus à un contact déjà intervenant sur ce dossier
    (ex: un client qu'on déclare aussi demandeur) sans le rechercher à
    nouveau — voir _preparer_formulaire_role dans fiche()."""
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = AjouterRoleForm()
    formulaire.type_role_id.choices = [(t.id, t.libelle) for t in reference.lister_types_role()]
    intervenants = dossiers.lister_intervenants(dossier_id)
    formulaire.contact_lie_id.choices = [("", "—")] + [
        (str(i["contact_id"]), i["nom_contact"]) for i in intervenants
    ]

    if formulaire.validate_on_submit():
        contact_lie_id = int(formulaire.contact_lie_id.data) if formulaire.contact_lie_id.data else None
        try:
            attribuer_role(
                contact_id=contact_id,
                type_role_id=int(formulaire.type_role_id.data),
                utilisateur_id=current_user.id,
                dossier_id=dossier_id,
                contact_lie_id=contact_lie_id,
            )
            flash("Rôle ajouté.", "succes")
        except RegleRoleViolee as e:
            flash(str(e), "erreur")
    else:
        flash("Choisissez un rôle valide.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/intervenants/<int:role_contact_id>/retirer", methods=["POST"])
@login_required
def retirer_intervenant(dossier_id, role_contact_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    try:
        retirer_role(role_contact_id)
        flash("Intervenant retiré du dossier.", "succes")
    except RegleRoleViolee as e:
        flash(str(e), "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


# --- Matières (réservé avocat / collaborateur) ------------------------------


@bp.route("/matieres")
@login_required
@role_requis("avocat", "collaborateur")
def liste_matieres():
    formulaire = NouvelleMatiereForm()
    return render_template(
        "dossiers/matieres.html",
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
    return redirect(url_for("dossiers.liste_matieres"))


@bp.route("/matieres/<int:matiere_id>/basculer", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def basculer_matiere(matiere_id):
    matieres.basculer_actif(matiere_id)
    return redirect(url_for("dossiers.liste_matieres"))
