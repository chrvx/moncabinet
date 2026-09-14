from datetime import date, datetime

from psycopg.rows import class_row

from app import db
from app.modeles import Document, DocumentEmail, DocumentGenere, DocumentListe, DocumentPiece, PieceListe

_COLONNES_DOCUMENT = """
    id, dossier_id, type_document, titre, chemin_fichier,
    document_origine_id, cree_par, cree_le, notes
"""

_CTE_NOM_CONTACT = """
    COALESCE(
        NULLIF(trim(COALESCE(pp.prenom || ' ', '') || pp.nom), ''),
        pm.raison_sociale
    )
"""


def creer_genere(
    dossier_id: int,
    modele_slug: str,
    titre: str,
    chemin_fichier: str,
    chemin_typ: str,
    utilisateur_id: int,
) -> Document:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(
                f"""
                INSERT INTO document (dossier_id, type_document, titre, chemin_fichier, cree_par)
                VALUES (%s, 'genere', %s, %s, %s)
                RETURNING {_COLONNES_DOCUMENT}
                """,
                (dossier_id, titre, chemin_fichier, utilisateur_id),
            )
            document = cur.fetchone()
            cur.execute(
                """
                INSERT INTO document_genere (document_id, modele_slug, chemin_typ)
                VALUES (%s, %s, %s)
                """,
                (document.id, modele_slug, chemin_typ),
            )
            conn.commit()
            return document


def creer_depose(
    dossier_id: int,
    titre: str,
    chemin_fichier: str,
    utilisateur_id: int,
    document_origine_id: int | None = None,
    notes: str | None = None,
) -> Document:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(
                f"""
                INSERT INTO document
                    (dossier_id, type_document, titre, chemin_fichier, document_origine_id, cree_par, notes)
                VALUES (%s, 'depose', %s, %s, %s, %s, %s)
                RETURNING {_COLONNES_DOCUMENT}
                """,
                (dossier_id, titre, chemin_fichier, document_origine_id, utilisateur_id, notes),
            )
            conn.commit()
            return cur.fetchone()


def creer_email(
    dossier_id: int,
    sens: str,
    expediteur: str,
    destinataires: str,
    objet: str | None,
    date_message: datetime,
    message_id: str,
    chemin_fichier: str,
    titre: str,
) -> Document:
    """Importé par la synchronisation IMAP (app/services/messagerie.py) —
    pas d'utilisateur_id : le message vient de la boîte, pas d'une saisie."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(
                f"""
                INSERT INTO document (dossier_id, type_document, titre, chemin_fichier)
                VALUES (%s, 'email', %s, %s)
                RETURNING {_COLONNES_DOCUMENT}
                """,
                (dossier_id, titre, chemin_fichier),
            )
            document = cur.fetchone()
            cur.execute(
                """
                INSERT INTO document_email
                    (document_id, sens, expediteur, destinataires, objet, date_message, message_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (document.id, sens, expediteur, destinataires, objet, date_message, message_id),
            )
            conn.commit()
            return document


def existe_email(dossier_id: int, message_id: str) -> bool:
    """Contrôle d'unicité par dossier (pas global : un même message peut
    légitimement concerner deux dossiers) — voir migration 0021."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM document_email de
                JOIN document d ON d.id = de.document_id
                WHERE d.dossier_id = %s AND de.message_id = %s
                """,
                (dossier_id, message_id),
            )
            return cur.fetchone() is not None


def recuperer_email(document_id: int) -> DocumentEmail | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentEmail)) as cur:
            cur.execute(
                """
                SELECT document_id, sens, expediteur, destinataires, objet, date_message, message_id
                FROM document_email WHERE document_id = %s
                """,
                (document_id,),
            )
            return cur.fetchone()


def recuperer(document_id: int) -> Document | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(f"SELECT {_COLONNES_DOCUMENT} FROM document WHERE id = %s", (document_id,))
            return cur.fetchone()


