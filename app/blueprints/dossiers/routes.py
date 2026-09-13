from datetime import date, datetime, time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from psycopg.errors import UniqueViolation

from app.blueprints.dossiers.forms import (
    AjouterIntervenantForm,
    AjouterRoleForm,
    AnnulerEvenementForm,
    DeplacerEvenementForm,
    EcheanceForm,
    EvenementForm,
    ModifierDossierForm,
    NouveauDossierForm,
    OuvrirDossierForm,
)
from app.repositories import categories_echeance, categories_matiere
from app.repositories import documents as documents_repo
from app.repositories import echeances as echeances_repo
from app.repositories import evenements as evenements_repo
from app.repositories import dossiers, matieres, reference, types_evenement, utilisateurs
from app.repositories.roles import RegleRoleViolee, attribuer_role, retirer_role
from app.securite import role_requis
from app.services import modeles_documents

bp = Blueprint("dossiers", __name__, url_prefix="/dossiers")


def _choix_avec_vide(items, cle, libelle):
    return [("", "—")] + [(getattr(i, cle), getattr(i, libelle)) for i in items]


def _matieres_groupees():
    """Regroupe les matières actives par catégorie pour l'affichage en
    <optgroup> du menu "Matière" (voir dossiers/fiche.html) — les matières
    sans catégorie ("non classées") forment un groupe à part, en dernier."""
    par_categorie_id = {}
    for m in matieres.lister():
        par_categorie_id.setdefault(m.categorie_id, []).append(m)
    groupes = [
        (c.libelle, par_categorie_id[c.id])
        for c in categories_matiere.lister()
        if c.id in par_categorie_id
    ]
    if None in par_categorie_id:
        groupes.append(("Non classée", par_categorie_id[None]))
    return groupes


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


ROLES_NOTRE_PARTIE = {"client"}
ROLES_PARTIE_ADVERSE = {"adversaire"}
ROLES_AVOCAT_OU_LIE = {"avocat", "enfant"}
# demandeur/défendeur sont des positions procédurales, indépendantes de la
# qualité de client ou d'adversaire (le cabinet peut représenter l'un ou
# l'autre) : elles ne déterminent donc pas de camp, contrairement à
# client/adversaire ci-dessus. Un contact qui ne porte que ce rôle atterrit
# dans "autres" (voir _repartir_par_camp).


def _classe_role(libelle: str) -> str:
    """Classe CSS du badge de rôle affiché sur la fiche dossier — purement
    cosmétique (voir role-badge dans style.css), donc un rôle non reconnu
    (type_role étant un vocabulaire ouvert, voir migrations/0004) obtient
    simplement un badge neutre plutôt qu'une erreur."""
    if libelle in ROLES_NOTRE_PARTIE:
        return "client"
    if libelle in ROLES_PARTIE_ADVERSE:
        return "adverse"
    if libelle in ROLES_AVOCAT_OU_LIE:
        return "avocat"
    return ""


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
        i["role_classe"] = _classe_role(i["role_libelle"])
        if contact_id not in groupes:
            groupes[contact_id] = {
                "contact_id": contact_id,
                "nom_contact": i["nom_contact"],
                "roles": [],
            }
            ordre.append(contact_id)
        groupes[contact_id]["roles"].append(i)
    return sorted((groupes[cid] for cid in ordre), key=lambda g: g["nom_contact"])


