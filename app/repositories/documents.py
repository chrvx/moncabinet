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
