from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from psycopg.errors import UniqueViolation

from app.blueprints.contacts.forms import (
    AjouterAdresseForm,
    AjouterEmailForm,
    AjouterTelephoneForm,
    CorrigerAdresseForm,
    CorrigerEmailForm,
    CorrigerTelephoneForm,
    ModifierPersonneMoraleForm,
    ModifierPersonnePhysiqueForm,
    NouvelAvocatAnnuaireForm,
    NouvelOfficeNotarialAnnuaireForm,
    NouvellePersonneMoraleForm,
    NouvellePersonnePhysiqueForm,
    PartagerAdresseForm,
    QualificationAvocatForm,
    QualificationCommissaireJusticeForm,
    QualificationNotaireForm,
)
from app.blueprints.dossiers.forms import NouveauDossierForm
from app.repositories import contacts, coordonnees, dossiers, qualifications, reference
from app.securite import role_requis
from app.services import annuaire_avocats, annuaire_notaires, import_avocats, import_notaires

bp = Blueprint("contacts", __name__, url_prefix="/contacts")

TAILLE_PAGE = 25


def _choix_avec_vide(items, cle, libelle):
    """Construit une liste de choix pour un SelectField optionnel, avec une
    première option vide représentant "non renseigné"."""
    return [("", "—")] + [(getattr(i, cle), getattr(i, libelle)) for i in items]


def _choix_pays_nationalite():
    """Comme _choix_avec_vide, mais France en tête plutôt qu'à sa place
    alphabétique : de loin la nationalité la plus fréquente pour ce cabinet."""
    tous = reference.lister_pays()
    france = next((p for p in tous if p.code_iso == "FR"), None)
    reste = [p for p in tous if p.code_iso != "FR"]
    ordonnes = ([france] if france else []) + reste
    return [("", "—")] + [(p.code_iso, p.libelle) for p in ordonnes]


def _vide_en_none(valeur):
    return valeur if valeur else None


# --- Recherche / liste ----------------------------------------------------


#: Qualités pour lesquelles la page contacts.recherche propose un raccourci
#: filtré (voir _vue_par_qualite et api_tableau) — libellé et message à
#: afficher quand la liste est vide.
QUALITES = {
    "avocat": ("Avocats", "Aucun avocat enregistré pour l'instant."),
    "client": ("Clients", "Aucun client enregistré pour l'instant."),
    "adversaire": ("Adversaires", "Aucun adversaire enregistré pour l'instant."),
}


