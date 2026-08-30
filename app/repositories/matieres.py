from psycopg.rows import class_row

from app import db
from app.modeles import Matiere


def lister(actives_seulement: bool = True) -> list[Matiere]:
    requete = "SELECT id, libelle, actif FROM matiere"
    if actives_seulement:
        requete += " WHERE actif"
    requete += " ORDER BY libelle"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Matiere)) as cur:
            cur.execute(requete)
            return cur.fetchall()


def creer(libelle: str) -> Matiere:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Matiere)) as cur:
            cur.execute(
                "INSERT INTO matiere (libelle) VALUES (%s) RETURNING id, libelle, actif",
                (libelle.strip(),),
            )
            conn.commit()
            return cur.fetchone()


def basculer_actif(matiere_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE matiere SET actif = NOT actif WHERE id = %s", (matiere_id,)
            )
            conn.commit()
