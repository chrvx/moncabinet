from psycopg.rows import class_row

from app import db
from app.modeles import (
    Contact,
    LigneContact,
    PersonneMorale,
    PersonnePhysique,
    ResultatRecherche,
)
from app.normalisation import normaliser_nom, normaliser_prenom

# Créer une personne physique ou morale touche deux tables (contact, puis
# sa spécialisation) : les deux insertions se font dans la même connexion,
# avec un seul commit à la fin, pour que l'opération soit atomique — soit
# les deux lignes existent, soit aucune.


def creer_personne_physique(
    nom: str,
    utilisateur_id: int,
    prenom: str | None = None,
    prenoms_secondaires: str | None = None,
    nom_usage: str | None = None,
    genre: str | None = None,
    civilite_id: str | None = None,
    date_naissance=None,
    ville_naissance: str | None = None,
    departement_naissance_id: str | None = None,
    pays_naissance_id: str | None = None,
    nationalite_id: str | None = None,
    profession: str | None = None,
    siren: str | None = None,
) -> PersonnePhysique:
    nom = normaliser_nom(nom)
    prenom = normaliser_prenom(prenom)
    prenoms_secondaires = normaliser_prenom(prenoms_secondaires)
    nom_usage = normaliser_nom(nom_usage)
    ville_naissance = normaliser_prenom(ville_naissance)

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contact (type_contact, cree_par)
                VALUES ('personne_physique', %s)
                RETURNING id
                """,
                (utilisateur_id,),
            )
            contact_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO personne_physique (
                    contact_id, nom, prenom, prenoms_secondaires, nom_usage,
                    genre, civilite_id, date_naissance, ville_naissance,
                    departement_naissance_id, pays_naissance_id,
                    nationalite_id, profession, siren
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    contact_id, nom, prenom, prenoms_secondaires, nom_usage,
                    genre, civilite_id, date_naissance, ville_naissance,
                    departement_naissance_id, pays_naissance_id,
                    nationalite_id, profession, siren,
                ),
            )
            conn.commit()
    return recuperer_personne_physique(contact_id)


def creer_personne_morale(
    raison_sociale: str,
    utilisateur_id: int,
    forme: str | None = None,
    siren: str | None = None,
) -> PersonneMorale:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contact (type_contact, cree_par)
                VALUES ('personne_morale', %s)
                RETURNING id
                """,
                (utilisateur_id,),
            )
            contact_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO personne_morale (contact_id, raison_sociale, forme, siren)
                VALUES (%s, %s, %s, %s)
                """,
                (contact_id, raison_sociale, forme, siren),
            )
            conn.commit()
    return recuperer_personne_morale(contact_id)


def recuperer_personne_physique(contact_id: int) -> PersonnePhysique | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(PersonnePhysique)) as cur:
            cur.execute(
                """
                SELECT contact_id, nom, prenom, prenoms_secondaires, nom_usage,
                       genre, civilite_id, date_naissance, ville_naissance,
                       departement_naissance_id, pays_naissance_id,
                       nationalite_id, profession, siren
                FROM personne_physique
                WHERE contact_id = %s
                """,
                (contact_id,),
            )
            return cur.fetchone()


def recuperer_personne_morale_par_siren(siren: str) -> PersonneMorale | None:
    """Retrouve un cabinet/une société déjà enregistré par son SIREN — sert
    à éviter de dupliquer le cabinet d'exercice d'un avocat à chaque import
    de l'annuaire national (app/services/annuaire_avocats.py), qui répète
    le même cabinet pour tous ses avocats."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(PersonneMorale)) as cur:
            cur.execute(
                "SELECT contact_id, raison_sociale, forme, siren FROM personne_morale WHERE siren = %s",
                (siren,),
            )
            return cur.fetchone()


def recuperer_personne_morale(contact_id: int) -> PersonneMorale | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(PersonneMorale)) as cur:
            cur.execute(
                """
                SELECT contact_id, raison_sociale, forme, siren
                FROM personne_morale
                WHERE contact_id = %s
                """,
                (contact_id,),
            )
            return cur.fetchone()


