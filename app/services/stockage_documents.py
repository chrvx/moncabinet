"""Stockage des fichiers rattachés à un dossier — dépôt manuel depuis la
fiche dossier, pièce jointe versée depuis un e-mail importé — sous
instance/documents/<dossier_id>/. Voir
docs/phase-documents-correspondance.md §8 : le fichier est toujours
enregistré sous un nom généré (UUID), jamais sous son nom d'origine, qui
vient de l'extérieur et pourrait contenir ../ pour écrire hors du répertoire
prévu. Seul Document.titre garde un nom lisible, utilisé pour l'affichage et
le téléchargement — voir app/blueprints/documents/routes.py::telecharger."""

import uuid
from pathlib import Path

from flask import current_app


def enregistrer(dossier_id: int, nom_origine: str, contenu: bytes) -> str:
    """Renvoie le chemin relatif à instance/, pour Document.chemin_fichier."""
    racine_instance = Path(current_app.instance_path)
    repertoire = racine_instance / "documents" / str(dossier_id)
    repertoire.mkdir(parents=True, exist_ok=True)
    nom_reel = f"{uuid.uuid4()}{Path(nom_origine).suffix}"
    (repertoire / nom_reel).write_bytes(contenu)
    return str((repertoire / nom_reel).relative_to(racine_instance))
