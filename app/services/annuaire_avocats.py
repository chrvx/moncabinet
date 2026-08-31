"""Client de l'Annuaire des avocats de France (Conseil national des
barreaux, data.gouv.fr) : voir le plan d'intégration pour le contexte.

Il n'existe pas d'API de requête filtrable pour ce jeu de données : seule
une ressource CSV nationale complète, republiée environ une fois par mois
sous un nouvel identifiant. Comme l'ajout d'avocats est un événement rare
dans ce cabinet (pas quotidien, souvent les mêmes confrères locaux qui
reviennent), le CSV est conservé indéfiniment sur disque (voir
_repertoire_cache) plutôt que retéléchargé à chaque usage : `telecharger_csv`
ne va chercher le gros fichier (~17 Mo) que si un petit appel à l'API
dataset (quelques Ko) révèle qu'une nouvelle version a été publiée depuis
la dernière fois. `filtrer_par_barreau`/`rechercher` filtrent ensuite ce
résultat en mémoire — import en masse (commande CLI) et recherche
ponctuelle (route API) partagent la même source et le même cache, jamais
deux mécanismes réseau distincts.
"""

import csv
import io
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from flask import current_app

URL_DATASET = "https://www.data.gouv.fr/api/1/datasets/annuaire-des-avocats-de-france/"
DELAI_ATTENTE_SECONDES = 30

_NOM_FICHIER_CSV = "dernier.csv"
_NOM_FICHIER_METADONNEES = "dernier.json"

#: Valeur de cbFormJuri pour un exercice à titre individuel ("cabinet
#: individuel") : la ligne porte quand même une raison sociale (le nom de
#: l'avocat lui-même, ex. "ACKERMANN YANNICK") et un SIREN, mais ce n'est
#: pas une personne morale distincte — voir import_avocats._resoudre_cabinet,
#: qui ne doit créer/lier un cabinet que pour une vraie structure (SCP,
#: SELARL, SARL, AARPI...), jamais pour ce cas (de très loin le plus
#: fréquent : ~52 000 lignes sur ~75 000 dans le fichier national).
FORME_JURIDIQUE_EXERCICE_INDIVIDUEL = "CABI"

@dataclass
class AvocatAnnuaire:
    """Une ligne du CSV nationale, mappée sur ses colonnes réelles
    (avCnbfCode, avNom, avPrenom, etc. — voir le mapping dans
    _lire_ligne). code_cnbf est l'identifiant stable utilisé pour le
    rapprochement avec un avocat déjà enregistré (voir
    app/repositories/qualifications.py::recuperer_avocat_par_code_cnbf).
    genre reprend telle quelle la colonne "civilit" du CSV ("M"/"F"), qui
    partage son codage avec personne_physique.genre (voir
    app/blueprints/contacts/forms.py) — à ne pas confondre avec
    civilite_id, toujours forcé à "ME" (Maître) pour un avocat (voir
    qualifications.enregistrer_avocat) : c'est ce genre qui permettra
    d'accorder correctement les courriers générés (confrère/consœur,
    Monsieur/Madame...)."""

    code_cnbf: str
    barreau_libelle: str
    barreau_id_annuaire: str
    nom: str
    prenom: str
    genre: str | None
    numero_voie: str | None
    libelle_voie: str | None
    adresse2: str | None
    code_postal: str | None
    ville: str | None
    telephone: str | None
    raison_sociale_cabinet: str | None
    forme_juridique_cabinet: str | None
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
        genre=ligne.get("civilit") or None,
        numero_voie=numero_voie,
        libelle_voie=libelle_voie,
        adresse2=ligne.get("cbAdresse2") or None,
        code_postal=ligne.get("cbCp") or None,
        ville=ligne.get("cbVille") or None,
        telephone=ligne.get("cbTel") or None,
        raison_sociale_cabinet=ligne.get("cbRaisonSociale") or None,
        forme_juridique_cabinet=ligne.get("cbFormJuri") or None,
        siret_siren_cabinet=ligne.get("cbSiretSiren") or None,
        email=ligne.get("avMelOrdre") or None,
        date_serment=_parser_date(ligne.get("acDateSerment")),
    )