def modifier_personne_physique(
    contact_id: int,
    utilisateur_id: int,
    nom: str,
    prenom: str | None = None,
    prenoms_secondaires: str | None = None,
    nom_usage: str | None = None,
    genre: str | None = None,
    civilite_id: str | None = None,
    date_naissance=None,
    ville_naissance: str | None = None,
    departement_naissance_id: str | None = None,
    pays_naissance_id: str | None = None,
    nationalite_id: str | None = None,
    profession: str | None = None,
    siren: str | None = None,
) -> PersonnePhysique:
    nom = normaliser_nom(nom)
    prenom = normaliser_prenom(prenom)
    prenoms_secondaires = normaliser_prenom(prenoms_secondaires)
    nom_usage = normaliser_nom(nom_usage)
    ville_naissance = normaliser_prenom(ville_naissance)

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            # Un avocat porte toujours la civilité "Maître" (voir
            # migrations/0002...civilite, code 'ME') : imposé ici plutôt
            # que dans le formulaire, pour qu'aucun appelant ne puisse la
            # contourner — voir aussi qualifications.enregistrer_avocat,
            # qui l'impose symétriquement au moment où le contact devient
            # avocat.
            cur.execute(
                "SELECT 1 FROM qualification_professionnelle WHERE contact_id = %s AND profession = 'avocat'",
                (contact_id,),
            )
            if cur.fetchone() is not None:
                civilite_id = "ME"
            cur.execute(
                """
                UPDATE personne_physique SET
                    nom = %s, prenom = %s, prenoms_secondaires = %s,
                    nom_usage = %s, genre = %s, civilite_id = %s,
                    date_naissance = %s, ville_naissance = %s,
                    departement_naissance_id = %s, pays_naissance_id = %s,
                    nationalite_id = %s, profession = %s, siren = %s
                WHERE contact_id = %s
                """,
                (
                    nom, prenom, prenoms_secondaires, nom_usage, genre,
                    civilite_id, date_naissance, ville_naissance,
                    departement_naissance_id, pays_naissance_id,
                    nationalite_id, profession, siren, contact_id,
                ),
            )
            cur.execute(
                "UPDATE contact SET modifie_par = %s, modifie_le = now() WHERE id = %s",
                (utilisateur_id, contact_id),
            )
            conn.commit()
    return recuperer_personne_physique(contact_id)


def modifier_personne_morale(
    contact_id: int,
    utilisateur_id: int,
    raison_sociale: str,
    forme: str | None = None,
    siren: str | None = None,
) -> PersonneMorale:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE personne_morale
                SET raison_sociale = %s, forme = %s, siren = %s
                WHERE contact_id = %s
                """,
                (raison_sociale, forme, siren, contact_id),
            )
            cur.execute(
                "UPDATE contact SET modifie_par = %s, modifie_le = now() WHERE id = %s",
                (utilisateur_id, contact_id),
            )
            conn.commit()
    return recuperer_personne_morale(contact_id)


def recuperer_contact(contact_id: int) -> Contact | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Contact)) as cur:
            cur.execute(
                """
                SELECT id, type_contact, cree_par, cree_le, modifie_par, modifie_le
                FROM contact
                WHERE id = %s
                """,
                (contact_id,),
            )
            return cur.fetchone()


def compter() -> int:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM contact")
            return cur.fetchone()[0]


def rechercher_par_nom(terme: str) -> list[ResultatRecherche]:
    """Recherche anti-conflit d'intérêts : balaie personnes physiques et
    morales sans distinction, sur tous les noms possibles d'une personne
    (nom, prénom, nom d'usage). Toujours exhaustive, quel que soit le rôle
    de qui l'exécute (voir la discussion sur les permissions de la
    phase 4) : ce n'est pas ici qu'on doit restreindre la visibilité."""
    motif = f"%{terme}%"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ResultatRecherche)) as cur:
            cur.execute(
                """
                SELECT contact_id, 'personne_physique' AS type_contact,
                       trim(coalesce(prenom || ' ', '') || nom) AS libelle
                FROM personne_physique
                WHERE nom ILIKE %(motif)s
                   OR prenom ILIKE %(motif)s
                   OR nom_usage ILIKE %(motif)s
                   OR trim(coalesce(prenom || ' ', '') || nom) ILIKE %(motif)s
                UNION ALL
                SELECT contact_id, 'personne_morale' AS type_contact,
                       raison_sociale AS libelle
                FROM personne_morale
                WHERE raison_sociale ILIKE %(motif)s
                ORDER BY libelle
                """,
                {"motif": motif},
            )
            return cur.fetchall()


# CTE commune à lister_avec_coordonnees : une ligne par contact (personne
# physique ou morale) avec son téléphone et son email actifs agrégés
# (string_agg, au cas où plusieurs seraient actifs à la fois), pour
# l'affichage en table de la page contacts.recherche et de ses raccourcis
# par qualité (avocats, clients, adversaires).
_CTE_CONTACTS_AVEC_COORDONNEES = """
    WITH base AS (
        SELECT contact_id, 'personne_physique' AS type_contact, nom, prenom, nom_usage
        FROM personne_physique
        UNION ALL
        SELECT contact_id, 'personne_morale' AS type_contact, raison_sociale AS nom,
               NULL AS prenom, NULL AS nom_usage
        FROM personne_morale
    ),
    tel AS (
        SELECT ct.contact_id, string_agg(t.numero, ', ' ORDER BY ct.date_debut DESC) AS telephone
        FROM contact_telephone ct
        JOIN telephone t ON t.id = ct.telephone_id
        WHERE ct.date_fin IS NULL
        GROUP BY ct.contact_id
    ),
    mail AS (
        SELECT ce.contact_id, string_agg(e.adresse_email, ', ' ORDER BY ce.date_debut DESC) AS email
        FROM contact_email ce
        JOIN email e ON e.id = ce.email_id
        WHERE ce.date_fin IS NULL
        GROUP BY ce.contact_id
    )
