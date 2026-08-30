from psycopg.rows import class_row

from app import db
from app.modeles import RoleContact
from app.repositories import reference


class RegleRoleViolee(ValueError):
    """Levée quand dossier_id ou contact_lie_id ne respecte pas la règle
    (obligatoire/optionnel/interdit) définie sur le type de rôle."""


def _valider_regle(regle: str, valeur, nom_champ: str) -> None:
    if regle == "obligatoire" and valeur is None:
        raise RegleRoleViolee(f"Ce rôle exige un {nom_champ}.")
    if regle == "interdit" and valeur is not None:
        raise RegleRoleViolee(f"Ce rôle n'admet pas de {nom_champ}.")


def _valider_compatibilite(contact_id: int, dossier_id: int | None, type_role) -> None:
    """Un même contact peut cumuler plusieurs rôles sur un même dossier
    (voir attribuer_role), sauf combinaisons explicitement incompatibles :
    un rôle "exclusif" (avocat, enfant) n'admet aucun autre rôle pour ce
    contact sur ce dossier, et certaines paires de rôles sont incompatibles
    entre elles (client / adversaire) même si aucune des deux n'est
    exclusive. Sans dossier, il n'y a pas de cumul à vérifier : chaque rôle
    hors dossier est indépendant."""
    if dossier_id is None:
        return

    roles_existants = [
        r for r in lister_roles(contact_id) if r.dossier_id == dossier_id
    ]
    if not roles_existants:
        return

    if type_role.exclusif:
        raise RegleRoleViolee(
            f"Le rôle « {type_role.libelle} » ne peut pas être cumulé avec un "
            "autre rôle pour ce contact sur ce dossier."
        )

    incompatibles = reference.lister_roles_incompatibles(type_role.id)
    for role_existant in roles_existants:
        type_existant = reference.recuperer_type_role(role_existant.type_role_id)
        if type_existant.exclusif or type_existant.id in incompatibles:
            raise RegleRoleViolee(
                f"Le rôle « {type_role.libelle} » ne peut pas être cumulé avec "
                f"« {type_existant.libelle} » pour ce contact sur ce dossier."
            )


def attribuer_role(
    contact_id: int,
    type_role_id: int,
    utilisateur_id: int,
    dossier_id: int | None = None,
    contact_lie_id: int | None = None,
) -> RoleContact:
    """Attribue un rôle à un contact, en vérifiant d'abord que dossier_id et
    contact_lie_id respectent la règle du type de rôle (voir la table
    type_role) — la règle est une donnée, pas une suite de if/elif sur le
    libellé du rôle, pour rester valable même quand vous ajouterez de
    nouveaux rôles."""
    type_role = reference.recuperer_type_role(type_role_id)
    if type_role is None:
        raise ValueError(f"Type de rôle inconnu : {type_role_id}")

    _valider_regle(type_role.dossier_regle, dossier_id, "dossier")
    _valider_regle(type_role.contact_lie_regle, contact_lie_id, "contact lié")
    _valider_compatibilite(contact_id, dossier_id, type_role)

    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(RoleContact)) as cur:
            cur.execute(
                """
                INSERT INTO role_contact
                    (contact_id, type_role_id, dossier_id, contact_lie_id, cree_par)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, contact_id, type_role_id, dossier_id,
                          contact_lie_id, cree_par, cree_le
                """,
                (contact_id, type_role_id, dossier_id, contact_lie_id, utilisateur_id),
            )
            conn.commit()
            return cur.fetchone()


def lister_roles(contact_id: int) -> list[RoleContact]:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(RoleContact)) as cur:
            cur.execute(
                """
                SELECT id, contact_id, type_role_id, dossier_id,
                       contact_lie_id, cree_par, cree_le
                FROM role_contact
                WHERE contact_id = %s
                ORDER BY cree_le
                """,
                (contact_id,),
            )
            return cur.fetchall()


def retirer_role(role_contact_id: int) -> None:
    """Retire un rôle attribué. Refuse si c'est le dernier rôle "client"
    d'un dossier : un dossier n'existe jamais sans client (cf. la
    discussion de conception initiale — un dossier sans client n'a pas de
    sens, mieux vaut l'empêcher ici qu'ailleurs)."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rc.dossier_id, tr.libelle
                FROM role_contact rc
                JOIN type_role tr ON tr.id = rc.type_role_id
                WHERE rc.id = %s
                """,
                (role_contact_id,),
            )
            ligne = cur.fetchone()
            if ligne is None:
                return
            dossier_id, libelle_role = ligne

            if libelle_role == "client" and dossier_id is not None:
                cur.execute(
                    """
                    SELECT count(*) FROM role_contact rc
                    JOIN type_role tr ON tr.id = rc.type_role_id
                    WHERE rc.dossier_id = %s AND tr.libelle = 'client'
                    """,
                    (dossier_id,),
                )
                if cur.fetchone()[0] <= 1:
                    raise RegleRoleViolee(
                        "Impossible de retirer le dernier client d'un dossier."
                    )

            cur.execute("DELETE FROM role_contact WHERE id = %s", (role_contact_id,))
            conn.commit()
