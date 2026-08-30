import click
from werkzeug.security import generate_password_hash

from app.repositories import reference, utilisateurs
from app.services import annuaire_avocats, annuaire_notaires, import_avocats, import_notaires

# Il n'y a pas d'inscription depuis l'application : c'est vous (le titulaire)
# qui créez les comptes des stagiaires ou d'un futur collaborateur, depuis
# le terminal. Ça évite d'avoir à construire et sécuriser un formulaire
# d'inscription pour un besoin qui ne concerne que 2-3 personnes.


def enregistrer_commandes(app):
    @app.cli.command("creer-utilisateur")
    @click.option("--nom", prompt=True)
    @click.option(
        "--mot-de-passe",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    )
    @click.option(
        "--role",
        type=click.Choice(["avocat", "collaborateur", "stagiaire"]),
        prompt=True,
    )
    def creer_utilisateur(nom, mot_de_passe, role):
        """Crée un compte utilisateur (une fois par nouveau membre du cabinet)."""
        hash_mdp = generate_password_hash(mot_de_passe)
        utilisateur = utilisateurs.creer(nom, hash_mdp, role)
        click.echo(f"Utilisateur créé : {utilisateur.nom}, rôle {utilisateur.role}")

    @app.cli.command("importer-avocats-barreau")
    @click.option(
        "--barreau",
        prompt=True,
        help="Libellé exact du barreau local (ex: \"barreau d'Agen\"), voir flask parametres.liste_barreaux.",
    )
    @click.option(
        "--utilisateur",
        prompt=True,
        help="Nom de l'utilisateur à qui attribuer les contacts créés (cree_par).",
    )
    def importer_avocats_barreau(barreau, utilisateur):
        """Importe/resynchronise les avocats d'un barreau depuis l'Annuaire
        des avocats de France (data.gouv.fr). Réexécutable sans effet de
        bord : les avocats déjà importés sont rapprochés par leur numéro
        CNBF (voir migration 0015) et leurs coordonnées mises à jour selon
        la règle décrite dans app/repositories/coordonnees.py
        (synchroniser_email/synchroniser_telephone) — une coordonnée
        corrigée à la main dans l'application n'est jamais écrasée."""
        utilisateur_compte = utilisateurs.recuperer_par_nom(utilisateur)
        if utilisateur_compte is None:
            raise click.ClickException(f"Utilisateur introuvable : {utilisateur}")

        barreau_local = next(
            (b for b in reference.lister_barreaux(actifs_seulement=False) if b.libelle.lower() == barreau.lower()),
            None,
        )
        if barreau_local is None:
            raise click.ClickException(
                f"Barreau local introuvable : {barreau!r} (voir flask parametres.liste_barreaux pour les libellés exacts)."
            )

        click.echo("Téléchargement de l'annuaire national (~17 Mo)...")
        avocats_annuaire = annuaire_avocats.telecharger_csv()
        avocats_du_barreau = annuaire_avocats.filtrer_par_barreau(avocats_annuaire, barreau_local.libelle)
        if not avocats_du_barreau:
            raise click.ClickException(
                f"Aucun avocat trouvé pour {barreau_local.libelle!r} dans l'annuaire : "
                "le rapprochement automatique du libellé a peut-être échoué pour ce barreau."
            )

        nb_crees = nb_maj = 0
        for avocat_annuaire in avocats_du_barreau:
            _, statut = import_avocats.importer_ou_mettre_a_jour(
                avocat_annuaire, barreau_local.id, utilisateur_compte.id
            )
            if statut == "cree":
                nb_crees += 1
            else:
                nb_maj += 1

        click.echo(f"Import terminé pour {barreau_local.libelle} : {nb_crees} créé(s), {nb_maj} mis à jour.")

    @app.cli.command("importer-notaires-departement")
    @click.option(
        "--departement",
        prompt=True,
        help="Code du département (ex: 10 pour l'Aube), voir app/data/notaires/.",
    )
    @click.option(
        "--utilisateur",
        prompt=True,
        help="Nom de l'utilisateur à qui attribuer les contacts créés (cree_par).",
    )
    def importer_notaires_departement(departement, utilisateur):
        """Importe/rapproche les offices notariaux d'un département depuis
        le répertoire local (app/data/notaires/*.csv) : contrairement à
        importer-avocats-barreau, aucun téléchargement n'a lieu, ce
        répertoire n'ayant pas d'équivalent API/dataset filtrable pour les
        notaires (voir app/services/annuaire_notaires.py)."""
        utilisateur_compte = utilisateurs.recuperer_par_nom(utilisateur)
        if utilisateur_compte is None:
            raise click.ClickException(f"Utilisateur introuvable : {utilisateur}")

        offices = annuaire_notaires.charger_repertoire()
        offices_du_departement = annuaire_notaires.filtrer_par_departement(offices, departement)
        if not offices_du_departement:
            raise click.ClickException(
                f"Aucun office trouvé pour le département {departement!r} : "
                "le CSV correspondant n'a peut-être pas encore été ajouté à app/data/notaires/."
            )

        nb_crees = nb_rapproches = 0
        for office_annuaire in offices_du_departement:
            _, statut = import_notaires.importer_ou_recuperer_office(
                office_annuaire, utilisateur_compte.id
            )
            if statut == "cree":
                nb_crees += 1
            else:
                nb_rapproches += 1

        click.echo(f"Import terminé pour le département {departement} : {nb_crees} créé(s), {nb_rapproches} rapproché(s).")
