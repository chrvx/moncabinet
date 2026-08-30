"""Client de l'Annuaire des avocats de France (Conseil national des
barreaux, data.gouv.fr) : voir le plan d'intégration pour le contexte.

Il n'existe pas d'API de requête filtrable pour ce jeu de données : seule
une ressource CSV nationale complète, republiée chaque mois sous un nouvel
identifiant. `telecharger_csv` résout donc systématiquement la ressource la
plus récente via l'API dataset de data.gouv.fr avant de la télécharger, et
`filtrer_par_barreau`/`rechercher` filtrent ensuite ce résultat en mémoire
— import en masse (commande CLI) et recherche ponctuelle (route API)
partagent la même source, jamais deux mécanismes réseau distincts.
"""

import csv
import io
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date

import requests

URL_DATASET = "https://www.data.gouv.fr/api/1/datasets/annuaire-des-avocats-de-france/"
DELAI_ATTENTE_SECONDES = 30

#: Durée de vie du cache mémoire du CSV national pour la recherche
#: ponctuelle depuis l'UI (voir telecharger_csv_avec_cache) : évite de
#: re-télécharger 17 Mo à chaque recherche, sans empêcher une nouvelle
#: version mensuelle d'être reprise dans la journée.
DUREE_CACHE_SECONDES = 6 * 3600

_cache: dict = {"donnees": None, "horodatage": 0.0}


@dataclass
class AvocatAnnuaire:
    """Une ligne du CSV nationale, mappée sur ses colonnes réelles
    (avCnbfCode, avNom, avPrenom, etc. — voir le mapping dans
    _lire_ligne). code_cnbf est l'identifiant stable utilisé pour le
    rapprochement avec un avocat déjà enregistré (voir
    app/repositories/qualifications.py::recuperer_avocat_par_code_cnbf)."""

    code_cnbf: str
    barreau_libelle: str
    barreau_id_annuaire: str
    nom: str
    prenom: str
    numero_voie: str | None
    libelle_voie: str | None
    adresse2: str | None
    code_postal: str | None
    ville: str | None
    telephone: str | None
    raison_sociale_cabinet: str | None
    siret_siren_cabinet: str | None
    email: str | None
    date_serment: date | None


def _parser_date(valeur: str | None) -> date | None:
    """Les dates du CSV sont au format entier YYYYMMDD (ex: "20190101")."""
    if not valeur or not valeur.strip():
        return None
    valeur = valeur.strip()
    try:
        return date(int(valeur[0:4]), int(valeur[4:6]), int(valeur[6:8]))
    except (ValueError, IndexError):
        return None


#: Reconnaît un numéro de voie en tête d'adresse ("2 avenue Pasteur", "16
#: rue Théophile Roussel", "9bis rue de la Paix"), pour séparer numéro et
#: libellé — le CSV national met les deux dans la même colonne (cbAdresse1),
#: contrairement au modèle local (adresse.numero_voie / libelle_voie
#: distincts, migration 0005). Sans cette séparation, numero_voie resterait
#: NULL et la fiche contact afficherait littéralement "None avenue Pasteur"
#: (voir app/templates/contacts/fiche.html, qui ne protège pas ce cas).
_MOTIF_NUMERO_VOIE = re.compile(r"^(\d+\s*(?:bis|ter|quater)?)\s+(.+)$", re.IGNORECASE)


def _separer_numero_voie(adresse1: str | None) -> tuple[str | None, str | None]:
    if not adresse1:
        return None, None
    correspondance = _MOTIF_NUMERO_VOIE.match(adresse1.strip())
    if not correspondance:
        return None, adresse1.strip()
    return correspondance.group(1).strip(), correspondance.group(2).strip()


def _lire_ligne(ligne: dict) -> AvocatAnnuaire:
    numero_voie, libelle_voie = _separer_numero_voie(ligne.get("cbAdresse1"))
    return AvocatAnnuaire(
        code_cnbf=ligne["avCnbfCode"].strip(),
        barreau_libelle=ligne["Barreau"].strip(),
        barreau_id_annuaire=ligne["BarreauId"].strip(),
        nom=ligne["avNom"].strip(),
        prenom=ligne["avPrenom"].strip(),
        numero_voie=numero_voie,
        libelle_voie=libelle_voie,
        adresse2=ligne.get("cbAdresse2") or None,
        code_postal=ligne.get("cbCp") or None,
        ville=ligne.get("cbVille") or None,
        telephone=ligne.get("cbTel") or None,
        raison_sociale_cabinet=ligne.get("cbRaisonSociale") or None,
        siret_siren_cabinet=ligne.get("cbSiretSiren") or None,
        email=ligne.get("avMelOrdre") or None,
        date_serment=_parser_date(ligne.get("acDateSerment")),
    )


