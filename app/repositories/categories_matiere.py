from psycopg.rows import class_row

from app import db
from app.modeles import CategorieMatiere


def lister(actives_seulement: bool = True) -> list[CategorieMatiere]:
    requete = "SELECT id, libelle, actif FROM categorie_matiere"
    if actives_seulement:
        requete += " WHERE actif"
    requete += " ORDER BY libelle"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(CategorieMatiere)) as cur:
            cur.execute(requete)
            return cur.fetchall()


def creer(libelle: str) -> CategorieMatiere:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(CategorieMatiere)) as cur:
            cur.execute(
                "INSERT INTO categorie_matiere (libelle) VALUES (%s) RETURNING id, libelle, actif",
                (libelle.strip(),),
            )
            conn.commit()
            return cur.fetchone()


def basculer_actif(categorie_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE categorie_matiere SET actif = NOT actif WHERE id = %s", (categorie_id,)
            )
            conn.commit()
