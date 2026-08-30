from psycopg.rows import class_row

from app import db
from app.modeles import Barreau, Civilite, Departement, Pays, TypeRole

# Tables de référence : lecture seule côté application (leur contenu est
# fixé par les migrations, pas par les utilisateurs de l'application) — à
# l'exception de BARREAU, gérée depuis l'écran d'administration
# parametres.liste_barreaux (voir les fonctions creer_barreau/
# basculer_actif_barreau ci-dessous).


def lister_pays() -> list[Pays]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Pays)) as cur:
            cur.execute(
                """
                SELECT code_iso, libelle, gentile_masculin, gentile_feminin
                FROM pays
                ORDER BY libelle
                """
            )
            return cur.fetchall()


def lister_departements() -> list[Departement]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Departement)) as cur:
            cur.execute("SELECT code, libelle FROM departement ORDER BY code")
            return cur.fetchall()


def lister_civilites() -> list[Civilite]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Civilite)) as cur:
            cur.execute("SELECT code, libelle, abreviation FROM civilite ORDER BY code")
            return cur.fetchall()


def lister_types_role() -> list[TypeRole]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(TypeRole)) as cur:
            cur.execute(
                """
                SELECT id, libelle, dossier_regle, contact_lie_regle, exclusif
                FROM type_role
                ORDER BY id
                """
            )
            return cur.fetchall()


def recuperer_type_role(type_role_id: int) -> TypeRole | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(TypeRole)) as cur:
            cur.execute(
                """
                SELECT id, libelle, dossier_regle, contact_lie_regle, exclusif
                FROM type_role
                WHERE id = %s
                """,
                (type_role_id,),
            )
            return cur.fetchone()


def lister_barreaux(actifs_seulement: bool = True) -> list[Barreau]:
    requete = "SELECT id, libelle, actif FROM barreau"
    if actifs_seulement:
        requete += " WHERE actif"
    requete += " ORDER BY libelle"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Barreau)) as cur:
            cur.execute(requete)
            return cur.fetchall()


def creer_barreau(libelle: str) -> Barreau:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Barreau)) as cur:
            cur.execute(
                "INSERT INTO barreau (libelle) VALUES (%s) RETURNING id, libelle, actif",
                (libelle.strip(),),
            )
            conn.commit()
            return cur.fetchone()


def basculer_actif_barreau(barreau_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE barreau SET actif = NOT actif WHERE id = %s", (barreau_id,)
            )
            conn.commit()


def lister_roles_incompatibles(type_role_id: int) -> set[int]:
    """Ids des types de rôle explicitement incompatibles avec celui-ci
    (ex: client / adversaire) — voir aussi TypeRole.exclusif pour
    l'incompatibilité totale (avocat, enfant), qui ne passe pas par cette
    table car elle vise tous les rôles, pas des paires spécifiques."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT type_role_id_2 FROM type_role_incompatible WHERE type_role_id_1 = %s
                UNION
                SELECT type_role_id_1 FROM type_role_incompatible WHERE type_role_id_2 = %s
                """,
                (type_role_id, type_role_id),
            )
            return {ligne[0] for ligne in cur.fetchall()}
