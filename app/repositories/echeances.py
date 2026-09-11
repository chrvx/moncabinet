from datetime import date, time

from psycopg.rows import class_row

from app import db
from app.modeles import Echeance, ModeleEcheance

_COLONNES = """
    id, dossier_id, categorie_id, libelle, date_echeance, heure_echeance,
    statut, fait_le, notes, cree_par, cree_le, modifie_par, modifie_le,
    document_id
"""


def creer(
    dossier_id: int,
    categorie_id: int,
    libelle: str,
    date_echeance: date,
    heure_echeance: time | None,
    notes: str | None,
    utilisateur_id: int,
    document_id: int | None = None,
) -> Echeance:
    """document_id rattache l'échéance au document (e-mail, pièce scannée...)
    qui l'a fait naître — voir le lien "créer une échéance" du compte rendu
    de synchronisation et de la fiche e-mail. None dans le cas courant d'une
    échéance saisie directement sur le dossier."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Echeance)) as cur:
            cur.execute(
                f"""
                INSERT INTO echeance
                    (dossier_id, categorie_id, libelle, date_echeance,
                     heure_echeance, notes, cree_par, document_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {_COLONNES}
                """,
                (dossier_id, categorie_id, libelle, date_echeance, heure_echeance, notes, utilisateur_id, document_id),
            )
            conn.commit()
            return cur.fetchone()


def modifier(
    echeance_id: int,
    categorie_id: int,
    libelle: str,
    date_echeance: date,
    heure_echeance: time | None,
    notes: str | None,
    utilisateur_id: int,
) -> Echeance:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Echeance)) as cur:
            cur.execute(
                f"""
                UPDATE echeance
                SET categorie_id = %s, libelle = %s, date_echeance = %s,
                    heure_echeance = %s, notes = %s,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                RETURNING {_COLONNES}
                """,
                (categorie_id, libelle, date_echeance, heure_echeance, notes, utilisateur_id, echeance_id),
            )
            conn.commit()
            return cur.fetchone()


def marquer_fait(echeance_id: int, utilisateur_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE echeance
                SET statut = 'fait', fait_le = now(),
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, echeance_id),
            )
            conn.commit()


def marquer_a_faire(echeance_id: int, utilisateur_id: int) -> None:
    """Inverse de marquer_fait : permet de corriger un clic accidentel."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE echeance
                SET statut = 'a_faire', fait_le = NULL,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, echeance_id),
            )
            conn.commit()


def supprimer(echeance_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM echeance WHERE id = %s", (echeance_id,))
            conn.commit()


def recuperer(echeance_id: int) -> Echeance | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Echeance)) as cur:
            cur.execute(f"SELECT {_COLONNES} FROM echeance WHERE id = %s", (echeance_id,))
            return cur.fetchone()


def lister_pour_dossier(dossier_id: int) -> list[Echeance]:
    """Triées à faire d'abord puis fait, et par date/heure croissantes au
    sein de chaque groupe."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Echeance)) as cur:
            cur.execute(
                f"""
                SELECT {_COLONNES} FROM echeance
                WHERE dossier_id = %s
                ORDER BY (statut = 'fait'), date_echeance, heure_echeance NULLS FIRST
                """,
                (dossier_id,),
            )
            return cur.fetchall()


def lister_a_venir(limite: int = 5) -> list[tuple[Echeance, str | None]]:
    """Les échéances non faites les plus proches (retard compris), tous
    dossiers ouverts confondus, avec la référence du dossier — utilisé par
    le tableau de bord d'accueil, même forme que documents.lister_recents."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.dossier_id, e.categorie_id, e.libelle,
                       e.date_echeance, e.heure_echeance, e.statut, e.fait_le,
                       e.notes, e.cree_par, e.cree_le, e.modifie_par, e.modifie_le,
                       e.document_id, d.reference
                FROM echeance e
                JOIN dossier d ON d.id = e.dossier_id
                WHERE e.statut = 'a_faire' AND d.statut = 'ouvert'
                ORDER BY e.date_echeance, e.heure_echeance NULLS FIRST
                LIMIT %s
                """,
                (limite,),
            )
            return [(Echeance(*ligne[0:14]), ligne[14]) for ligne in cur.fetchall()]


def compter_a_venir() -> int:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM echeance e
                JOIN dossier d ON d.id = e.dossier_id
                WHERE e.statut = 'a_faire' AND d.statut = 'ouvert'
                """
            )
            return cur.fetchone()[0]


# --- Modèles d'échéance (catalogue par matière) -----------------------------


def lister_modeles_pour_matiere(matiere_id: int) -> list[ModeleEcheance]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ModeleEcheance)) as cur:
            cur.execute(
                """
                SELECT id, matiere_id, libelle, categorie_id, delai_jours, actif
                FROM matiere_modele_echeance
                WHERE matiere_id = %s AND actif
                ORDER BY delai_jours, libelle
                """,
                (matiere_id,),
            )
            return cur.fetchall()


def lister_tous_modeles() -> list[tuple[ModeleEcheance, str]]:
    """Le catalogue complet (actifs et inactifs), avec le libellé de la
    matière — utilisé par l'écran d'administration parametres/."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT me.id, me.matiere_id, me.libelle, me.categorie_id,
                       me.delai_jours, me.actif, m.libelle
                FROM matiere_modele_echeance me
                JOIN matiere m ON m.id = me.matiere_id
                ORDER BY m.libelle, me.delai_jours, me.libelle
                """
            )
            return [(ModeleEcheance(*ligne[0:6]), ligne[6]) for ligne in cur.fetchall()]


def creer_modele(matiere_id: int, libelle: str, categorie_id: int, delai_jours: int) -> ModeleEcheance:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ModeleEcheance)) as cur:
            cur.execute(
                """
                INSERT INTO matiere_modele_echeance (matiere_id, libelle, categorie_id, delai_jours)
                VALUES (%s, %s, %s, %s)
                RETURNING id, matiere_id, libelle, categorie_id, delai_jours, actif
                """,
                (matiere_id, libelle.strip(), categorie_id, delai_jours),
            )
            conn.commit()
            return cur.fetchone()


def basculer_actif_modele(modele_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE matiere_modele_echeance SET actif = NOT actif WHERE id = %s",
                (modele_id,),
            )
            conn.commit()


def lister_modeles_non_instancies(dossier_id: int, matiere_id: int) -> list[ModeleEcheance]:
    """Modèles actifs de la matière du dossier dont le libellé n'a pas déjà
    été instancié comme échéance sur ce dossier — évite de re-suggérer une
    échéance déjà ajoutée. Comparaison sur libelle plutôt que sur une clé
    étrangère : une fois instanciée, une échéance est un enregistrement
    ordinaire, librement modifiable, sans lien conservé vers son modèle
    d'origine."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ModeleEcheance)) as cur:
            cur.execute(
                """
                SELECT id, matiere_id, libelle, categorie_id, delai_jours, actif
                FROM matiere_modele_echeance
                WHERE matiere_id = %s AND actif
                    AND libelle NOT IN (
                        SELECT libelle FROM echeance WHERE dossier_id = %s
                    )
                ORDER BY delai_jours, libelle
                """,
                (matiere_id, dossier_id),
            )
            return cur.fetchall()