def _repartir_par_camp(groupes):
    """Répartit les intervenants (déjà groupés par contact, voir
    _grouper_intervenants) en deux camps pour l'affichage de la fiche
    dossier : notre partie et la partie adverse. Un contact qui porte
    directement le rôle client fixe son camp à notre partie, adversaire à
    la partie adverse ; un rôle lié à un autre contact du dossier (avocat,
    enfant) hérite du camp de ce contact — potentiellement en chaîne. Un
    intervenant dont le camp ne se déduit pas ainsi (rôle procédural comme
    demandeur/défendeur sans lien, contact non lié, ou lié à un contact
    lui-même non classé) atterrit dans "autres" plutôt que d'être forcé
    dans l'un des deux camps : demandeur/défendeur sont des positions
    procédurales indépendantes de la qualité de client ou d'adversaire
    (le cabinet peut représenter l'un ou l'autre), et type_role est de
    toute façon un vocabulaire ouvert (voir migrations/0004) — de nouveaux
    rôles comme "témoin" ou "notaire" n'ont pas vocation à choisir un
    camp."""
    camps = {}
    for groupe in groupes:
        libelles = {r["role_libelle"] for r in groupe["roles"]}
        if libelles & ROLES_NOTRE_PARTIE:
            camps[groupe["contact_id"]] = "notre_partie"
        elif libelles & ROLES_PARTIE_ADVERSE:
            camps[groupe["contact_id"]] = "partie_adverse"

    changement = True
    while changement:
        changement = False
        for groupe in groupes:
            if groupe["contact_id"] in camps:
                continue
            for role in groupe["roles"]:
                camp_lie = camps.get(role["contact_lie_id"])
                if camp_lie:
                    camps[groupe["contact_id"]] = camp_lie
                    changement = True
                    break

    # Rattache les rôles purement "attachés" (avocat, enfant — voir
    # ROLES_AVOCAT_OU_LIE) à leur contact lié plutôt que de les afficher
    # comme des intervenants indépendants : un avocat n'a de sens
    # visuellement que rattaché à la partie qu'il représente (voir
    # fiche.html::colonne_partie, qui les affiche en sous-ligne atténuée).
    # Seul un contact dont TOUS les rôles sont de ce type, liés à UN SEUL
    # autre intervenant lui-même non "attaché", est rattaché ; les autres
    # cas (rôle mixte, contact lié absent, multiple, ou chaîné) restent
    # affichés au premier niveau — mieux vaut un intervenant mal groupé
    # qu'un intervenant invisible.
    par_id = {g["contact_id"]: g for g in groupes}
    for groupe in groupes:
        groupe["sous_lignes"] = []

    rattaches = set()
    for groupe in groupes:
        libelles = {r["role_libelle"] for r in groupe["roles"]}
        contacts_lies = {r["contact_lie_id"] for r in groupe["roles"]}
        if not libelles <= ROLES_AVOCAT_OU_LIE or len(contacts_lies) != 1:
            continue
        (contact_lie_id,) = contacts_lies
        parent = par_id.get(contact_lie_id)
        if parent is None or parent["contact_id"] == groupe["contact_id"]:
            continue
        libelles_parent = {r["role_libelle"] for r in parent["roles"]}
        if libelles_parent <= ROLES_AVOCAT_OU_LIE:
            continue
        parent["sous_lignes"].append(groupe)
        rattaches.add(groupe["contact_id"])

    resultat = {"notre_partie": [], "partie_adverse": [], "autres": []}
    for groupe in groupes:
        if groupe["contact_id"] in rattaches:
            continue
        resultat[camps.get(groupe["contact_id"], "autres")].append(groupe)
    return resultat


def _choix_contacts_lies(intervenants):
    """Choix de contact_lie_id pour les formulaires de rôle (Ajouter un
    intervenant / Ajouter un rôle) : un contact ne doit apparaître qu'une
    fois même s'il porte déjà plusieurs rôles sur ce dossier (ex: à la
    fois demandeur et adversaire) — voir _grouper_intervenants, qui
    dédoublonne de la même façon pour l'affichage."""
    vus = set()
    choix = [("", "—")]
    for i in intervenants:
        if i["contact_id"] in vus:
            continue
        vus.add(i["contact_id"])
        choix.append((str(i["contact_id"]), i["nom_contact"]))
    return choix


def _onglet_actif():
    """Les onglets de la fiche dossier sont de simples boutons radio
    stylés en CSS (voir .onglets-dossier dans style.css) : naviguer vers
    une ancre #ajouter-echeance/#ajouter-evenement ne coche pas le radio
    correspondant tout seul. Les liens qui rechargent la fiche pour
    préremplir un formulaire (raccourci "créer une échéance" depuis un
    document, "Clôturer avec compte-rendu", filtre des événements annulés)
    passent donc un paramètre de requête qu'on retraduit ici en onglet à
    afficher par défaut, plutôt que de toujours retomber sur Intervenants."""
    if request.args.get("onglet") == "evenements" or request.args.get("evenement_echeance_id"):
        return "evenements"
    if request.args.get("echeance_libelle") or request.args.get("echeance_document_id"):
        return "echeances"
    return "intervenants"


def _choix_dossiers_deplacement(dossier_id_actuel):
    """Choix de nouveau_dossier_id pour DeplacerEvenementForm : les
    dossiers ouverts autres que le dossier d'origine, référence et nom
    calculé à l'appui pour les distinguer."""
    return [
        (str(d.id), f"{d.reference} — {dossiers.nom_calcule(d.id)}")
        for d in dossiers.lister_ouverts()
        if d.id != dossier_id_actuel
    ]


