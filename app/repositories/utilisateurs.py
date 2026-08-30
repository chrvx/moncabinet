from psycopg.rows import class_row

from app import db
from app.modeles import Utilisateur

# Chaque fonction ici correspond à une requête SQL précise. C'est la seule
# partie du code qui écrit du SQL pour les utilisateurs : les routes ne font
# jamais de requête directement, elles appellent ces fonctions.


def recuperer_par_id(utilisateur_id: int) -> Utilisateur | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Utilisateur)) as cur:
            cur.execute(
                """
                SELECT id, nom, mot_de_passe_hash, role, actif
                FROM utilisateur
                WHERE id = %s
                """,
                (utilisateur_id,),
            )
            return cur.fetchone()


def recuperer_par_nom(nom: str) -> Utilisateur | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Utilisateur)) as cur:
            cur.execute(
                """
                SELECT id, nom, mot_de_passe_hash, role, actif
                FROM utilisateur
                WHERE nom = %s
                """,
                (nom,),
            )
            return cur.fetchone()


def creer(nom: str, mot_de_passe_hash: str, role: str) -> Utilisateur:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Utilisateur)) as cur:
            cur.execute(
                """
                INSERT INTO utilisateur (nom, mot_de_passe_hash, role)
                VALUES (%s, %s, %s)
                RETURNING id, nom, mot_de_passe_hash, role, actif
                """,
                (nom, mot_de_passe_hash, role),
            )
            conn.commit()
            return cur.fetchone()
