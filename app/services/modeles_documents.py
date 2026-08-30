"""Découverte des modèles de documents Typst.

Un modèle est un répertoire sous app/documents_modeles/<slug>/ contenant
modele.typ (le gabarit) et metadata.json (libellé + champs à saisir à la
main, non déductibles du dossier/contact). Ce sont des fichiers gérés
directement sur le serveur par un utilisateur technique — volontairement
pas d'écran d'upload dans l'application, voir la discussion de conception
autour de la génération de documents."""

import json
from dataclasses import dataclass
from pathlib import Path

REPERTOIRE_MODELES = Path(__file__).resolve().parent.parent / "documents_modeles"

#: Types de champ acceptés dans metadata.json, mappés vers les champs WTForms
#: correspondants — voir app/blueprints/documents/forms.py.
TYPES_CHAMP_EXTRA = ("texte", "zone_texte", "case", "entier", "date")


@dataclass
class ChampExtra:
    nom: str
    label: str
    type: str


@dataclass
class ModeleDocument:
    slug: str
    libelle: str
    champs_extra: list[ChampExtra]

    @property
    def chemin_typ(self) -> Path:
        return REPERTOIRE_MODELES / self.slug / "modele.typ"


def _charger(slug: str) -> ModeleDocument | None:
    chemin_metadata = REPERTOIRE_MODELES / slug / "metadata.json"
    if not chemin_metadata.is_file():
        return None
    metadata = json.loads(chemin_metadata.read_text(encoding="utf-8"))
    champs_extra = [ChampExtra(**champ) for champ in metadata.get("champs_extra", [])]
    return ModeleDocument(slug=slug, libelle=metadata["libelle"], champs_extra=champs_extra)


def lister() -> list[ModeleDocument]:
    if not REPERTOIRE_MODELES.is_dir():
        return []
    modeles = (
        _charger(chemin.name)
        for chemin in sorted(REPERTOIRE_MODELES.iterdir())
        if chemin.is_dir()
    )
    return [m for m in modeles if m is not None]


def recuperer(slug: str) -> ModeleDocument | None:
    # slug est un nom de répertoire, jamais interprété par le système de
    # fichiers autrement qu'en le collant tel quel sous REPERTOIRE_MODELES ;
    # il vient d'un <select> dont les seules valeurs valides sont produites
    # par lister() ci-dessus, donc pas de risque de traversée de chemin tant
    # qu'on vérifie ici qu'il correspond bien à un modèle connu.
    if "/" in slug or "\\" in slug or slug in (".", ".."):
        return None
    return _charger(slug)