def _preparer_formulaire_role(intervenants):
    """Formulaire minimal pour ajouter un rôle de plus à un contact déjà
    intervenant sur ce dossier : pas de recherche de contact (il est déjà
    connu, voir dossiers.ajouter_role), donc pas de champ contact_id — ce
    qui évite aussi tout risque de collision d'id avec le champ caché
    contact_id du formulaire de recherche principal (voir historique)."""
    formulaire = AjouterRoleForm()
    formulaire.type_role_id.choices = [(t.id, t.libelle) for t in reference.lister_types_role()]
    formulaire.contact_lie_id.choices = _choix_contacts_lies(intervenants)
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
    formulaire_intervenant.contact_lie_id.choices = _choix_contacts_lies(intervenants)

    intervenants_groupes = _grouper_intervenants(intervenants)
    intervenants_par_camp = _repartir_par_camp(intervenants_groupes)
    formulaire_role = _preparer_formulaire_role(intervenants)

    categorie_choix = [(c.id, c.libelle) for c in categories_echeance.lister()]

    echeances = echeances_repo.lister_pour_dossier(dossier_id)
    # Préremplissage depuis le lien "créer une échéance" d'un document (compte
    # rendu de synchronisation IMAP, fiche e-mail) — voir app/blueprints/messagerie.
    formulaire_echeance = EcheanceForm(
        libelle=request.args.get("echeance_libelle"),
        document_id=request.args.get("echeance_document_id"),
    )
    formulaire_echeance.categorie_id.choices = categorie_choix
    formulaires_echeances = {}
    for e in echeances:
        formulaire_modif_echeance = EcheanceForm(
            categorie_id=e.categorie_id,
            libelle=e.libelle,
            date_echeance=e.date_echeance,
            heure_echeance=e.heure_echeance,
            notes=e.notes,
        )
        formulaire_modif_echeance.categorie_id.choices = categorie_choix
        formulaires_echeances[e.id] = formulaire_modif_echeance

    type_evenement_choix = [(t.id, t.libelle) for t in types_evenement.lister()]
    afficher_evenements_annules = request.args.get("afficher_evenements_annules") == "1"
    evenements = evenements_repo.lister_pour_dossier(
        dossier_id, inclure_annules=afficher_evenements_annules
    )
    # Préremplissage depuis le lien "Clôturer avec compte-rendu" d'une
    # échéance — voir echeance_id ci-dessous et le bouton correspondant sur
    # panneau-echeances.
    evenement_echeance_id = request.args.get("evenement_echeance_id")
    formulaire_evenement = EvenementForm(
        echeance_id=evenement_echeance_id,
        date_evenement=date.today() if evenement_echeance_id else None,
    )
    formulaire_evenement.type_evenement_id.choices = type_evenement_choix
    formulaires_evenements = {}
    formulaires_annulation_evenement = {}
    formulaires_deplacement_evenement = {}
    dossiers_choix_deplacement = _choix_dossiers_deplacement(dossier_id)
    for ev in evenements:
        formulaire_modif_evenement = EvenementForm(
            type_evenement_id=ev.type_evenement_id,
            date_evenement=ev.date_evenement,
            duree_minutes=ev.duree_minutes,
            contenu=ev.contenu,
        )
        formulaire_modif_evenement.type_evenement_id.choices = type_evenement_choix
        formulaires_evenements[ev.id] = formulaire_modif_evenement
        formulaires_annulation_evenement[ev.id] = AnnulerEvenementForm()
        formulaire_deplacement = DeplacerEvenementForm()
        formulaire_deplacement.nouveau_dossier_id.choices = dossiers_choix_deplacement
        formulaires_deplacement_evenement[ev.id] = formulaire_deplacement

    return render_template(
        "dossiers/fiche.html",
        dossier=dossier,
        nom=nom,
        intervenants_groupes=intervenants_groupes,
        intervenants_par_camp=intervenants_par_camp,
        formulaire_ouvrir=formulaire_ouvrir,
        formulaire_modif=formulaire_modif,
        formulaire_intervenant=formulaire_intervenant,
        formulaire_role=formulaire_role,
        documents=documents_repo.lister_pour_dossier(dossier_id),
        modeles_documents=modeles_documents.lister(),
        echeances=echeances,
        formulaire_echeance=formulaire_echeance,
        formulaires_echeances=formulaires_echeances,
        categorie_libelles={c.id: c.libelle for c in categories_echeance.lister(actives_seulement=False)},
        utilisateur_noms={u.id: u.nom for u in utilisateurs.lister()},
        aujourd_hui=date.today(),
        matieres_groupees=_matieres_groupees(),
        evenements=evenements,
        formulaire_evenement=formulaire_evenement,
        formulaires_evenements=formulaires_evenements,
        formulaires_annulation_evenement=formulaires_annulation_evenement,
        formulaires_deplacement_evenement=formulaires_deplacement_evenement,
        afficher_evenements_annules=afficher_evenements_annules,
        type_evenement_libelles={t.id: t.libelle for t in types_evenement.lister(actives_seulement=False)},
        onglet_actif=_onglet_actif(),
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
    formulaire.contact_lie_id.choices = _choix_contacts_lies(intervenants)

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
    formulaire.contact_lie_id.choices = _choix_contacts_lies(intervenants)

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


# --- Échéances ---------------------------------------------------------------


@bp.route("/<int:dossier_id>/echeances", methods=["POST"])
@login_required
def ajouter_echeance(dossier_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = EcheanceForm()
    formulaire.categorie_id.choices = [(c.id, c.libelle) for c in categories_echeance.lister()]
    if formulaire.validate_on_submit():
        echeances_repo.creer(
            dossier_id=dossier_id,
            categorie_id=int(formulaire.categorie_id.data),
            libelle=formulaire.libelle.data,
            date_echeance=formulaire.date_echeance.data,
            heure_echeance=formulaire.heure_echeance.data,
            notes=formulaire.notes.data or None,
            utilisateur_id=current_user.id,
            document_id=int(formulaire.document_id.data) if formulaire.document_id.data else None,
        )
        flash("Échéance ajoutée.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/echeances/<int:echeance_id>/modifier", methods=["POST"])
@login_required
def modifier_echeance(dossier_id, echeance_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = EcheanceForm()
    formulaire.categorie_id.choices = [(c.id, c.libelle) for c in categories_echeance.lister()]
    if formulaire.validate_on_submit():
        echeances_repo.modifier(
            echeance_id=echeance_id,
            categorie_id=int(formulaire.categorie_id.data),
            libelle=formulaire.libelle.data,
            date_echeance=formulaire.date_echeance.data,
            heure_echeance=formulaire.heure_echeance.data,
            notes=formulaire.notes.data or None,
            utilisateur_id=current_user.id,
        )
        flash("Échéance mise à jour.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/echeances/<int:echeance_id>/fait", methods=["POST"])
@login_required
def marquer_echeance_fait(dossier_id, echeance_id):
    echeances_repo.marquer_fait(echeance_id, current_user.id)
    flash("Échéance marquée comme faite.", "succes")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/echeances/<int:echeance_id>/a-faire", methods=["POST"])
@login_required
def marquer_echeance_a_faire(dossier_id, echeance_id):
    echeances_repo.marquer_a_faire(echeance_id, current_user.id)
    flash("Échéance remise à faire.", "succes")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


@bp.route("/<int:dossier_id>/echeances/<int:echeance_id>/supprimer", methods=["POST"])
@login_required
def supprimer_echeance(dossier_id, echeance_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    echeances_repo.supprimer(echeance_id)
    flash("Échéance supprimée.", "succes")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))


# --- Événements ---------------------------------------------------------------


@bp.route("/<int:dossier_id>/evenements", methods=["POST"])
@login_required
def ajouter_evenement(dossier_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = EvenementForm()
    formulaire.type_evenement_id.choices = [(t.id, t.libelle) for t in types_evenement.lister()]
    if formulaire.validate_on_submit():
        echeance_id = int(formulaire.echeance_id.data) if formulaire.echeance_id.data else None
        evenements_repo.creer(
            dossier_id=dossier_id,
            type_evenement_id=int(formulaire.type_evenement_id.data),
            date_evenement=formulaire.date_evenement.data,
            duree_minutes=formulaire.duree_minutes.data,
            contenu=formulaire.contenu.data,
            utilisateur_id=current_user.id,
            echeance_id=echeance_id,
        )
        # Raccourci "Clôturer avec compte-rendu" : la création de
        # l'événement vaut clôture de l'échéance qui l'a fait naître.
        if echeance_id is not None:
            echeances_repo.marquer_fait(echeance_id, current_user.id)
        flash("Événement ajouté.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id, onglet="evenements"))


@bp.route("/<int:dossier_id>/evenements/<int:evenement_id>/modifier", methods=["POST"])
@login_required
def modifier_evenement(dossier_id, evenement_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = EvenementForm()
    formulaire.type_evenement_id.choices = [(t.id, t.libelle) for t in types_evenement.lister()]
    if formulaire.validate_on_submit():
        evenements_repo.modifier(
            evenement_id=evenement_id,
            type_evenement_id=int(formulaire.type_evenement_id.data),
            date_evenement=formulaire.date_evenement.data,
            duree_minutes=formulaire.duree_minutes.data,
            contenu=formulaire.contenu.data,
            utilisateur_id=current_user.id,
        )
        flash("Événement mis à jour.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id, onglet="evenements"))


@bp.route("/<int:dossier_id>/evenements/<int:evenement_id>/deplacer", methods=["POST"])
@login_required
@role_requis("avocat", "collaborateur")
def deplacer_evenement(dossier_id, evenement_id):
    """Changement de dossier de rattachement, réservé avocat/collaborateur
    (voir DeplacerEvenementForm) : une portée différente d'une simple
    correction de contenu."""
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = DeplacerEvenementForm()
    formulaire.nouveau_dossier_id.choices = _choix_dossiers_deplacement(dossier_id)
    if formulaire.validate_on_submit():
        evenements_repo.changer_dossier(
            evenement_id=evenement_id,
            nouveau_dossier_id=int(formulaire.nouveau_dossier_id.data),
            utilisateur_id=current_user.id,
        )
        flash("Événement déplacé vers l'autre dossier.", "succes")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id, onglet="evenements"))
    flash("Choisissez un dossier de destination valide.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id, onglet="evenements"))


@bp.route("/<int:dossier_id>/evenements/<int:evenement_id>/annuler", methods=["POST"])
@login_required
def annuler_evenement(dossier_id, evenement_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    formulaire = AnnulerEvenementForm()
    if formulaire.validate_on_submit():
        evenements_repo.annuler(
            evenement_id, current_user.id, motif=formulaire.motif_annulation.data or None
        )
        flash("Événement annulé.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id, onglet="evenements"))


@bp.route("/<int:dossier_id>/evenements/<int:evenement_id>/reactiver", methods=["POST"])
@login_required
def reactiver_evenement(dossier_id, evenement_id):
    blocage = _bloquer_si_clos(dossier_id)
    if blocage:
        return blocage
    evenements_repo.reactiver(evenement_id, current_user.id)
    flash("Événement réactivé.", "succes")
    return redirect(url_for("dossiers.fiche", dossier_id=dossier_id, onglet="evenements"))


@bp.route("/<int:dossier_id>/evenements/<int:evenement_id>/historique")
@login_required
def historique_evenement(dossier_id, evenement_id):
    dossier = dossiers.recuperer(dossier_id)
    if dossier is None:
        flash("Ce dossier n'existe pas.", "erreur")
        return redirect(url_for("dossiers.liste"))
    evenement = evenements_repo.recuperer(evenement_id)
    return render_template(
        "dossiers/evenement_historique.html",
        dossier=dossier,
        nom=dossiers.nom_calcule(dossier_id),
        evenement=evenement,
        historique=evenements_repo.lister_historique(evenement_id),
        type_evenement_libelles={t.id: t.libelle for t in types_evenement.lister(actives_seulement=False)},
        utilisateur_noms={u.id: u.nom for u in utilisateurs.lister()},
    )


# --- Chronologie --------------------------------------------------------------


@bp.route("/<int:dossier_id>/chronologie")
@login_required
def chronologie(dossier_id):
    """Fusionne en mémoire les événements (date = date_evenement, annulés
    exclus) et les documents (date = date_tri) d'un dossier, triés
    ensemble par date décroissante — pas de nouvelle table, pur Python."""
    dossier = dossiers.recuperer(dossier_id)
    if dossier is None:
        flash("Ce dossier n'existe pas.", "erreur")
        return redirect(url_for("dossiers.liste"))

    lignes = []
    for ev in evenements_repo.lister_pour_dossier(dossier_id):
        lignes.append({
            "type": "evenement",
            "date": datetime.combine(ev.date_evenement, time.min),
            "objet": ev,
        })
    for document in documents_repo.lister_pour_dossier(dossier_id):
        lignes.append({"type": "document", "date": document.date_tri, "objet": document})
    lignes.sort(key=lambda l: l["date"], reverse=True)

    return render_template(
        "dossiers/chronologie.html",
        dossier=dossier,
        nom=dossiers.nom_calcule(dossier_id),
        lignes=lignes,
        type_evenement_libelles={t.id: t.libelle for t in types_evenement.lister(actives_seulement=False)},
        libelles_origine_document={"genere": "Généré", "email": "E-mail", "depose": "Déposé"},
    )
