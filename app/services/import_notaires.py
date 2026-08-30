"""Création/rapprochement d'un contact office notarial (personne morale) à
partir d'une ligne du répertoire local (app/services/annuaire_notaires.py).
Pendant côté notaires de import_avocats.py, avec deux différences dictées
par les données disponibles :

- il n'y a pas d'identifiant stable équivalent au code CNBF pour rapprocher
  un office déjà importé : on utilise le SIREN quand le CSV en fournit un
  (comme pour le cabinet d'un avocat, voir import_avocats._resoudre_cabinet)
  : sinon, un nouveau contact est créé à chaque fois (~15% des lignes du
  CSV, sans identifiant fiable pour éviter les doublons) ;
- le CSV ne recense que des offices (personnes morales, parfois plusieurs
  notaires associés), jamais un notaire individuel nommément : aucun
  contact personne physique n'est donc créé ici. C'est à l'utilisateur de
  créer ensuite chaque notaire associé et de le rattacher à cet office
  depuis sa fiche (champ "Office notarial", déjà existant)."""

from app.modeles import PersonneMorale
from app.repositories import contacts, coordonnees
from app.services.annuaire_notaires import OfficeAnnuaire


def importer_ou_recuperer_office(
    office_annuaire: OfficeAnnuaire, utilisateur_id: int
) -> tuple[PersonneMorale, str]:
    """Renvoie (personne_morale, "rapproche" | "cree")."""
    if office_annuaire.siren:
        office_existant = contacts.recuperer_personne_morale_par_siren(office_annuaire.siren)
        if office_existant:
            return office_existant, "rapproche"

    office = contacts.creer_personne_morale(
        office_annuaire.nom, utilisateur_id, siren=office_annuaire.siren,
    )
    if office_annuaire.libelle_voie or office_annuaire.commune:
        coordonnees.ajouter_adresse(
            office.contact_id, utilisateur_id,
            numero_voie=office_annuaire.numero_voie,
            libelle_voie=office_annuaire.libelle_voie,
            code_postal=office_annuaire.code_postal,
            commune=office_annuaire.commune,
            source="import_annuaire",
        )
    return office, "cree"
