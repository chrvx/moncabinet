"""Création/mise à jour d'un contact avocat à partir d'une ligne de
l'Annuaire national (app/services/annuaire_avocats.py). Logique partagée
entre la commande CLI d'import en masse par barreau
(app/commandes.py::importer_avocats_barreau) et la recherche ponctuelle
depuis l'UI (app/blueprints/contacts/routes.py::api_annuaire_avocats /
creer_depuis_annuaire), pour ne jamais dupliquer les règles de
rapprochement (code CNBF, SIREN du cabinet) et de synchronisation des
coordonnées (voir app/repositories/coordonnees.py)."""

from app.repositories import contacts, coordonnees, qualifications
from app.services.annuaire_avocats import FORME_JURIDIQUE_EXERCICE_INDIVIDUEL, AvocatAnnuaire


def _resoudre_cabinet(avocat_annuaire: AvocatAnnuaire, utilisateur_id: int) -> int | None:
    """None pour un exercice à titre individuel (cbFormJuri = "CABI") :
    le CSV porte quand même une raison sociale et un SIREN sur cette ligne
    (le nom de l'avocat lui-même), mais ce n'est pas une personne morale
    distincte — n'en créer une que pour une vraie structure d'exercice
    (SCP, SELARL, SARL, AARPI...).

    À la création d'un nouveau cabinet, son adresse est reprise de cette
    ligne (une seule fois, jamais resynchronisée ensuite — même logique
    que coordonnees.ajouter_adresse pour un contact individuel : c'est
    presque toujours vraiment le lieu d'exercice partagé). L'email et le
    téléphone de la ligne, en revanche, ne sont jamais recopiés sur le
    cabinet : ce sont la ligne directe et la boîte mail personnelle de CET
    avocat, pas un contact générique du cabinet — les attribuer au cabinet
    ferait passer les coordonnées d'un seul associé pour celles de toute
    la structure."""
    if avocat_annuaire.forme_juridique_cabinet in (None, "", FORME_JURIDIQUE_EXERCICE_INDIVIDUEL):
        return None
    if not avocat_annuaire.siret_siren_cabinet or not avocat_annuaire.raison_sociale_cabinet:
        return None
    cabinet = contacts.recuperer_personne_morale_par_siren(avocat_annuaire.siret_siren_cabinet)
    if cabinet:
        return cabinet.contact_id
    cabinet = contacts.creer_personne_morale(
        avocat_annuaire.raison_sociale_cabinet, utilisateur_id,
        forme=avocat_annuaire.forme_juridique_cabinet,
        siren=avocat_annuaire.siret_siren_cabinet,
    )
    if avocat_annuaire.libelle_voie or avocat_annuaire.ville:
        coordonnees.ajouter_adresse(
            cabinet.contact_id, utilisateur_id,
            numero_voie=avocat_annuaire.numero_voie,
            libelle_voie=avocat_annuaire.libelle_voie,
            complement=avocat_annuaire.adresse2,
            code_postal=avocat_annuaire.code_postal,
            commune=avocat_annuaire.ville,
            source="import_annuaire",
        )
    return cabinet.contact_id


def importer_ou_mettre_a_jour(
    avocat_annuaire: AvocatAnnuaire, barreau_id: int | None, utilisateur_id: int
) -> tuple[int, str]:
    """Crée le contact s'il n'existe pas encore (rapproché par code CNBF,
    voir qualifications.recuperer_avocat_par_code_cnbf), sinon met à jour
    sa qualification et resynchronise ses coordonnées sans jamais écraser
    une correction manuelle (coordonnees.synchroniser_email/telephone).
    Renvoie (contact_id, "cree" | "maj")."""
    cabinet_id = _resoudre_cabinet(avocat_annuaire, utilisateur_id)
    avocat_existant = qualifications.recuperer_avocat_par_code_cnbf(avocat_annuaire.code_cnbf)

    if avocat_existant:
        contact_id = avocat_existant.contact_id
        qualifications.enregistrer_avocat(
            contact_id, utilisateur_id,
            barreau_id=barreau_id, cabinet_id=cabinet_id,
            code_cnbf=avocat_annuaire.code_cnbf,
        )
        coordonnees.synchroniser_email(contact_id, avocat_annuaire.email, utilisateur_id)
        coordonnees.synchroniser_telephone(contact_id, avocat_annuaire.telephone, utilisateur_id)
        return contact_id, "maj"

    personne = contacts.creer_personne_physique(
        avocat_annuaire.nom, utilisateur_id, prenom=avocat_annuaire.prenom,
    )
    qualifications.enregistrer_avocat(
        personne.contact_id, utilisateur_id,
        barreau_id=barreau_id, cabinet_id=cabinet_id,
        code_cnbf=avocat_annuaire.code_cnbf,
    )
    if avocat_annuaire.email:
        coordonnees.ajouter_email(
            personne.contact_id, avocat_annuaire.email, utilisateur_id, source="import_annuaire"
        )
    if avocat_annuaire.telephone:
        coordonnees.ajouter_telephone(
            personne.contact_id, avocat_annuaire.telephone, utilisateur_id, source="import_annuaire"
        )
    if avocat_annuaire.libelle_voie or avocat_annuaire.ville:
        coordonnees.ajouter_adresse(
            personne.contact_id, utilisateur_id,
            numero_voie=avocat_annuaire.numero_voie,
            libelle_voie=avocat_annuaire.libelle_voie,
            complement=avocat_annuaire.adresse2,
            code_postal=avocat_annuaire.code_postal,
            commune=avocat_annuaire.ville,
            source="import_annuaire",
        )
    return personne.contact_id, "cree"
