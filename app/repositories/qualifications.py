from psycopg.rows import class_row

from app import db
from app.modeles import Avocat, CommissaireJustice, Notaire, ResultatRecherche

# Qualification professionnelle d'un contact personne physique déjà
# existant (avocat, notaire, commissaire de justice) — voir
# migrations/0014.cree-tables-qualification-professionnelle.sql. Ces
# fonctions ne créent jamais le contact/personne_physique sous-jacent.
#
# Les trois professions sont mutuellement exclusives (table
# qualification_professionnelle, contrainte UNIQUE(contact_id)) :
# _basculer_qualification supprime la qualification existante si elle
# correspond à une autre profession (la suppression de
# qualification_professionnelle entraîne, par ON DELETE CASCADE, celle de
# la ligne avocat/notaire/commissaire_justice associée) avant d'en établir
# une nouvelle. Si le contact a déjà la même profession, sa ligne
# qualification_professionnelle est conservée telle quelle, pour ne pas
# perdre cree_par/cree_le sur une simple mise à jour.


def _basculer_qualification(cur, contact_id: int, profession: str) -> None:
    cur.execute(
        "SELECT profession FROM qualification_professionnelle WHERE contact_id = %s",
        (contact_id,),
    )
    ligne = cur.fetchone()
    if ligne is not None and ligne[0] != profession:
        cur.execute(
            "DELETE FROM qualification_professionnelle WHERE contact_id = %s",
            (contact_id,),
        )
        ligne = None
    if ligne is None:
        cur.execute(
            "INSERT INTO qualification_professionnelle (contact_id, profession) VALUES (%s, %s)",
            (contact_id, profession),
        )


def recuperer_avocat(contact_id: int) -> Avocat | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Avocat)) as cur:
            cur.execute(
                """
                SELECT contact_id, barreau_id, cabinet_id, code_cnbf,
                       cree_par, cree_le, modifie_par, modifie_le
                FROM avocat
                WHERE contact_id = %s
                """,
                (contact_id,),
            )
            return cur.fetchone()


def recuperer_avocat_par_code_cnbf(code_cnbf: str) -> Avocat | None:
    """Rapproche un avocat déjà enregistré par son numéro CNBF (identifiant
    stable et unique de l'annuaire national) — sert de clé de détection de
    doublons à l'import (voir app/services/annuaire_avocats.py), à la place
    d'un matching approximatif sur le nom et le prénom."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Avocat)) as cur:
            cur.execute(
                """
                SELECT contact_id, barreau_id, cabinet_id, code_cnbf,
                       cree_par, cree_le, modifie_par, modifie_le
                FROM avocat
                WHERE code_cnbf = %s
                """,
                (code_cnbf,),
            )
            return cur.fetchone()


def enregistrer_avocat(
    contact_id: int,
    utilisateur_id: int,
    barreau_id: int | None = None,
    cabinet_id: int | None = None,
    code_cnbf: str | None = None,
) -> Avocat:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            _basculer_qualification(cur, contact_id, "avocat")
            cur.execute(
                """
                INSERT INTO avocat (contact_id, barreau_id, cabinet_id, code_cnbf, cree_par)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (contact_id) DO UPDATE
                    SET barreau_id = EXCLUDED.barreau_id,
                        cabinet_id = EXCLUDED.cabinet_id,
                        code_cnbf = COALESCE(EXCLUDED.code_cnbf, avocat.code_cnbf),
                        modifie_par = %s,
                        modifie_le = now()
                """,
                (contact_id, barreau_id, cabinet_id, code_cnbf, utilisateur_id, utilisateur_id),
            )
            # Un avocat porte toujours la civilité "Maître" (code 'ME',
            # voir migrations/0002...civilite) : imposé dès qu'un contact
            # devient avocat, symétriquement à l'interdiction de la changer
            # ensuite (voir contacts.modifier_personne_physique).
            cur.execute(
                "UPDATE personne_physique SET civilite_id = 'ME' WHERE contact_id = %s",
                (contact_id,),
            )
            conn.commit()
    return recuperer_avocat(contact_id)


def supprimer_avocat(contact_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM qualification_professionnelle WHERE contact_id = %s AND profession = 'avocat'",
                (contact_id,),
            )
            conn.commit()


def lister_avocats_par_cabinet(cabinet_id: int) -> list[ResultatRecherche]:
    """Avocats rattachés à ce cabinet (personne_morale), pour affichage sur
    la fiche du cabinet — pendant symétrique du champ cabinet affiché sur
    la fiche de l'avocat."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ResultatRecherche)) as cur:
            cur.execute(
                """
                SELECT pp.contact_id, 'personne_physique' AS type_contact,
                       trim(coalesce(pp.prenom || ' ', '') || pp.nom) AS libelle
                FROM avocat a
                JOIN personne_physique pp ON pp.contact_id = a.contact_id
                WHERE a.cabinet_id = %s
                ORDER BY libelle
                """,
                (cabinet_id,),
            )
            return cur.fetchall()


