"""Répertoire local des offices notariaux : contrairement à l'Annuaire des
avocats de France (app/services/annuaire_avocats.py), il n'existe pas de
jeu de données ouvert avec une API filtrable ni un CSV national officiel
recensant les notaires nommément — l'annuaire officiel (notaires.fr)
interdit le scraping de ses pages de résultats via robots.txt.

La source retenue est donc un ou plusieurs CSV locaux versionnés avec
l'application (app/data/notaires/*.csv, un fichier par département),
construits manuellement à partir de données ouvertes (API Recherche
d'entreprises / Sirene, filtrée sur le code de nature juridique INSEE 6565
"office notarial") complétées au besoin par un annuaire professionnel
public. Chaque ligne représente un OFFICE (personne morale, parfois une
SCP/SELARL de plusieurs notaires associés) et non un notaire individuel :
le CSV n'a pas de colonnes nom/prénom séparées par personne comme
l'annuaire des avocats, donc à la différence d'import_avocats.py, l'import
ne crée jamais de contact personne physique — seulement l'office (voir
app/services/import_notaires.py). Ajouter un département revient à déposer
un nouveau CSV au même format dans ce répertoire."""

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPERTOIRE_DONNEES = Path(__file__).resolve().parent.parent / "data" / "notaires"


@dataclass
class OfficeAnnuaire:
    """Une ligne d'un des CSV locaux de app/data/notaires/."""

    nom: str
    siren: str | None
    numero_voie: str | None
    libelle_voie: str | None
    code_postal: str | None
    commune: str | None


#: Reconnaît un numéro de voie en tête d'adresse ("26 rue du Général
#: Vouillemont"), même logique que annuaire_avocats._MOTIF_NUMERO_VOIE.
_MOTIF_NUMERO_VOIE = re.compile(r"^(\d+\s*(?:bis|ter|quater)?)\s+(.+)$", re.IGNORECASE)


def _decouper_adresse(adresse_brute: str | None, code_postal: str | None, commune: str | None) -> tuple[str | None, str | None]:
    """L'adresse du CSV (issue de Sirene) répète en fin de chaîne le code
    postal et la commune déjà présents dans leurs propres colonnes (ex:
    "26 RUE DU GENERAL VOUILLEMONT 10200 BAR-SUR-AUBE") : on retire ce
    suffixe avant de séparer le numéro de voie du libellé, sans quoi la
    commune se retrouverait dupliquée dans libelle_voie."""
    if not adresse_brute:
        return None, None
    valeur = adresse_brute.strip()
    if code_postal and commune:
        suffixe = f"{code_postal} {commune}".strip()
        if valeur.upper().endswith(suffixe.upper()):
            valeur = valeur[: -len(suffixe)].strip()
    correspondance = _MOTIF_NUMERO_VOIE.match(valeur)
    if not correspondance:
        return None, valeur or None
    return correspondance.group(1).strip(), correspondance.group(2).strip()


def _lire_ligne(ligne: dict) -> OfficeAnnuaire:
    numero_voie, libelle_voie = _decouper_adresse(
        ligne.get("adresse"), ligne.get("code_postal"), ligne.get("commune")
    )
    return OfficeAnnuaire(
        nom=ligne["nom"].strip(),
        siren=ligne.get("siren") or None,
        numero_voie=numero_voie,
        libelle_voie=libelle_voie,
        code_postal=ligne.get("code_postal") or None,
        commune=ligne.get("commune") or None,
    )


def charger_repertoire() -> list[OfficeAnnuaire]:
    """Charge tous les CSV de app/data/notaires/ (un par département)."""
    offices = []
    for chemin in sorted(REPERTOIRE_DONNEES.glob("*.csv")):
        with chemin.open(encoding="utf-8", newline="") as fichier:
            lecteur = csv.DictReader(fichier)
            offices.extend(_lire_ligne(ligne) for ligne in lecteur if ligne.get("nom"))
    return offices


#: Le répertoire local est un petit fichier statique versionné avec
#: l'application (pas une ressource distante de plusieurs Mo comme
#: l'annuaire des avocats) : pas besoin d'un cache à durée de vie, un
#: simple singleton en mémoire process suffit.
_cache: list[OfficeAnnuaire] | None = None


def charger_repertoire_avec_cache() -> list[OfficeAnnuaire]:
    global _cache
    if _cache is None:
        _cache = charger_repertoire()
    return _cache


def _normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    return sans_accents.strip().upper()


def filtrer_par_departement(offices: list[OfficeAnnuaire], code_departement: str) -> list[OfficeAnnuaire]:
    """Filtre par code de département (ex: "10" pour l'Aube), déduit du
    code postal — il n'y a pas de colonne département dédiée dans le CSV."""
    return [o for o in offices if o.code_postal and o.code_postal[:2] == code_departement]


def rechercher(offices: list[OfficeAnnuaire], terme: str) -> list[OfficeAnnuaire]:
    """Recherche libre par nom ou commune, insensible à la casse et aux
    accents."""
    cible = _normaliser(terme)
    return [
        o for o in offices
        if cible in _normaliser(o.nom) or (o.commune and cible in _normaliser(o.commune))
    ]
