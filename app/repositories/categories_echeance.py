from psycopg.rows import class_row

from app import db
from app.modeles import CategorieEcheance


def lister(actives_seulement: bool = True) -> list[CategorieEcheance]:
    requete = "SELECT id, libelle, actif FROM categorie_echeance"
    if actives_seulement:
        requete += " WHERE actif"
    requete += " ORDER BY libelle"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(CategorieEcheance)) as cur:
            cur.execute(requete)
            return cur.fetchall()


def creer(libelle: str) -> CategorieEcheance:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(CategorieEcheance)) as cur:
            cur.execute(
                "INSERT INTO categorie_echeance (libelle) VALUES (%s) RETURNING id, libelle, actif",
                (libelle.strip(),),
            )
            conn.commit()
            return cur.fetchone()


def basculer_actif(categorie_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE categorie_echeance SET actif = NOT actif WHERE id = %s", (categorie_id,)
            )
            conn.commit()
