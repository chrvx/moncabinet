from datetime import date, datetime

from psycopg.rows import class_row

from app import db
from app.modeles import Document, DocumentEmail, DocumentGenere, DocumentListe, DocumentPiece

_COLONNES_DOCUMENT = """
    id, dossier_id, type_document, titre, chemin_fichier,
    document_origine_id, cree_par, cree_le
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
) -> Document:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(
                f"""
                INSERT INTO document
                    (dossier_id, type_document, titre, chemin_fichier, document_origine_id, cree_par)
                VALUES (%s, 'depose', %s, %s, %s, %s)
                RETURNING {_COLONNES_DOCUMENT}
                """,
                (dossier_id, titre, chemin_fichier, document_origine_id, utilisateur_id),
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
    docs/phase-documents-correspondance.md §4."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DocumentListe)) as cur:
            cur.execute(
                """
                SELECT
                    d.id, d.dossier_id, d.type_document, d.titre, d.chemin_fichier, d.cree_le,
                    COALESCE(de.date_message, dp.date_transmission::timestamptz, d.cree_le) AS date_tri,
                    (dp.document_id IS NOT NULL) AS est_piece,
                    dp.numero_piece
                FROM document d
                LEFT JOIN document_email de ON de.document_id = d.id
                LEFT JOIN document_piece dp ON dp.document_id = d.id
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
                       d.cree_le, d.cree_le AS date_tri, false AS est_piece,
                       NULL::text AS numero_piece, dos.reference
                FROM document d
                JOIN dossier dos ON dos.id = d.dossier_id
                WHERE d.type_document = 'genere'
                ORDER BY d.cree_le DESC
                LIMIT %s
                """,
                (limite,),
            )
            return [(DocumentListe(*ligne[0:9]), ligne[9]) for ligne in cur.fetchall()]


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
