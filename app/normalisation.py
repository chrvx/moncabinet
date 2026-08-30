"""Normalisation des valeurs saisies, appliquée à l'écriture (pas à
l'affichage) pour que la donnée stockée soit cohérente une fois pour
toutes, indépendamment de la façon dont l'utilisateur l'a tapée."""

import re


def normaliser_nom(valeur: str | None) -> str | None:
    """NOM et nom d'usage en MAJUSCULES : convention administrative
    française (cf. les exemples de La Poste : "Monsieur Bernard MARCELIN")."""
    if not valeur:
        return None
    return valeur.strip().upper()


def normaliser_prenom(valeur: str | None) -> str | None:
    """Casse titre pour prénoms et ville de naissance. Approximatif sur les
    cas particuliers (particules, apostrophes : "D'Artagnan" devient
    "D'Artagnan", mais un cas comme "d'Arcy-sur-Cure" peut demander une
    petite correction manuelle) : le champ reste modifiable à la main."""
    if not valeur:
        return None
    return valeur.strip().title()


def normaliser_telephone(valeur: str | None) -> str | None:
    """Ne garde que les chiffres (et un + initial éventuel), pour que
    "06 12 34 56 78", "06-12-34-56-78" et "0612345678" soient reconnus
    comme le même numéro plutôt que trois entrées différentes.

    Un numéro français (10 chiffres commençant par 0, y compris quand il
    est saisi avec l'indicatif international +33/0033, ou 33 seul sans
    indicatif de composition internationale — rencontré tel quel dans
    l'Annuaire des avocats de France, ex. "33553486185") est en plus
    reformaté en paires ("01 02 03 04 05") pour un affichage lisible ; un
    numéro étranger qui ne suit pas ce format est laissé tel quel."""
    if not valeur:
        return None
    valeur = valeur.strip()
    if not valeur:
        return None
    chiffres = re.sub(r"\D", "", valeur)
    prefixe = "+" if valeur.startswith("+") else ""
    if prefixe and chiffres.startswith("33") and len(chiffres) == 11:
        chiffres, prefixe = "0" + chiffres[2:], ""
    elif not prefixe and chiffres.startswith("0033") and len(chiffres) == 13:
        chiffres, prefixe = "0" + chiffres[4:], ""
    elif not prefixe and chiffres.startswith("33") and len(chiffres) == 11:
        chiffres, prefixe = "0" + chiffres[2:], ""
    if len(chiffres) == 10 and chiffres.startswith("0"):
        return " ".join(chiffres[i : i + 2] for i in range(0, 10, 2))
    return prefixe + chiffres


def normaliser_email(valeur: str | None) -> str | None:
    """Minuscules et espaces superflus retirés : la partie locale d'un
    email est théoriquement sensible à la casse, mais en pratique aucun
    fournisseur courant ne distingue Jean@ de jean@, et normaliser évite
    les doublons artificiels."""
    if not valeur:
        return None
    return valeur.strip().lower()