"""

# Sous-requêtes de contact_id restreignant à une qualité donnée, pour
# lister_avec_coordonnees : avocat vient de la qualification professionnelle
# (voir qualifications.py) et inclut aussi les cabinets d'exercice
# (personne_morale référencée en cabinet_id), client/adversaire d'un rôle
# porté sur un dossier, quel qu'il soit (voir roles.py).
_SOUS_REQUETES_QUALITE = {
    "avocat": """
        SELECT contact_id FROM avocat
        UNION
        SELECT cabinet_id FROM avocat WHERE cabinet_id IS NOT NULL
    """,
    "client": """
        SELECT DISTINCT rc.contact_id FROM role_contact rc
        JOIN type_role tr ON tr.id = rc.type_role_id WHERE tr.libelle = 'client'
    """,
    "adversaire": """
        SELECT DISTINCT rc.contact_id FROM role_contact rc
        JOIN type_role tr ON tr.id = rc.type_role_id WHERE tr.libelle = 'adversaire'
    """,
}


def lister_avec_coordonnees(
    qualite: str | None = None,
    terme: str | None = None,
    page: int = 1,
    taille_page: int = 25,
) -> tuple[list[LigneContact], int]:
    """Table de contacts, coordonnées jointes, triée par nom/dénomination —
    sert à la fois la page contacts.recherche (terme et pagination) et ses
    raccourcis par qualité contacts.liste_avocats/clients/adversaires
    (qualite, jamais paginés puisque déjà une liste bornée). Combiner
    qualite et terme filtre l'un par l'autre (ex: chercher un nom parmi les
    seuls clients)."""
    conditions = []
    parametres = {}
    if qualite:
        conditions.append(f"b.contact_id IN ({_SOUS_REQUETES_QUALITE[qualite]})")
    if terme:
        conditions.append(
            "(b.nom ILIKE %(motif)s OR b.prenom ILIKE %(motif)s OR b.nom_usage ILIKE %(motif)s)"
        )
        parametres["motif"] = f"%{terme}%"
    clause_where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    paginer = not conditions
    clause_limite = "LIMIT %(taille_page)s OFFSET %(decalage)s" if paginer else ""
    if paginer:
        parametres["taille_page"] = taille_page
        parametres["decalage"] = (page - 1) * taille_page

    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(LigneContact)) as cur:
            cur.execute(
                _CTE_CONTACTS_AVEC_COORDONNEES
                + f"""
                SELECT b.contact_id, b.type_contact, b.nom, b.prenom,
                       tel.telephone, mail.email
                FROM base b
                LEFT JOIN tel ON tel.contact_id = b.contact_id
                LEFT JOIN mail ON mail.contact_id = b.contact_id
                {clause_where}
                ORDER BY b.nom
                {clause_limite}
                """,
                parametres,
            )
            resultats = cur.fetchall()
        if paginer:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT (SELECT count(*) FROM personne_physique)
                         + (SELECT count(*) FROM personne_morale)
                    """
                )
                total = cur.fetchone()[0]
        else:
            total = len(resultats)
    return resultats, total


def rechercher_suggestions(terme: str, limite: int = 8) -> list[ResultatRecherche]:
    """Même recherche que rechercher_par_nom, mais bornée en nombre de
    résultats : pensée pour l'autocomplétion au fil de la frappe, pas pour
    la liste complète affichée après une recherche validée."""
    motif = f"%{terme}%"
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ResultatRecherche)) as cur:
            cur.execute(
                """
                SELECT contact_id, 'personne_physique' AS type_contact,
                       trim(coalesce(prenom || ' ', '') || nom) AS libelle
                FROM personne_physique
                WHERE nom ILIKE %(motif)s
                   OR prenom ILIKE %(motif)s
                   OR nom_usage ILIKE %(motif)s
                   OR trim(coalesce(prenom || ' ', '') || nom) ILIKE %(motif)s
                UNION ALL
                SELECT contact_id, 'personne_morale' AS type_contact,
                       raison_sociale AS libelle
                FROM personne_morale
                WHERE raison_sociale ILIKE %(motif)s
                ORDER BY libelle
                LIMIT %(limite)s
                """,
                {"motif": motif, "limite": limite},
            )
            return cur.fetchall()
