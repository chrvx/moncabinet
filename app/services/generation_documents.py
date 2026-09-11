"""Fusion d'un modèle Typst avec les données d'un dossier, puis compilation
en PDF — voir la discussion de conception autour du choix de Typst
(rendu déterministe, pagination automatique correcte, logique conditionnelle
native) plutôt qu'un format .docx/.odt pour les documents générés.

Le modèle reste éditable après fusion : le fichier data.json et la copie du
.typ produits ici sont conservés (voir dossier d'exécution), pour qu'un
utilisateur puisse retélécharger le .typ fusionné et le personnaliser
localement avec son propre outillage Typst (typst watch...)."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from flask import current_app

from app.repositories import coordonnees, dossiers, matieres
from app.repositories.contacts import recuperer_personne_morale, recuperer_personne_physique
from app.repositories.documents import creer_genere
from app.services.modeles_documents import ModeleDocument


class ErreurGenerationDocument(Exception):
    """Levée quand `typst compile` échoue — message brut de Typst, en
    général assez clair pour l'utilisateur (champ manquant, syntaxe...)."""


def _repertoire_documents() -> Path:
    return Path(current_app.instance_path) / "documents"


def resoudre_chemin(chemin_relatif: str) -> Path:
    """Reconstitue le chemin absolu d'un fichier stocké en base (document.chemin_fichier ou document_genere.chemin_typ), relatif à instance/."""
    return Path(current_app.instance_path) / chemin_relatif


def _formater_adresse(adresse) -> str:
    lignes_voie = " ".join(
        partie
        for partie in (adresse.numero_voie, adresse.libelle_voie)
        if partie
    )
    lignes = [
        adresse.complement,
        lignes_voie or None,
        " ".join(partie for partie in (adresse.code_postal, adresse.commune) if partie) or None,
    ]
    return "\n".join(ligne for ligne in lignes if ligne)


def _contexte_contact(contact_id: int, type_contact: str) -> dict:
    if type_contact == "personne_physique":
        personne = recuperer_personne_physique(contact_id)
        identite = {
            "nom": personne.nom,
            "prenom": personne.prenom,
            "profession": personne.profession,
        }
    else:
        personne = recuperer_personne_morale(contact_id)
        identite = {
            "raison_sociale": personne.raison_sociale,
            "forme": personne.forme,
        }

    adresses = coordonnees.lister_adresses(contact_id)
    telephones = coordonnees.lister_telephones(contact_id)
    emails = coordonnees.lister_emails(contact_id)

    return {
        "type_contact": type_contact,
        **identite,
        "adresse": _formater_adresse(adresses[0][0]) if adresses else None,
        "telephone": telephones[0][0].numero if telephones else None,
        "email": emails[0][0].adresse_email if emails else None,
    }


def construire_contexte(dossier_id: int) -> dict:
    """Assemble les données du dossier et de ses intervenants (groupés par
    rôle) en un dict JSON-sérialisable, lu depuis le modèle Typst via
    `json("data.json")`."""
    dossier = dossiers.recuperer(dossier_id)
    matiere_libelle = None
    if dossier.matiere_id:
        matiere_libelle = next(
            (m.libelle for m in matieres.lister(actives_seulement=False) if m.id == dossier.matiere_id),
            None,
        )

    intervenants_par_role: dict[str, list[dict]] = {}
    for i in dossiers.lister_intervenants(dossier_id):
        contexte = _contexte_contact(i["contact_id"], i["type_contact"])
        intervenants_par_role.setdefault(i["role_libelle"], []).append(contexte)

    return {
        "dossier": {
            "reference": dossier.reference,
            "categorie": dossier.categorie,
            "matiere": matiere_libelle,
            "date_ouverture": dossier.date_ouverture.isoformat() if dossier.date_ouverture else None,
        },
        "intervenants": intervenants_par_role,
    }


def generer(
    dossier_id: int,
    modele: ModeleDocument,
    champs_extra: dict,
    utilisateur_id: int,
):
    """Fusionne le modèle avec les données du dossier, compile le PDF, et
    trace le résultat en base. Lève ErreurGenerationDocument si `typst
    compile` échoue (champ manquant, syntaxe Typst invalide...)."""
    horodatage = datetime.now().strftime("%Y%m%d%H%M%S")
    repertoire_execution = (
        _repertoire_documents() / str(dossier_id) / f"{horodatage}_{modele.slug}"
    )
    repertoire_execution.mkdir(parents=True, exist_ok=True)

    contexte = construire_contexte(dossier_id)
    contexte["extra"] = champs_extra
    (repertoire_execution / "data.json").write_text(
        json.dumps(contexte, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    chemin_typ = repertoire_execution / "modele.typ"
    shutil.copyfile(modele.chemin_typ, chemin_typ)

    chemin_pdf = repertoire_execution / "document.pdf"
    resultat = subprocess.run(
        ["typst", "compile", chemin_typ.name, chemin_pdf.name],
        cwd=repertoire_execution,
        capture_output=True,
        text=True,
    )
    if resultat.returncode != 0:
        raise ErreurGenerationDocument(resultat.stderr.strip() or "Échec de la compilation Typst.")

    racine_instance = Path(current_app.instance_path)
    return creer_genere(
        dossier_id=dossier_id,
        modele_slug=modele.slug,
        titre=modele.libelle,
        chemin_fichier=str(chemin_pdf.relative_to(racine_instance)),
        chemin_typ=str(chemin_typ.relative_to(racine_instance)),
        utilisateur_id=utilisateur_id,
    )