def _resoudre_derniere_ressource() -> dict:
    """Le dataset republie un nouveau fichier CSV chaque mois sous un
    nouvel identifiant de ressource : on ne code jamais cet identifiant en
    dur, on retrouve systématiquement la ressource CSV la plus récente via
    le champ "resources" de l'API dataset. Renvoie la ressource entière
    (id, url, created_at...), pas seulement son URL, pour pouvoir comparer
    son id à celui du cache local (voir _repertoire_cache)."""
    reponse = requests.get(URL_DATASET, timeout=DELAI_ATTENTE_SECONDES)
    reponse.raise_for_status()
    ressources_csv = [
        r for r in reponse.json().get("resources", []) if r.get("format") == "csv"
    ]
    if not ressources_csv:
        raise RuntimeError("Aucune ressource CSV trouvée sur le dataset annuaire-des-avocats-de-france.")
    return max(ressources_csv, key=lambda r: r["created_at"])


def _repertoire_cache() -> Path:
    """Suit la même convention que app/services/generation_documents.py
    pour ses fichiers générés : un sous-répertoire de current_app.instance_path
    (donc sous instance/, déjà exclu de git). Valide aussi bien dans une
    requête que dans une commande Flask CLI (app/commandes.py), qui
    s'exécute avec un contexte d'application actif."""
    repertoire = Path(current_app.instance_path) / "annuaire_avocats"
    repertoire.mkdir(parents=True, exist_ok=True)
    return repertoire


def _lire_metadonnees_locales() -> dict | None:
    chemin = _repertoire_cache() / _NOM_FICHIER_METADONNEES
    if not chemin.exists():
        return None
    return json.loads(chemin.read_text(encoding="utf-8"))


def _ecrire_cache(ressource: dict, contenu: bytes) -> None:
    repertoire = _repertoire_cache()
    # Écriture dans un fichier temporaire puis remplacement atomique
    # (os.replace), pour ne jamais laisser un cache à moitié écrit si le
    # téléchargement est interrompu en cours de route.
    chemin_csv = repertoire / _NOM_FICHIER_CSV
    chemin_temporaire = repertoire / f"{_NOM_FICHIER_CSV}.tmp"
    chemin_temporaire.write_bytes(contenu)
    os.replace(chemin_temporaire, chemin_csv)
    (repertoire / _NOM_FICHIER_METADONNEES).write_text(
        json.dumps({"id": ressource["id"], "created_at": ressource["created_at"], "url": ressource["url"]}),
        encoding="utf-8",
    )


def _parser_csv(contenu: str) -> list[AvocatAnnuaire]:
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


def telecharger_csv() -> list[AvocatAnnuaire]:
    """Point d'entrée unique pour l'import en masse (CLI) comme pour la
    recherche ponctuelle (route API) : un téléchargement déclenché par
    l'un profite aussi à l'autre. Le CSV national (~17 Mo) est conservé
    indéfiniment sur disque (_repertoire_cache) — un petit appel à l'API
    dataset (quelques Ko) suffit à savoir si la version en cache est
    encore la dernière publiée ; le gros fichier n'est retéléchargé que
    si un nouvel identifiant de ressource est apparu. Si cet appel échoue
    (réseau indisponible) et qu'un cache local existe, on l'utilise tel
    quel plutôt que de faire échouer la recherche pour un mois de retard
    éventuel ; sans cache local du tout, l'erreur remonte normalement."""
    metadonnees_locales = _lire_metadonnees_locales()
    chemin_csv = _repertoire_cache() / _NOM_FICHIER_CSV

    try:
        derniere_ressource = _resoudre_derniere_ressource()
    except requests.RequestException:
        if metadonnees_locales and chemin_csv.exists():
            return _parser_csv(chemin_csv.read_text(encoding="utf-8-sig"))
        raise

    if (
        metadonnees_locales
        and metadonnees_locales.get("id") == derniere_ressource["id"]
        and chemin_csv.exists()
    ):
        return _parser_csv(chemin_csv.read_text(encoding="utf-8-sig"))

    reponse = requests.get(derniere_ressource["url"], timeout=DELAI_ATTENTE_SECONDES)
    reponse.raise_for_status()
    _ecrire_cache(derniere_ressource, reponse.content)
    return _parser_csv(reponse.content.decode("utf-8-sig"))


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