def _resoudre_url_derniere_ressource() -> str:
    """Le dataset republie un nouveau fichier CSV chaque mois sous un
    nouvel identifiant de ressource : on ne code jamais cet identifiant en
    dur, on retrouve systématiquement la ressource CSV la plus récente via
    le champ "resources" de l'API dataset."""
    reponse = requests.get(URL_DATASET, timeout=DELAI_ATTENTE_SECONDES)
    reponse.raise_for_status()
    ressources_csv = [
        r for r in reponse.json().get("resources", []) if r.get("format") == "csv"
    ]
    if not ressources_csv:
        raise RuntimeError("Aucune ressource CSV trouvée sur le dataset annuaire-des-avocats-de-france.")
    plus_recente = max(ressources_csv, key=lambda r: r["created_at"])
    return plus_recente["url"]


def telecharger_csv() -> list[AvocatAnnuaire]:
    """Télécharge et parse le CSV national complet (~17 Mo, un fichier par
    mois, tous barreaux confondus). À appeler une seule fois par commande
    CLI ou requête, le résultat étant destiné à être filtré en mémoire par
    filtrer_par_barreau/rechercher plutôt que re-téléchargé."""
    url = _resoudre_url_derniere_ressource()
    reponse = requests.get(url, timeout=DELAI_ATTENTE_SECONDES)
    reponse.raise_for_status()
    contenu = reponse.content.decode("utf-8-sig")
    lecteur = csv.DictReader(io.StringIO(contenu), delimiter=";")
    # Le fichier contient une ligne parasite par barreau (162 constatées),
    # un marqueur de section ("V1.8" en guise de code CNBF, suivi du
    # nombre d'avocats de la section) plutôt qu'un vrai avocat — à exclure
    # explicitement, sans quoi elle serait importée comme un contact.
    return [
        _lire_ligne(ligne)
        for ligne in lecteur
        if ligne.get("avCnbfCode") and ligne["avCnbfCode"] != "V1.8"
    ]


def normaliser_libelle_barreau(libelle: str) -> str:
    """Rapproche un libellé de barreau local ("barreau d'Agen") du libellé
    brut de l'annuaire ("AGEN") : retire le préfixe administratif, les
    accents et la casse."""
    sans_prefixe = libelle
    for prefixe in ("barreau de l'", "barreau de la ", "barreau de ", "barreau des ", "barreau du ", "barreau d'"):
        if sans_prefixe.lower().startswith(prefixe):
            sans_prefixe = sans_prefixe[len(prefixe):]
            break
    sans_accents = unicodedata.normalize("NFKD", sans_prefixe).encode("ascii", "ignore").decode("ascii")
    return sans_accents.strip().upper()


def filtrer_par_barreau(avocats: list[AvocatAnnuaire], barreau_libelle_local: str) -> list[AvocatAnnuaire]:
    """Filtre le résultat de telecharger_csv sur un barreau donné, en
    rapprochant le libellé local ("barreau d'Agen") du libellé brut du
    CSV ("AGEN") — voir normaliser_libelle_barreau. Si aucune ligne ne
    correspond, le libellé local ne se rapproche peut-être pas
    automatiquement du libellé annuaire : à vérifier au cas par cas."""
    cible = normaliser_libelle_barreau(barreau_libelle_local)
    return [a for a in avocats if normaliser_libelle_barreau(a.barreau_libelle) == cible]


def apparier_barreau_local(barreaux_locaux, barreau_libelle_annuaire: str):
    """Retrouve, parmi une liste de Barreau locaux (voir
    app/repositories/reference.py::lister_barreaux), celui qui correspond
    au libellé brut d'une ligne de l'annuaire — None si aucun ne
    correspond automatiquement."""
    cible = normaliser_libelle_barreau(barreau_libelle_annuaire)
    return next(
        (b for b in barreaux_locaux if normaliser_libelle_barreau(b.libelle) == cible), None
    )


def telecharger_csv_avec_cache() -> list[AvocatAnnuaire]:
    """Comme telecharger_csv, mais mémorise le résultat en mémoire process
    pendant DUREE_CACHE_SECONDES : pensé pour la recherche ponctuelle
    depuis l'UI (voir contacts.routes.api_annuaire_avocats), où
    retélécharger 17 Mo à chaque frappe serait trop lent."""
    maintenant = time.monotonic()
    if _cache["donnees"] is None or maintenant - _cache["horodatage"] > DUREE_CACHE_SECONDES:
        _cache["donnees"] = telecharger_csv()
        _cache["horodatage"] = maintenant
    return _cache["donnees"]


def rechercher(avocats: list[AvocatAnnuaire], nom: str, prenom: str | None = None) -> list[AvocatAnnuaire]:
    """Recherche ponctuelle en mémoire par nom (et éventuellement prénom),
    insensible à la casse — pour le cas d'un confrère hors des barreaux
    déjà importés en masse."""
    nom_normalise = nom.strip().upper()
    prenom_normalise = prenom.strip().upper() if prenom else None
    resultats = [a for a in avocats if nom_normalise in a.nom.upper()]
    if prenom_normalise:
        resultats = [a for a in resultats if prenom_normalise in a.prenom.upper()]
    return resultats
