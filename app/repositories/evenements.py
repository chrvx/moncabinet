from datetime import date

from psycopg.rows import class_row

from app import db
from app.modeles import Evenement, EvenementHistorique

_COLONNES = """
    id, dossier_id, type_evenement_id, date_evenement, duree_minutes, contenu,
    echeance_id, document_id, annule_le, annule_par, motif_annulation,
    cree_par, cree_le, modifie_par, modifie_le
"""


def _historiser(cur, evenement_id: int, utilisateur_id: int) -> None:
    """Copie l'état actuel de la ligne evenement dans evenement_historique
    juste avant qu'une des quatre fonctions d'écriture ci-dessous ne
    l'écrase — appelée dans la même transaction que l'UPDATE qui suit.
    modifie_par identifie qui produit ce changement (modifie_le est fixé
    par le DEFAULT now() de la table)."""
    cur.execute(
        """
        INSERT INTO evenement_historique
            (evenement_id, dossier_id, type_evenement_id, date_evenement,
             duree_minutes, contenu, annule_le, annule_par, motif_annulation,
             modifie_par)
        SELECT id, dossier_id, type_evenement_id, date_evenement,
               duree_minutes, contenu, annule_le, annule_par, motif_annulation,
               %s
        FROM evenement WHERE id = %s
        """,
        (utilisateur_id, evenement_id),
    )


def creer(
    dossier_id: int,
    type_evenement_id: int,
    date_evenement: date,
    duree_minutes: int | None,
    contenu: str,
    utilisateur_id: int,
    echeance_id: int | None = None,
) -> Evenement:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Evenement)) as cur:
            cur.execute(
                f"""
                INSERT INTO evenement
                    (dossier_id, type_evenement_id, date_evenement,
                     duree_minutes, contenu, echeance_id, cree_par)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING {_COLONNES}
                """,
                (dossier_id, type_evenement_id, date_evenement, duree_minutes, contenu, echeance_id, utilisateur_id),
            )
            conn.commit()
            return cur.fetchone()


def modifier(
    evenement_id: int,
    type_evenement_id: int,
    date_evenement: date,
    duree_minutes: int | None,
    contenu: str,
    utilisateur_id: int,
) -> Evenement:
    """Corrige le contenu/type/date/durée ; ne touche jamais dossier_id
    (voir changer_dossier pour ça, gatée par un rôle différent)."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Evenement)) as cur:
            _historiser(cur, evenement_id, utilisateur_id)
            cur.execute(
                f"""
                UPDATE evenement
                SET type_evenement_id = %s, date_evenement = %s,
                    duree_minutes = %s, contenu = %s,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                RETURNING {_COLONNES}
                """,
                (type_evenement_id, date_evenement, duree_minutes, contenu, utilisateur_id, evenement_id),
            )
            conn.commit()
            return cur.fetchone()


def changer_dossier(evenement_id: int, nouveau_dossier_id: int, utilisateur_id: int) -> Evenement:
    """Correction d'un événement saisi sur le mauvais dossier — fonction
    séparée de modifier() car sa route est réservée aux comptes
    avocat/collaborateur, contrairement au reste."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Evenement)) as cur:
            _historiser(cur, evenement_id, utilisateur_id)
            cur.execute(
                f"""
                UPDATE evenement
                SET dossier_id = %s, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                RETURNING {_COLONNES}
                """,
                (nouveau_dossier_id, utilisateur_id, evenement_id),
            )
            conn.commit()
            return cur.fetchone()


def annuler(evenement_id: int, utilisateur_id: int, motif: str | None = None) -> None:
    """Annulation réversible (voir reactiver) : l'événement reste en base
    et consultable, mais sort de l'affichage par défaut."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            _historiser(cur, evenement_id, utilisateur_id)
            cur.execute(
                """
                UPDATE evenement
                SET annule_le = now(), annule_par = %s, motif_annulation = %s,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, motif, utilisateur_id, evenement_id),
            )
            conn.commit()


def reactiver(evenement_id: int, utilisateur_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            _historiser(cur, evenement_id, utilisateur_id)
            cur.execute(
                """
                UPDATE evenement
                SET annule_le = NULL, annule_par = NULL, motif_annulation = NULL,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, evenement_id),
            )
            conn.commit()


def recuperer(evenement_id: int) -> Evenement | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Evenement)) as cur:
            cur.execute(f"SELECT {_COLONNES} FROM evenement WHERE id = %s", (evenement_id,))
            return cur.fetchone()


def lister_pour_dossier(dossier_id: int, inclure_annules: bool = False) -> list[Evenement]:
    """Triées par date décroissante : contrairement à
    echeances.lister_pour_dossier (tourné vers l'avenir), evenement est une
    trace du passé, la plus récente d'abord."""
    requete = f"SELECT {_COLONNES} FROM evenement WHERE dossier_id = %s"
    if not inclure_annules:
        requete += " AND annule_le IS NULL"
    requete += " ORDER BY date_evenement DESC, id DESC"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Evenement)) as cur:
            cur.execute(requete, (dossier_id,))
            return cur.fetchall()


def lister_historique(evenement_id: int) -> list[EvenementHistorique]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(EvenementHistorique)) as cur:
            cur.execute(
                """
                SELECT id, evenement_id, dossier_id, type_evenement_id,
                       date_evenement, duree_minutes, contenu, annule_le,
                       annule_par, motif_annulation, modifie_par, modifie_le
                FROM evenement_historique
                WHERE evenement_id = %s
                ORDER BY modifie_le DESC
                """,
                (evenement_id,),
            )
            return cur.fetchall()
