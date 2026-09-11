"""Synchronisation IMAP des dossiers clients, et lecture des e-mails déjà
importés — voir docs/phase-documents-correspondance.md §5.

Le classement (quel message appartient à quel dossier) est entièrement
délégué à l'organisation que l'utilisateur applique déjà dans Thunderbird :
un répertoire IMAP par dossier, sous IMAP_PREFIXE_DOSSIERS, nommé en
commençant par la référence du dossier. L'application ne fait que lire ce
nom ; elle ne devine rien. Lecture strictement passive : BODY.PEEK partout
(jamais BODY), aucun select en écriture, aucun message déplacé, supprimé ou
marqué comme lu."""

import email
import imaplib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime

from flask import current_app

from app.modeles import Document
from app.repositories import dossiers
from app.repositories import documents as documents_repo
from app.services import stockage_documents
from app.services.generation_documents import resoudre_chemin


class ErreurSynchronisation(Exception):
    """Connexion ou authentification IMAP impossible."""


@dataclass
class AnomalieSynchronisation:
    nom_repertoire_imap: str
    raison: str


@dataclass
class DossierSynchronise:
    dossier_id: int
    reference: str
    documents_importes: list[Document] = field(default_factory=list)


@dataclass
class CompteRendu:
    dossiers_synchronises: list[DossierSynchronise] = field(default_factory=list)
    anomalies: list[AnomalieSynchronisation] = field(default_factory=list)

    @property
    def nb_importes(self) -> int:
        return sum(len(d.documents_importes) for d in self.dossiers_synchronises)


def _decoder_entete(valeur: str | None) -> str:
    if not valeur:
        return ""
    morceaux = decode_header(valeur)
    return "".join(
        morceau.decode(encodage or "utf-8", errors="replace") if isinstance(morceau, bytes) else morceau
        for morceau, encodage in morceaux
    )


_MOTIF_LIST = re.compile(r'^\([^)]*\)\s+"[^"]*"\s+(?P<nom>.+)$')


def _repertoires_dossiers(conn: imaplib.IMAP4_SSL, prefixe: str) -> list[str]:
    """Noms des répertoires IMAP sous le préfixe configuré. Liste tout
    l'arbre et filtre en Python plutôt que de passer un motif de recherche
    au serveur (LIST) : les règles de guillemetage du motif varient trop
    d'un serveur IMAP à l'autre pour être fiables, et l'arbre d'une boîte de
    cabinet reste petit."""
    typ, data = conn.list()
    if typ != "OK" or not data:
        return []
    noms = []
    for ligne in data:
        if ligne is None:
            continue
        m = _MOTIF_LIST.match(ligne.decode(errors="replace"))
        if not m:
            continue
        nom = m.group("nom").strip().strip('"')
        if nom.startswith(f"{prefixe}/") or nom.startswith(f"{prefixe}."):
            noms.append(nom)
    return noms


def _reference_depuis_nom(nom_repertoire: str, prefixe: str) -> str | None:
    """Les 5 premiers chiffres du nom du répertoire, préfixe ignoré — ex:
    "dossier/26001_Dupont" -> "26001". None si la convention n'est pas
    respectée (faute de frappe, dossier pas encore ouvert)."""
    nom = nom_repertoire[len(prefixe) + 1 :]
    m = re.match(r"^(\d{5})", nom)
    return m.group(1) if m else None


def _adresse(entete: str | None) -> str:
    adresses = getaddresses([entete or ""])
    return adresses[0][1] if adresses else ""


def _corps_brut(conn: imaplib.IMAP4_SSL, uid: bytes, partie: str) -> bytes | None:
    typ, data = conn.uid("fetch", uid, f"(BODY.PEEK[{partie}])")
    if typ != "OK" or not data or data[0] is None:
        return None
    brut = data[0]
    return brut[1] if isinstance(brut, tuple) else brut


def _message_id_existant(conn: imaplib.IMAP4_SSL, uid: bytes) -> str | None:
    brut = _corps_brut(conn, uid, "HEADER.FIELDS (MESSAGE-ID)")
    if not brut:
        return None
    return email.message_from_bytes(brut).get("Message-ID")


def _importer_message(conn: imaplib.IMAP4_SSL, uid: bytes, dossier_id: int, adresses_cabinet: set[str]) -> Document:
    brut = _corps_brut(conn, uid, "")
    message = email.message_from_bytes(brut)

    expediteur = _adresse(message.get("From"))
    objet = _decoder_entete(message.get("Subject")) or None
    destinataires = _decoder_entete(message.get("To")) or ""
    message_id = message.get("Message-ID") or f"<sans-id-{uuid.uuid4()}@moncabinet.local>"
    try:
        date_message = parsedate_to_datetime(message.get("Date"))
    except (TypeError, ValueError):
        date_message = None
    if date_message is None:
        date_message = datetime.now()
    sens = "envoye" if expediteur.lower() in adresses_cabinet else "recu"

    chemin_fichier = stockage_documents.enregistrer(dossier_id, "message.eml", brut)

    return documents_repo.creer_email(
        dossier_id=dossier_id,
        sens=sens,
        expediteur=expediteur,
        destinataires=destinataires,
        objet=objet,
        date_message=date_message,
        message_id=message_id,
        chemin_fichier=chemin_fichier,
        titre=objet or "(sans objet)",
    )