def modifier_notes(document_id: int, notes: str | None) -> Document:
    """Écran de modification d'un document (migration 0026) : seule la note
    libre est éditable après coup, quel que soit le type_document — voir
    docs/phase-documents-correspondance.md §3."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(
                f"UPDATE document SET notes = %s WHERE id = %s RETURNING {_COLONNES_DOCUMENT}",
                (notes, document_id),
            )
            conn.commit()
            return cur.fetchone()


def recuperer_genere(document_id: int) -> DocumentGenere | None:
    """Champs propres à un document généré (modèle, .typ fusionné) — voir
    app/blueprints/documents/routes.py::telecharger_typ."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentGenere)) as cur:
            cur.execute(
                "SELECT document_id, modele_slug, chemin_typ FROM document_genere WHERE document_id = %s",
                (document_id,),
            )
            return cur.fetchone()


def recuperer_piece(document_id: int) -> DocumentPiece | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentPiece)) as cur:
            cur.execute(
                """
                SELECT document_id, numero_piece, contact_provenance_id, date_transmission, utilisee
                FROM document_piece WHERE document_id = %s
                """,
                (document_id,),
            )
            return cur.fetchone()


def marquer_piece(
    document_id: int,
    contact_provenance_id: int,
    date_transmission: date | None = None,
    numero_piece: str | None = None,
    utilisee: bool = False,
) -> DocumentPiece:
    """Attache la caractéristique "pièce" à un document existant, quel que
    soit son type — voir docs/phase-documents-correspondance.md §2.3."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentPiece)) as cur:
            cur.execute(
                """
                INSERT INTO document_piece
                    (document_id, numero_piece, contact_provenance_id, date_transmission, utilisee)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING document_id, numero_piece, contact_provenance_id, date_transmission, utilisee
                """,
                (document_id, numero_piece, contact_provenance_id, date_transmission, utilisee),
            )
            conn.commit()
            return cur.fetchone()


def lister_pour_dossier(dossier_id: int) -> list[DocumentListe]:
    """Tous les documents du dossier, tous types confondus, triés sur
    date_tri plutôt que sur cree_le (qui n'est que la date d'import) — voir
    docs/phase-documents-correspondance.md §4. Alimente dossiers.chronologie,
    qui n'a pas besoin des liens croisés Documents/Messagerie (§7.3) : les
    champs correspondants sont laissés à leur valeur neutre."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentListe)) as cur:
            cur.execute(
                """
                SELECT
                    d.id, d.dossier_id, d.type_document, d.titre, d.chemin_fichier, d.cree_le,
                    COALESCE(de.date_message, dp.date_transmission::timestamptz, d.cree_le) AS date_tri,
                    (dp.document_id IS NOT NULL) AS est_piece,
                    dp.numero_piece,
                    d.notes,
                    d.document_origine_id,
                    NULL::timestamptz AS origine_date_message,
                    NULL::text AS origine_expediteur,
                    0 AS nb_versements
                FROM document d
                LEFT JOIN document_email de ON de.document_id = d.id
                LEFT JOIN document_piece dp ON dp.document_id = d.id
                WHERE d.dossier_id = %s
                ORDER BY date_tri DESC
                """,
                (dossier_id,),
            )
            return cur.fetchall()


