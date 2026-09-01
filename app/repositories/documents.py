from psycopg.rows import class_row

from app import db
from app.modeles import DossierDocument


def creer(
    dossier_id: int,
    modele_slug: str,
    titre: str,
    chemin_pdf: str,
    chemin_typ: str,
    utilisateur_id: int,
) -> DossierDocument:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DossierDocument)) as cur:
            cur.execute(
                """
                INSERT INTO dossier_document
                    (dossier_id, modele_slug, titre, chemin_pdf, chemin_typ, cree_par)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, dossier_id, modele_slug, titre, chemin_pdf, chemin_typ,
                          cree_par, cree_le
                """,
                (dossier_id, modele_slug, titre, chemin_pdf, chemin_typ, utilisateur_id),
            )
            conn.commit()
            return cur.fetchone()


def recuperer(document_id: int) -> DossierDocument | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DossierDocument)) as cur:
            cur.execute(
                """
                SELECT id, dossier_id, modele_slug, titre, chemin_pdf, chemin_typ,
                       cree_par, cree_le
                FROM dossier_document
                WHERE id = %s
                """,
                (document_id,),
            )
            return cur.fetchone()


def lister_pour_dossier(dossier_id: int) -> list[DossierDocument]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(DossierDocument)) as cur:
            cur.execute(
                """
                SELECT id, dossier_id, modele_slug, titre, chemin_pdf, chemin_typ,
                       cree_par, cree_le
                FROM dossier_document
                WHERE dossier_id = %s
                ORDER BY cree_le DESC
                """,
                (dossier_id,),
            )
            return cur.fetchall()


def lister_recents(limite: int = 5) -> list[tuple[DossierDocument, str | None]]:
    """Les derniers documents générés, tous dossiers confondus, avec la
    référence du dossier concerné (None si le dossier est encore en
    brouillon) — utilisé par le tableau de bord d'accueil."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dd.id, dd.dossier_id, dd.modele_slug, dd.titre,
                       dd.chemin_pdf, dd.chemin_typ, dd.cree_par, dd.cree_le,
                       d.reference
                FROM dossier_document dd
                JOIN dossier d ON d.id = dd.dossier_id
                ORDER BY dd.cree_le DESC
                LIMIT %s
                """,
                (limite,),
            )
            return [
                (DossierDocument(*ligne[0:8]), ligne[8]) for ligne in cur.fetchall()
            ]


def compter_ce_mois() -> int:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM dossier_document
                WHERE cree_le >= date_trunc('month', now())
                """
            )
            return cur.fetchone()[0]