def synchroniser() -> CompteRendu:
    """Parcourt les répertoires IMAP sous IMAP_PREFIXE_DOSSIERS et importe
    les messages dont le Message-ID n'est pas déjà rattaché au dossier
    correspondant. Voir l'algorithme détaillé en §5 du document de
    conception."""
    config = current_app.config
    adresses_cabinet = {a.strip().lower() for a in config["ADRESSES_CABINET"].split(",") if a.strip()}
    prefixe = config["IMAP_PREFIXE_DOSSIERS"]

    try:
        conn = imaplib.IMAP4_SSL(config["IMAP_HOST"], int(config["IMAP_PORT"]))
        conn.login(config["IMAP_USER"], config["IMAP_PASSWORD"])
    except (imaplib.IMAP4.error, OSError) as e:
        raise ErreurSynchronisation(str(e)) from e

    compte_rendu = CompteRendu()
    try:
        for nom_repertoire in _repertoires_dossiers(conn, prefixe):
            reference = _reference_depuis_nom(nom_repertoire, prefixe)
            dossier = dossiers.recuperer_par_reference(reference) if reference else None
            if dossier is None:
                raison = (
                    "Aucun dossier ne porte cette référence."
                    if reference
                    else "Nom de répertoire sans référence de dossier reconnaissable."
                )
                compte_rendu.anomalies.append(
                    AnomalieSynchronisation(nom_repertoire_imap=nom_repertoire, raison=raison)
                )
                continue

            conn.select(f'"{nom_repertoire}"', readonly=True)
            typ, data = conn.uid("search", None, "ALL")
            uids = data[0].split() if typ == "OK" and data and data[0] else []

            dossier_synchronise = DossierSynchronise(dossier_id=dossier.id, reference=dossier.reference)
            for uid in uids:
                message_id = _message_id_existant(conn, uid)
                if message_id and documents_repo.existe_email(dossier.id, message_id):
                    continue
                dossier_synchronise.documents_importes.append(
                    _importer_message(conn, uid, dossier.id, adresses_cabinet)
                )

            if dossier_synchronise.documents_importes:
                compte_rendu.dossiers_synchronises.append(dossier_synchronise)
    finally:
        conn.logout()

    return compte_rendu


# --- Lecture d'un e-mail déjà importé ---------------------------------------


def lire_message(document: Document) -> Message:
    return email.message_from_bytes(resoudre_chemin(document.chemin_fichier).read_bytes())


def corps_texte(message: Message) -> str:
    """Partie texte brut uniquement : le HTML n'est jamais rendu (pixels de
    traçage dans les images distantes, risque d'injection) — voir
    docs/phase-documents-correspondance.md §8. Le .eml brut reste
    téléchargeable pour qui a besoin du rendu complet."""
    if message.is_multipart():
        for partie in message.walk():
            if partie.get_content_type() == "text/plain" and partie.get_content_disposition() != "attachment":
                charset = partie.get_content_charset() or "utf-8"
                return partie.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    if message.get_content_type() == "text/plain":
        charset = message.get_content_charset() or "utf-8"
        return message.get_payload(decode=True).decode(charset, errors="replace")
    return ""


def pieces_jointes(message: Message) -> list[dict]:
    """Une entrée par pièce jointe, indexée dans l'ordre de parcours du
    message — l'index sert à la retrouver pour la verser au dossier (voir
    extraire_piece_jointe), sans avoir à la stocker avant que l'utilisateur
    ne le décide."""
    resultats = []
    if not message.is_multipart():
        return resultats
    for index, partie in enumerate(message.walk()):
        nom = partie.get_filename()
        if not nom:
            continue
        resultats.append(
            {
                "index": index,
                "nom": _decoder_entete(nom),
                "type_contenu": partie.get_content_type(),
                "taille": len(partie.get_payload(decode=True) or b""),
            }
        )
    return resultats


def extraire_piece_jointe(message: Message, index: int) -> tuple[str, bytes]:
    for i, partie in enumerate(message.walk()):
        if i == index:
            return _decoder_entete(partie.get_filename()), partie.get_payload(decode=True)
    raise ValueError(f"Pièce jointe introuvable à l'index {index}.")