@bp.route("/")
@login_required
def recherche():
    terme = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    resultats, total = contacts.lister_avec_coordonnees(
        terme=terme, page=page, taille_page=TAILLE_PAGE
    )
    nb_pages = 1 if terme else max(1, -(-total // TAILLE_PAGE))  # arrondi au-dessus

    return render_template(
        "contacts/recherche.html",
        terme=terme,
        resultats=resultats,
        page=page,
        nb_pages=nb_pages,
    )


def _vue_par_qualite(qualite):
    titre, message_vide = QUALITES[qualite]
    resultats, _ = contacts.lister_avec_coordonnees(qualite=qualite)
    return render_template(
        "contacts/liste_par_qualite.html",
        titre=titre,
        qualite=qualite,
        resultats=resultats,
        message_vide=message_vide,
    )


@bp.route("/avocats")
@login_required
def liste_avocats():
    return _vue_par_qualite("avocat")


@bp.route("/clients")
@login_required
def liste_clients():
    return _vue_par_qualite("client")


@bp.route("/adversaires")
@login_required
def liste_adversaires():
    return _vue_par_qualite("adversaire")


@bp.route("/api/tableau")
@login_required
def api_tableau():
    """Endpoint JSON pour le filtrage en direct du tableau au fil de la
    frappe, utilisé par contacts.recherche et ses raccourcis par qualité
    (avocats/clients/adversaires) : voir static/js/filtre_contacts.js.
    Terme vide sans qualité = première page de tous les contacts (même
    contenu que le chargement initial de la page)."""
    terme = request.args.get("q", "").strip()
    qualite = request.args.get("qualite") or None
    if qualite is not None and qualite not in QUALITES:
        return jsonify([]), 400
    resultats, _ = contacts.lister_avec_coordonnees(
        qualite=qualite, terme=terme, page=1, taille_page=TAILLE_PAGE
    )
    return jsonify([
        {
            "contact_id": r.contact_id,
            "type_contact": r.type_contact,
            "nom": r.nom,
            "prenom": r.prenom,
            "telephone": r.telephone,
            "email": r.email,
        }
        for r in resultats
    ])


@bp.route("/api/suggestions")
@login_required
def api_suggestions():
    """Endpoint JSON pour l'autocomplétion au fil de la frappe (recherche
    de contact, et partage d'adresse sur la fiche) : voir
    static/js/recherche_contact.js."""
    terme = request.args.get("q", "").strip()
    if len(terme) < 2:
        return jsonify([])
    resultats = contacts.rechercher_suggestions(terme)
    return jsonify([
        {"contact_id": r.contact_id, "type_contact": r.type_contact, "libelle": r.libelle}
        for r in resultats
    ])


@bp.route("/api/annuaire-avocats")
@login_required
def api_annuaire_avocats():
    """Endpoint JSON de recherche ponctuelle dans l'Annuaire national des
    avocats (data.gouv.fr), pour retrouver un confrère absent de la base
    locale — voir app/services/annuaire_avocats.py. Le CSV national est
    conservé sur disque et seulement retéléchargé quand une nouvelle
    version est publiée (telecharger_csv) : une recherche isolée reste
    donc rapide même après plusieurs semaines sans usage de cette page."""
    nom = request.args.get("nom", "").strip()
    prenom = request.args.get("prenom", "").strip() or None
    if len(nom) < 2:
        return jsonify([])
    avocats = annuaire_avocats.telecharger_csv()
    resultats = annuaire_avocats.rechercher(avocats, nom, prenom)[:20]
    return jsonify([
        {
            "code_cnbf": a.code_cnbf,
            "nom": a.nom,
            "prenom": a.prenom,
            "barreau": a.barreau_libelle,
            "cabinet": a.raison_sociale_cabinet,
            "ville": a.ville,
        }
        for a in resultats
    ])


@bp.route("/api/annuaire-notaires")
@login_required
def api_annuaire_notaires():
    """Endpoint JSON de recherche ponctuelle dans le répertoire local des
    offices notariaux (voir app/services/annuaire_notaires.py) : à la
    différence de l'annuaire des avocats, il n'existe pas d'API filtrable
    ni de dataset national pour les notaires, donc pas de téléchargement ni
    de cache à durée de vie — juste un petit CSV chargé une fois par
    processus."""
    terme = request.args.get("q", "").strip()
    if len(terme) < 2:
        return jsonify([])
    offices = annuaire_notaires.charger_repertoire_avec_cache()
    resultats = annuaire_notaires.rechercher(offices, terme)[:20]
    return jsonify([
        {
            "nom": o.nom,
            "siren": o.siren,
            "numero_voie": o.numero_voie,
            "libelle_voie": o.libelle_voie,
            "code_postal": o.code_postal,
            "commune": o.commune,
        }
        for o in resultats
    ])


# --- Création (formulaire minimal) -----------------------------------------


@bp.route("/nouveau")
@login_required
def nouveau():
    return render_template("contacts/nouveau.html")


@bp.route("/nouveau/avocat-annuaire")
@login_required
def nouveau_avocat_annuaire_recherche():
    """Page de recherche dans l'Annuaire national, pour un confrère non
    rattaché à un barreau déjà importé en masse (voir api_annuaire_avocats
    pour la recherche au fil de la frappe et nouveau_avocat_annuaire pour
    la création une fois un résultat choisi)."""
    return render_template(
        "contacts/nouveau_avocat_annuaire.html", formulaire=NouvelAvocatAnnuaireForm()
    )


@bp.route("/nouveau/avocat-annuaire", methods=["POST"])
@login_required
def nouveau_avocat_annuaire():
    """Crée (ou rapproche, si déjà importé) un contact avocat à partir d'un
    résultat choisi dans l'Annuaire national (voir api_annuaire_avocats et
    static/js/annuaire_avocats.js) — même logique de création que la
    commande CLI d'import en masse, voir
    app/services/import_avocats.py::importer_ou_mettre_a_jour."""
    formulaire = NouvelAvocatAnnuaireForm()
    if not formulaire.validate_on_submit():
        flash("Aucun résultat sélectionné dans l'annuaire.", "erreur")
        return redirect(url_for("contacts.nouveau_avocat_annuaire_recherche"))

    code_cnbf = formulaire.code_cnbf.data.strip()
    avocats = annuaire_avocats.telecharger_csv()
    avocat_annuaire = next((a for a in avocats if a.code_cnbf == code_cnbf), None)
    if avocat_annuaire is None:
        flash(
            "Avocat introuvable dans l'annuaire (le cache a peut-être changé "
            "entre-temps) : relancez la recherche.",
            "erreur",
        )
        return redirect(url_for("contacts.nouveau_avocat_annuaire_recherche"))

    barreau_local = annuaire_avocats.apparier_barreau_local(
        reference.lister_barreaux(actifs_seulement=False), avocat_annuaire.barreau_libelle
    )
    contact_id, statut = import_avocats.importer_ou_mettre_a_jour(
        avocat_annuaire, barreau_local.id if barreau_local else None, current_user.id
    )
    message = (
        "Contact déjà existant, coordonnées resynchronisées"
        if statut == "maj"
        else "Contact créé depuis l'annuaire national"
    )
    flash(f"{message} : {avocat_annuaire.prenom} {avocat_annuaire.nom}", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/nouveau/notaire-annuaire")
@login_required
def nouveau_notaire_annuaire_recherche():
    """Page de recherche dans le répertoire local des offices notariaux
    (voir api_annuaire_notaires pour la recherche au fil de la frappe et
    nouveau_notaire_annuaire pour la création une fois un résultat
    choisi)."""
    return render_template(
        "contacts/nouveau_notaire_annuaire.html",
        formulaire=NouvelOfficeNotarialAnnuaireForm(),
    )


@bp.route("/nouveau/notaire-annuaire", methods=["POST"])
@login_required
def nouveau_notaire_annuaire():
    """Crée (ou rapproche, si déjà importé) un contact office notarial à
    partir d'un résultat choisi dans le répertoire local — voir
    app/services/import_notaires.py::importer_ou_recuperer_office. Contrairement
    à l'avocat, aucune API filtrable n'existe pour retrouver le résultat côté
    serveur : le formulaire transmet directement les champs choisis en
    JavaScript (voir NouvelOfficeNotarialAnnuaireForm)."""
    formulaire = NouvelOfficeNotarialAnnuaireForm()
    if not formulaire.validate_on_submit():
        flash("Aucun résultat sélectionné dans le répertoire.", "erreur")
        return redirect(url_for("contacts.nouveau_notaire_annuaire_recherche"))

    office_annuaire = annuaire_notaires.OfficeAnnuaire(
        nom=formulaire.nom.data.strip(),
        siren=_vide_en_none(formulaire.siren.data),
        numero_voie=_vide_en_none(formulaire.numero_voie.data),
        libelle_voie=_vide_en_none(formulaire.libelle_voie.data),
        code_postal=_vide_en_none(formulaire.code_postal.data),
        commune=_vide_en_none(formulaire.commune.data),
    )
    office, statut = import_notaires.importer_ou_recuperer_office(
        office_annuaire, current_user.id
    )
    message = (
        "Contact déjà existant (rapproché par SIREN)"
        if statut == "rapproche"
        else "Contact créé depuis le répertoire local des notaires"
    )
    flash(f"{message} : {office.raison_sociale}", "succes")
    return redirect(url_for("contacts.fiche", contact_id=office.contact_id))


@bp.route("/nouveau/personne-physique", methods=["GET", "POST"])
@login_required
def nouveau_personne_physique():
    formulaire = NouvellePersonnePhysiqueForm()

    if formulaire.validate_on_submit():
        personne = contacts.creer_personne_physique(
            nom=formulaire.nom.data,
            utilisateur_id=current_user.id,
            prenom=_vide_en_none(formulaire.prenom.data),
        )
        flash(
            f"Contact créé : {personne.prenom or ''} {personne.nom}".strip(),
            "succes",
        )
        return redirect(url_for("contacts.fiche", contact_id=personne.contact_id))

    return render_template(
        "contacts/nouveau_personne_physique.html", formulaire=formulaire
    )


@bp.route("/nouveau/personne-morale", methods=["GET", "POST"])
@login_required
def nouveau_personne_morale():
    formulaire = NouvellePersonneMoraleForm()

    if formulaire.validate_on_submit():
        personne = contacts.creer_personne_morale(
            raison_sociale=formulaire.raison_sociale.data,
            utilisateur_id=current_user.id,
        )
        flash(f"Contact créé : {personne.raison_sociale}", "succes")
        return redirect(url_for("contacts.fiche", contact_id=personne.contact_id))

    return render_template(
        "contacts/nouveau_personne_morale.html", formulaire=formulaire
    )


# --- Fiche contact (affichage + édition progressive) -----------------------


def _preparer_formulaire_physique(personne):
    formulaire = ModifierPersonnePhysiqueForm(obj=personne)
    formulaire.genre.choices = [("", "—"), ("M", "Homme"), ("F", "Femme")]
    formulaire.civilite_id.choices = _choix_avec_vide(
        reference.lister_civilites(), "code", "libelle"
    )
    formulaire.departement_naissance_id.choices = _choix_avec_vide(
        reference.lister_departements(), "code", "libelle"
    )
    formulaire.pays_naissance_id.choices = _choix_avec_vide(
        reference.lister_pays(), "code_iso", "libelle"
    )
    formulaire.nationalite_id.choices = _choix_pays_nationalite()
    if request.method == "GET":
        # obj= pré-remplit les champs simples, mais WTForms a besoin qu'on
        # lui redise explicitement la valeur des SelectField.
        formulaire.civilite_id.data = personne.civilite_id or ""
        formulaire.genre.data = personne.genre or ""
        formulaire.departement_naissance_id.data = personne.departement_naissance_id or ""
        formulaire.pays_naissance_id.data = personne.pays_naissance_id or ""
        formulaire.nationalite_id.data = personne.nationalite_id or ""
    return formulaire


def _preparer_formulaire_correction_adresse(adresse, lien):
    """Formulaire de correction pré-rempli pour une adresse donnée, préfixé
    par l'id du lien pour que chaque adresse active du contact ait son
    propre formulaire indépendant sur la fiche."""
    formulaire = CorrigerAdresseForm(prefix=f"adresse-{lien.id}", obj=adresse)
    formulaire.pays_id.choices = _choix_avec_vide(
        reference.lister_pays(), "code_iso", "libelle"
    )
    formulaire.pays_id.data = adresse.pays_id or ""
    formulaire.mention_distribution_type.data = adresse.mention_distribution_type or ""
    formulaire.mention_destinataire.data = lien.mention_destinataire
    return formulaire


@bp.route("/<int:contact_id>")
@login_required
def fiche(contact_id):
    contact = contacts.recuperer_contact(contact_id)
    if contact is None:
        flash("Ce contact n'existe pas.", "erreur")
        return redirect(url_for("contacts.recherche"))

    profession_actuelle = None
    avocat = notaire = commissaire_justice = None
    cabinet_avocat = None
    formulaire_avocat = formulaire_notaire = formulaire_commissaire_justice = None
    avocats_du_cabinet = []
    if contact.type_contact == "personne_physique":
        personne = contacts.recuperer_personne_physique(contact_id)
        formulaire_modif = _preparer_formulaire_physique(personne)
        titre = f"{personne.prenom or ''} {personne.nom}".strip()

        # Les trois qualifications sont mutuellement exclusives : au plus
        # une seule est active, donc au plus un des trois formulaires
        # ci-dessous est réellement affiché (voir fiche.html).
        profession_actuelle = qualifications.recuperer_profession(contact_id)

        if profession_actuelle in (None, "avocat"):
            avocat = qualifications.recuperer_avocat(contact_id)
            formulaire_avocat = QualificationAvocatForm(
                barreau_id=str(avocat.barreau_id) if avocat and avocat.barreau_id else "",
                cabinet_id=avocat.cabinet_id if avocat else None,
            )
            formulaire_avocat.barreau_id.choices = _choix_avec_vide(
                reference.lister_barreaux(), "id", "libelle"
            )
            if avocat and avocat.cabinet_id:
                cabinet_avocat = contacts.recuperer_personne_morale(avocat.cabinet_id)
                formulaire_avocat.cabinet_recherche.data = (
                    cabinet_avocat.raison_sociale if cabinet_avocat else ""
                )

        if profession_actuelle in (None, "notaire"):
            notaire = qualifications.recuperer_notaire(contact_id)
            formulaire_notaire = QualificationNotaireForm(
                office_id=notaire.office_id if notaire else None
            )
            if notaire and notaire.office_id:
                office = contacts.recuperer_personne_morale(notaire.office_id)
                formulaire_notaire.office_recherche.data = office.raison_sociale if office else ""

        if profession_actuelle in (None, "commissaire_justice"):
            commissaire_justice = qualifications.recuperer_commissaire_justice(contact_id)
            formulaire_commissaire_justice = QualificationCommissaireJusticeForm(
                etude_id=commissaire_justice.etude_id if commissaire_justice else None
            )
            if commissaire_justice and commissaire_justice.etude_id:
                etude = contacts.recuperer_personne_morale(commissaire_justice.etude_id)
                formulaire_commissaire_justice.etude_recherche.data = (
                    etude.raison_sociale if etude else ""
                )
    else:
        personne = contacts.recuperer_personne_morale(contact_id)
        formulaire_modif = ModifierPersonneMoraleForm(obj=personne)
        titre = personne.raison_sociale
        avocats_du_cabinet = qualifications.lister_avocats_par_cabinet(contact_id)

    formulaire_adresse = AjouterAdresseForm()
    formulaire_adresse.pays_id.choices = _choix_avec_vide(
        reference.lister_pays(), "code_iso", "libelle"
    )
    formulaire_telephone = AjouterTelephoneForm()
    formulaire_email = AjouterEmailForm()
    formulaire_partage = PartagerAdresseForm()

    adresses = [
        (
            adresse,
            lien,
            _preparer_formulaire_correction_adresse(adresse, lien),
            coordonnees.lister_autres_contacts_adresse(adresse.id, contact_id),
        )
        for adresse, lien in coordonnees.lister_adresses(contact_id)
    ]
    telephones = [
        (
            telephone,
            lien,
            CorrigerTelephoneForm(prefix=f"telephone-{lien.id}", numero=telephone.numero),
            coordonnees.lister_autres_contacts_telephone(telephone.id, contact_id),
        )
        for telephone, lien in coordonnees.lister_telephones(contact_id)
    ]
    emails = [
        (
            email,
            lien,
            CorrigerEmailForm(prefix=f"email-{lien.id}", adresse_email=email.adresse_email),
            coordonnees.lister_autres_contacts_email(email.id, contact_id),
        )
        for email, lien in coordonnees.lister_emails(contact_id)
    ]
    dossiers_du_contact = dossiers.lister_pour_contact(contact_id)
    formulaire_nouveau_dossier = NouveauDossierForm(contact_id=contact_id)

    # Recherche d'un contact dont on veut réutiliser l'adresse (couple
    # partageant un domicile) : déclenchée par ?partage_terme=... sur cette
    # même page, pour éviter une page séparée.
    partage_terme = request.args.get("partage_terme", "").strip()
    partage_resultats = []
    if partage_terme:
        for r in contacts.rechercher_par_nom(partage_terme):
            if r.contact_id == contact_id:
                continue
            adresses_autre = coordonnees.lister_adresses(r.contact_id)
            if adresses_autre:
                partage_resultats.append((r, adresses_autre))

    est_avocat = profession_actuelle == "avocat"

    return render_template(
        "contacts/fiche.html",
        est_avocat=est_avocat,
        contact=contact,
        personne=personne,
        titre=titre,
        formulaire_modif=formulaire_modif,
        formulaire_adresse=formulaire_adresse,
        formulaire_telephone=formulaire_telephone,
        formulaire_email=formulaire_email,
        formulaire_partage=formulaire_partage,
        adresses=adresses,
        telephones=telephones,
        emails=emails,
        dossiers_du_contact=dossiers_du_contact,
        formulaire_nouveau_dossier=formulaire_nouveau_dossier,
        partage_terme=partage_terme,
        partage_resultats=partage_resultats,
        profession_actuelle=profession_actuelle,
        avocat=avocat,
        cabinet_avocat=cabinet_avocat,
        notaire=notaire,
        commissaire_justice=commissaire_justice,
        avocats_du_cabinet=avocats_du_cabinet,
        formulaire_avocat=formulaire_avocat,
        formulaire_notaire=formulaire_notaire,
        formulaire_commissaire_justice=formulaire_commissaire_justice,
    )


@bp.route("/<int:contact_id>/modifier", methods=["POST"])
@login_required
def modifier(contact_id):
    contact = contacts.recuperer_contact(contact_id)
    if contact is None:
        flash("Ce contact n'existe pas.", "erreur")
        return redirect(url_for("contacts.recherche"))

    if contact.type_contact == "personne_physique":
        formulaire = _preparer_formulaire_physique(
            contacts.recuperer_personne_physique(contact_id)
        )
        if formulaire.validate_on_submit():
            depart = _vide_en_none(formulaire.departement_naissance_id.data)
            pays_naissance = _vide_en_none(formulaire.pays_naissance_id.data)
            if depart and pays_naissance:
                flash(
                    "Le lieu de naissance ne peut pas être à la fois en "
                    "France et à l'étranger : remplissez le département OU "
                    "le pays, pas les deux.",
                    "erreur",
                )
            else:
                try:
                    contacts.modifier_personne_physique(
                        contact_id=contact_id,
                        utilisateur_id=current_user.id,
                        nom=formulaire.nom.data,
                        prenom=_vide_en_none(formulaire.prenom.data),
                        prenoms_secondaires=_vide_en_none(formulaire.prenoms_secondaires.data),
                        nom_usage=_vide_en_none(formulaire.nom_usage.data),
                        genre=_vide_en_none(formulaire.genre.data),
                        civilite_id=_vide_en_none(formulaire.civilite_id.data),
                        date_naissance=formulaire.date_naissance.data,
                        ville_naissance=_vide_en_none(formulaire.ville_naissance.data),
                        departement_naissance_id=depart,
                        pays_naissance_id=pays_naissance,
                        nationalite_id=_vide_en_none(formulaire.nationalite_id.data),
                        profession=_vide_en_none(formulaire.profession.data),
                        siren=_vide_en_none(formulaire.siren.data),
                    )
                    flash("Contact mis à jour.", "succes")
                except UniqueViolation:
                    flash("Ce SIREN est déjà utilisé par un autre contact.", "erreur")
        else:
            flash("Le formulaire contient des erreurs.", "erreur")
    else:
        formulaire = ModifierPersonneMoraleForm()
        if formulaire.validate_on_submit():
            try:
                contacts.modifier_personne_morale(
                    contact_id=contact_id,
                    utilisateur_id=current_user.id,
                    raison_sociale=formulaire.raison_sociale.data,
                    forme=_vide_en_none(formulaire.forme.data),
                    siren=_vide_en_none(formulaire.siren.data),
                )
                flash("Contact mis à jour.", "succes")
            except UniqueViolation:
                flash("Ce SIREN est déjà utilisé par un autre contact.", "erreur")
        else:
            flash("Le formulaire contient des erreurs.", "erreur")

    return redirect(url_for("contacts.fiche", contact_id=contact_id))


# --- Adresses ---------------------------------------------------------------


@bp.route("/<int:contact_id>/adresses", methods=["POST"])
@login_required
def ajouter_adresse(contact_id):
    formulaire = AjouterAdresseForm()
    formulaire.pays_id.choices = _choix_avec_vide(
        reference.lister_pays(), "code_iso", "libelle"
    )
    if formulaire.validate_on_submit():
        latitude = float(formulaire.latitude.data) if formulaire.latitude.data else None
        longitude = float(formulaire.longitude.data) if formulaire.longitude.data else None
        coordonnees.ajouter_adresse(
            contact_id=contact_id,
            utilisateur_id=current_user.id,
            complement=_vide_en_none(formulaire.complement.data),
            entree_batiment=_vide_en_none(formulaire.entree_batiment.data),
            numero_voie=_vide_en_none(formulaire.numero_voie.data),
            libelle_voie=_vide_en_none(formulaire.libelle_voie.data),
            mention_distribution_type=_vide_en_none(formulaire.mention_distribution_type.data),
            mention_distribution_valeur=_vide_en_none(formulaire.mention_distribution_valeur.data),
            code_postal=_vide_en_none(formulaire.code_postal.data),
            code_cedex=_vide_en_none(formulaire.code_cedex.data),
            numero_cedex=_vide_en_none(formulaire.numero_cedex.data),
            commune=_vide_en_none(formulaire.commune.data),
            pays_id=_vide_en_none(formulaire.pays_id.data),
            code_insee_commune=_vide_en_none(formulaire.code_insee_commune.data),
            latitude=latitude,
            longitude=longitude,
            libelle_complet_ban=_vide_en_none(formulaire.libelle_complet_ban.data),
            mention_destinataire=_vide_en_none(formulaire.mention_destinataire.data),
        )
        flash("Adresse ajoutée.", "succes")
    else:
        flash("Le formulaire d'adresse contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/adresses/lier", methods=["POST"])
@login_required
def lier_adresse(contact_id):
    adresse_id = request.form.get("adresse_id", type=int)
    if adresse_id is None:
        flash("Adresse introuvable.", "erreur")
    else:
        coordonnees.lier_adresse_existante(contact_id, adresse_id, current_user.id)
        flash("Adresse liée à ce contact.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/adresses/<int:contact_adresse_id>/terminer", methods=["POST"])
@login_required
def terminer_adresse(contact_id, contact_adresse_id):
    coordonnees.terminer_lien_adresse(contact_adresse_id, current_user.id)
    flash("Adresse clôturée.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/adresses/<int:contact_adresse_id>/corriger", methods=["POST"])
@login_required
def corriger_adresse(contact_id, contact_adresse_id):
    lien = coordonnees.recuperer_contact_adresse(contact_adresse_id)
    if lien is None or lien.contact_id != contact_id:
        flash("Adresse introuvable.", "erreur")
        return redirect(url_for("contacts.fiche", contact_id=contact_id))

    formulaire = CorrigerAdresseForm(prefix=f"adresse-{contact_adresse_id}")
    formulaire.pays_id.choices = _choix_avec_vide(
        reference.lister_pays(), "code_iso", "libelle"
    )
    if formulaire.validate_on_submit():
        autres = coordonnees.lister_autres_contacts_adresse(lien.adresse_id, contact_id)
        latitude = float(formulaire.latitude.data) if formulaire.latitude.data else None
        longitude = float(formulaire.longitude.data) if formulaire.longitude.data else None
        coordonnees.corriger_adresse(
            adresse_id=lien.adresse_id,
            utilisateur_id=current_user.id,
            complement=_vide_en_none(formulaire.complement.data),
            entree_batiment=_vide_en_none(formulaire.entree_batiment.data),
            numero_voie=_vide_en_none(formulaire.numero_voie.data),
            libelle_voie=_vide_en_none(formulaire.libelle_voie.data),
            mention_distribution_type=_vide_en_none(formulaire.mention_distribution_type.data),
            mention_distribution_valeur=_vide_en_none(formulaire.mention_distribution_valeur.data),
            code_postal=_vide_en_none(formulaire.code_postal.data),
            code_cedex=_vide_en_none(formulaire.code_cedex.data),
            numero_cedex=_vide_en_none(formulaire.numero_cedex.data),
            commune=_vide_en_none(formulaire.commune.data),
            pays_id=_vide_en_none(formulaire.pays_id.data),
            code_insee_commune=_vide_en_none(formulaire.code_insee_commune.data),
            latitude=latitude,
            longitude=longitude,
            libelle_complet_ban=_vide_en_none(formulaire.libelle_complet_ban.data),
        )
        coordonnees.modifier_mention_destinataire_adresse(
            contact_adresse_id,
            _vide_en_none(formulaire.mention_destinataire.data),
            current_user.id,
        )
        if autres:
            flash(
                "Adresse corrigée. Cette adresse est partagée avec "
                + ", ".join(autres) + " : la correction s'applique à eux aussi.",
                "info",
            )
        else:
            flash("Adresse corrigée.", "succes")
    else:
        flash("Le formulaire de correction contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


# --- Téléphones -------------------------------------------------------------


@bp.route("/<int:contact_id>/telephones", methods=["POST"])
@login_required
def ajouter_telephone(contact_id):
    formulaire = AjouterTelephoneForm()
    if formulaire.validate_on_submit():
        _, statut = coordonnees.ajouter_telephone(
            contact_id, formulaire.numero.data, current_user.id
        )
        messages = {
            "nouveau": ("Téléphone ajouté.", "succes"),
            "partage": ("Ce numéro existait déjà pour un autre contact : il est désormais partagé avec celui-ci.", "succes"),
            "deja_actif": ("Ce contact a déjà ce numéro actif.", "info"),
        }
        texte, categorie = messages[statut]
        flash(texte, categorie)
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/telephones/<int:contact_telephone_id>/terminer", methods=["POST"])
@login_required
def terminer_telephone(contact_id, contact_telephone_id):
    coordonnees.terminer_lien_telephone(contact_telephone_id, current_user.id)
    flash("Téléphone clôturé.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/telephones/<int:contact_telephone_id>/corriger", methods=["POST"])
@login_required
def corriger_telephone(contact_id, contact_telephone_id):
    lien = coordonnees.recuperer_contact_telephone(contact_telephone_id)
    if lien is None or lien.contact_id != contact_id:
        flash("Téléphone introuvable.", "erreur")
        return redirect(url_for("contacts.fiche", contact_id=contact_id))

    formulaire = CorrigerTelephoneForm(prefix=f"telephone-{contact_telephone_id}")
    if formulaire.validate_on_submit():
        autres = coordonnees.lister_autres_contacts_telephone(lien.telephone_id, contact_id)
        resultat = coordonnees.corriger_telephone(
            lien.telephone_id, formulaire.numero.data, current_user.id
        )
        if resultat != "doublon":
            # Une correction manuelle prime désormais sur l'annuaire
            # national pour ce lien : la resynchronisation ne l'écrasera
            # plus (voir coordonnees.synchroniser_telephone).
            coordonnees.marquer_source_manuelle_telephone(lien.id)
        if resultat == "doublon":
            flash(
                "Ce numéro correspond déjà à un autre téléphone enregistré : "
                "ce serait fusionner deux numéros, pas corriger une faute de "
                "frappe. Clôturez ce téléphone puis ajoutez le bon numéro "
                "pour profiter du partage automatique.",
                "erreur",
            )
        elif autres:
            flash(
                "Téléphone corrigé. Ce numéro est partagé avec "
                + ", ".join(autres) + " : la correction s'applique à eux aussi.",
                "info",
            )
        else:
            flash("Téléphone corrigé.", "succes")
    else:
        flash("Le formulaire de correction contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


# --- Emails -------------------------------------------------------------


@bp.route("/<int:contact_id>/emails", methods=["POST"])
@login_required
def ajouter_email(contact_id):
    formulaire = AjouterEmailForm()
    if formulaire.validate_on_submit():
        _, statut = coordonnees.ajouter_email(
            contact_id, formulaire.adresse_email.data, current_user.id
        )
        messages = {
            "nouveau": ("Email ajouté.", "succes"),
            "partage": ("Cet email existait déjà pour un autre contact : il est désormais partagé avec celui-ci.", "succes"),
            "deja_actif": ("Ce contact a déjà cet email actif.", "info"),
        }
        texte, categorie = messages[statut]
        flash(texte, categorie)
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/emails/<int:contact_email_id>/terminer", methods=["POST"])
@login_required
def terminer_email(contact_id, contact_email_id):
    coordonnees.terminer_lien_email(contact_email_id, current_user.id)
    flash("Email clôturé.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/emails/<int:contact_email_id>/corriger", methods=["POST"])
@login_required
def corriger_email(contact_id, contact_email_id):
    lien = coordonnees.recuperer_contact_email(contact_email_id)
    if lien is None or lien.contact_id != contact_id:
        flash("Email introuvable.", "erreur")
        return redirect(url_for("contacts.fiche", contact_id=contact_id))

    formulaire = CorrigerEmailForm(prefix=f"email-{contact_email_id}")
    if formulaire.validate_on_submit():
        autres = coordonnees.lister_autres_contacts_email(lien.email_id, contact_id)
        resultat = coordonnees.corriger_email(
            lien.email_id, formulaire.adresse_email.data, current_user.id
        )
        if resultat != "doublon":
            # Idem corriger_telephone : la correction manuelle prime
            # désormais sur l'annuaire national pour ce lien.
            coordonnees.marquer_source_manuelle_email(lien.id)
        if resultat == "doublon":
            flash(
                "Cette adresse correspond déjà à un autre email enregistré : "
                "ce serait fusionner deux adresses, pas corriger une faute "
                "de frappe. Clôturez cet email puis ajoutez la bonne adresse "
                "pour profiter du partage automatique.",
                "erreur",
            )
        elif autres:
            flash(
                "Email corrigé. Cette adresse est partagée avec "
                + ", ".join(autres) + " : la correction s'applique à eux aussi.",
                "info",
            )
        else:
            flash("Email corrigé.", "succes")
    else:
        flash("Le formulaire de correction contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


# --- Qualifications professionnelles ----------------------------------------


@bp.route("/<int:contact_id>/qualifications/avocat", methods=["POST"])
@login_required
def enregistrer_qualification_avocat(contact_id):
    formulaire = QualificationAvocatForm()
    formulaire.barreau_id.choices = _choix_avec_vide(
        reference.lister_barreaux(), "id", "libelle"
    )
    if formulaire.validate_on_submit():
        barreau_id = int(formulaire.barreau_id.data) if formulaire.barreau_id.data else None
        cabinet_id = int(formulaire.cabinet_id.data) if formulaire.cabinet_id.data else None
        qualifications.enregistrer_avocat(contact_id, current_user.id, barreau_id, cabinet_id)
        flash("Qualification avocat enregistrée.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/qualifications/avocat/supprimer", methods=["POST"])
@login_required
def supprimer_qualification_avocat(contact_id):
    qualifications.supprimer_avocat(contact_id)
    flash("Qualification avocat retirée.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/qualifications/notaire", methods=["POST"])
@login_required
def enregistrer_qualification_notaire(contact_id):
    formulaire = QualificationNotaireForm()
    if formulaire.validate_on_submit():
        office_id = int(formulaire.office_id.data) if formulaire.office_id.data else None
        qualifications.enregistrer_notaire(contact_id, current_user.id, office_id)
        flash("Qualification notaire enregistrée.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/qualifications/notaire/supprimer", methods=["POST"])
@login_required
def supprimer_qualification_notaire(contact_id):
    qualifications.supprimer_notaire(contact_id)
    flash("Qualification notaire retirée.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/qualifications/commissaire-justice", methods=["POST"])
@login_required
def enregistrer_qualification_commissaire_justice(contact_id):
    formulaire = QualificationCommissaireJusticeForm()
    if formulaire.validate_on_submit():
        etude_id = int(formulaire.etude_id.data) if formulaire.etude_id.data else None
        qualifications.enregistrer_commissaire_justice(contact_id, current_user.id, etude_id)
        flash("Qualification commissaire de justice enregistrée.", "succes")
    else:
        flash("Le formulaire contient des erreurs.", "erreur")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))


@bp.route("/<int:contact_id>/qualifications/commissaire-justice/supprimer", methods=["POST"])
@login_required
def supprimer_qualification_commissaire_justice(contact_id):
    qualifications.supprimer_commissaire_justice(contact_id)
    flash("Qualification commissaire de justice retirée.", "succes")
    return redirect(url_for("contacts.fiche", contact_id=contact_id))