def recuperer_notaire(contact_id: int) -> Notaire | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Notaire)) as cur:
            cur.execute(
                """
                SELECT contact_id, office_id,
                       cree_par, cree_le, modifie_par, modifie_le
                FROM notaire
                WHERE contact_id = %s
                """,
                (contact_id,),
            )
            return cur.fetchone()


def enregistrer_notaire(
    contact_id: int,
    utilisateur_id: int,
    office_id: int | None = None,
) -> Notaire:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            _basculer_qualification(cur, contact_id, "notaire")
            cur.execute(
                """
                INSERT INTO notaire (contact_id, office_id, cree_par)
                VALUES (%s, %s, %s)
                ON CONFLICT (contact_id) DO UPDATE
                    SET office_id = EXCLUDED.office_id,
                        modifie_par = %s,
                        modifie_le = now()
                """,
                (contact_id, office_id, utilisateur_id, utilisateur_id),
            )
            conn.commit()
    return recuperer_notaire(contact_id)


def supprimer_notaire(contact_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM qualification_professionnelle WHERE contact_id = %s AND profession = 'notaire'",
                (contact_id,),
            )
            conn.commit()


def recuperer_commissaire_justice(contact_id: int) -> CommissaireJustice | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(CommissaireJustice)) as cur:
            cur.execute(
                """
                SELECT contact_id, etude_id,
                       cree_par, cree_le, modifie_par, modifie_le
                FROM commissaire_justice
                WHERE contact_id = %s
                """,
                (contact_id,),
            )
            return cur.fetchone()


def enregistrer_commissaire_justice(
    contact_id: int,
    utilisateur_id: int,
    etude_id: int | None = None,
) -> CommissaireJustice:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            _basculer_qualification(cur, contact_id, "commissaire_justice")
            cur.execute(
                """
                INSERT INTO commissaire_justice (contact_id, etude_id, cree_par)
                VALUES (%s, %s, %s)
                ON CONFLICT (contact_id) DO UPDATE
                    SET etude_id = EXCLUDED.etude_id,
                        modifie_par = %s,
                        modifie_le = now()
                """,
                (contact_id, etude_id, utilisateur_id, utilisateur_id),
            )
            conn.commit()
    return recuperer_commissaire_justice(contact_id)


def supprimer_commissaire_justice(contact_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM qualification_professionnelle WHERE contact_id = %s AND profession = 'commissaire_justice'",
                (contact_id,),
            )
            conn.commit()


def recuperer_profession(contact_id: int) -> str | None:
    """'avocat', 'notaire', 'commissaire_justice' ou None — au plus une
    seule, les trois étant mutuellement exclusives."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT profession FROM qualification_professionnelle WHERE contact_id = %s",
                (contact_id,),
            )
            ligne = cur.fetchone()
            return ligne[0] if ligne else None