def lister_documents_pour_dossier(dossier_id: int) -> list[DocumentListe]:
    """Documents hors e-mails, pour l'onglet Documents de la fiche dossier
    (§4, §7.1). Résout la provenance quand le document vient d'une pièce
    jointe versée (document_origine_id → document_email), pour le lien
    croisé vers Messagerie décrit en §7.3."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentListe)) as cur:
            cur.execute(
                """
                SELECT
                    d.id, d.dossier_id, d.type_document, d.titre, d.chemin_fichier, d.cree_le,
                    COALESCE(dp.date_transmission::timestamptz, d.cree_le) AS date_tri,
                    (dp.document_id IS NOT NULL) AS est_piece,
                    dp.numero_piece,
                    d.notes,
                    d.document_origine_id,
                    origine.date_message AS origine_date_message,
                    origine.expediteur AS origine_expediteur,
                    0 AS nb_versements
                FROM document d
                LEFT JOIN document_piece dp ON dp.document_id = d.id
                LEFT JOIN document_email origine ON origine.document_id = d.document_origine_id
                WHERE d.dossier_id = %s AND d.type_document <> 'email'
                ORDER BY date_tri DESC
                """,
                (dossier_id,),
            )
            return cur.fetchall()


def lister_emails_pour_dossier(dossier_id: int) -> list[DocumentListe]:
    """E-mails du dossier, pour l'onglet Messagerie de la fiche dossier (§4,
    §7.1). nb_versements compte les documents dont document_origine_id
    pointe vers cet e-mail, pour signaler qu'une pièce jointe a déjà été
    versée (§7.3) et éviter un double versement."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentListe)) as cur:
            cur.execute(
                """
                SELECT
                    d.id, d.dossier_id, d.type_document, d.titre, d.chemin_fichier, d.cree_le,
                    de.date_message AS date_tri,
                    (dp.document_id IS NOT NULL) AS est_piece,
                    dp.numero_piece,
                    d.notes,
                    d.document_origine_id,
                    NULL::timestamptz AS origine_date_message,
                    NULL::text AS origine_expediteur,
                    COALESCE(versements.nb, 0) AS nb_versements
                FROM document d
                JOIN document_email de ON de.document_id = d.id
                LEFT JOIN document_piece dp ON dp.document_id = d.id
                LEFT JOIN (
                    SELECT document_origine_id, count(*) AS nb
                    FROM document
                    WHERE document_origine_id IS NOT NULL
                    GROUP BY document_origine_id
                ) versements ON versements.document_origine_id = d.id
                WHERE d.dossier_id = %s
                ORDER BY date_tri DESC
                """,
                (dossier_id,),
            )
            return cur.fetchall()


def lister_pieces_pour_dossier(dossier_id: int) -> list[PieceListe]:
    """Page Pièces (§7.2) : tous les documents marqués comme pièce, tous
    types confondus (un e-mail produit comme pièce doit y figurer au même
    titre qu'un document déposé)."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(PieceListe)) as cur:
            cur.execute(
                f"""
                SELECT
                    d.id, d.dossier_id, d.type_document, d.titre, d.chemin_fichier,
                    COALESCE(de.date_message, dp.date_transmission::timestamptz, d.cree_le) AS date_tri,
                    dp.numero_piece, dp.contact_provenance_id,
                    {_CTE_NOM_CONTACT} AS nom_contact_provenance,
                    dp.date_transmission, dp.utilisee, d.notes
                FROM document d
                JOIN document_piece dp ON dp.document_id = d.id
                LEFT JOIN document_email de ON de.document_id = d.id
                LEFT JOIN personne_physique pp ON pp.contact_id = dp.contact_provenance_id
                LEFT JOIN personne_morale pm ON pm.contact_id = dp.contact_provenance_id
                WHERE d.dossier_id = %s
                ORDER BY date_tri DESC
                """,
                (dossier_id,),
            )
            return cur.fetchall()


def lister_recents(limite: int = 5) -> list[tuple[DocumentListe, str | None]]:
    """Les derniers documents générés, tous dossiers confondus, avec la
    référence du dossier concerné (None si le dossier est encore en
    brouillon) — utilisé par le tableau de bord d'accueil. Limité aux
    documents générés : le tableau de bord parle de "documents générés",
    pas des e-mails ou fichiers déposés."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.dossier_id, d.type_document, d.titre, d.chemin_fichier,
                       d.cree_le, d.notes, dos.reference
                FROM document d
                JOIN dossier dos ON dos.id = d.dossier_id
                WHERE d.type_document = 'genere'
                ORDER BY d.cree_le DESC
                LIMIT %s
                """,
                (limite,),
            )
            return [
                (
                    DocumentListe(
                        id=ligne[0],
                        dossier_id=ligne[1],
                        type_document=ligne[2],
                        titre=ligne[3],
                        chemin_fichier=ligne[4],
                        cree_le=ligne[5],
                        date_tri=ligne[5],
                        est_piece=False,
                        numero_piece=None,
                        notes=ligne[6],
                        document_origine_id=None,
                        origine_date_message=None,
                        origine_expediteur=None,
                        nb_versements=0,
                    ),
                    ligne[7],
                )
                for ligne in cur.fetchall()
            ]


def compter_ce_mois() -> int:
    """Documents générés ce mois-ci, pour le tableau de bord — mêmes
    réserves que lister_recents sur le périmètre "généré"."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM document
                WHERE type_document = 'genere' AND cree_le >= date_trunc('month', now())
                """
            )
            return cur.fetchone()[0]
