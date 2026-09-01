import re
from datetime import date, datetime

from psycopg.rows import class_row

from app import db
from app.modeles import Dossier

# --- Numérotation -----------------------------------------------------------


def proposer_reference() -> str:
    """Numéro suivant proposé pour l'année en cours, au format YYNNN.
    Pure lecture : le compteur n'est mis à jour qu'à l'ouverture effective
    (voir ouvrir()), pas à chaque fois qu'on affiche cette suggestion."""
    annee = date.today().year
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT dernier_numero FROM compteur_dossier WHERE annee = %s",
                (annee,),
            )
            ligne = cur.fetchone()
    dernier = ligne[0] if ligne else 0
    numero = dernier + 1
    if numero > 999:
        raise ValueError(
            f"Compteur de dossiers {annee} au maximum (999) : "
            "vérifier compteur_dossier, une référence a dû être saisie par erreur."
        )
    return f"{annee % 100:02d}{numero:03d}"


def _parser_reference(reference: str) -> tuple[int, int] | None:
    """Extrait (année complète, numéro) d'une référence au format YYNNN.
    Renvoie None si la référence ne suit pas ce format (reprise d'un dossier
    numéroté différemment) : dans ce cas le compteur n'est pas mis à jour
    automatiquement, mais l'ouverture reste possible."""
    m = re.fullmatch(r"(\d{2})(\d{3})", reference.strip())
    if not m:
        return None
    annee_courte, numero = m.groups()
    return 2000 + int(annee_courte), int(numero)


# --- Cycle de vie -------------------------------------------------------


def creer_brouillon(contact_id: int, utilisateur_id: int) -> Dossier:
    """Crée un dossier en brouillon et attribue immédiatement le rôle
    client au contact d'origine : un dossier n'existe jamais sans client,
    dès sa création (cf. la discussion de conception initiale)."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dossier (cree_par) VALUES (%s) RETURNING id",
                (utilisateur_id,),
            )
            dossier_id = cur.fetchone()[0]
            cur.execute(
                "SELECT id FROM type_role WHERE libelle = 'client'",
            )
            type_role_client_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO role_contact (contact_id, type_role_id, dossier_id, cree_par)
                VALUES (%s, %s, %s, %s)
                """,
                (contact_id, type_role_client_id, dossier_id, utilisateur_id),
            )
            conn.commit()
    return recuperer(dossier_id)


def ouvrir(dossier_id: int, reference: str, utilisateur_id: int) -> Dossier:
    """Fait passer un dossier de brouillon à ouvert : fixe la référence
    (suggérée ou corrigée par l'utilisateur) et la date d'ouverture. Met à
    jour compteur_dossier sur le plus haut numéro réellement utilisé, que la
    référence vienne de la suggestion ou d'une correction manuelle."""
    reference = reference.strip()
    parse = _parser_reference(reference)

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dossier
                SET reference = %s, statut = 'ouvert', date_ouverture = current_date,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (reference, utilisateur_id, dossier_id),
            )
            if parse:
                annee, numero = parse
                cur.execute(
                    """
                    INSERT INTO compteur_dossier (annee, dernier_numero)
                    VALUES (%s, %s)
                    ON CONFLICT (annee) DO UPDATE
                    SET dernier_numero = GREATEST(compteur_dossier.dernier_numero, EXCLUDED.dernier_numero)
                    """,
                    (annee, numero),
                )
            conn.commit()
    return recuperer(dossier_id)


def clore(dossier_id: int, utilisateur_id: int) -> None:
    """Clôture le dossier et génère son numéro d'archive (format
    YYMMDDHHMM, horodatage de la clôture) : un identifiant de classement
    distinct de la référence YYNNN, qu'il ne remplace pas. Régénéré à
    chaque nouvelle clôture si le dossier a été rouvert entre-temps."""
    numero_archive = datetime.now().strftime("%y%m%d%H%M")
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dossier
                SET statut = 'clos', date_cloture = current_date,
                    numero_archive = %s, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (numero_archive, utilisateur_id, dossier_id),
            )
            conn.commit()


def rouvrir(dossier_id: int, utilisateur_id: int) -> None:
    """Rouvre un dossier clos : le numéro d'archive de la clôture
    précédente est conservé (il reste vrai que ce dossier a été archivé
    sous ce numéro à un moment donné), seuls le statut et la date de
    clôture sont remis à zéro."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dossier
                SET statut = 'ouvert', date_cloture = NULL,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, dossier_id),
            )
            conn.commit()


def modifier(
    dossier_id: int,
    utilisateur_id: int,
    categorie: str | None,
    matiere_id: int | None,
) -> Dossier:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dossier
                SET categorie = %s, matiere_id = %s, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (categorie, matiere_id, utilisateur_id, dossier_id),
            )
            conn.commit()
    return recuperer(dossier_id)


# --- Lecture -------------------------------------------------------------


def recuperer(dossier_id: int) -> Dossier | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Dossier)) as cur:
            cur.execute(
                """
                SELECT id, reference, statut, categorie, matiere_id,
                       date_ouverture, date_cloture, cree_par, cree_le,
                       modifie_par, modifie_le, numero_archive
                FROM dossier
                WHERE id = %s
                """,
                (dossier_id,),
            )
            return cur.fetchone()


def nom_calcule(dossier_id: int) -> str:
    """"NOM DES CLIENTS / NOM DES ADVERSAIRES", en ne gardant que le nom
    (pas le prénom) pour les personnes physiques, comme le veut la
    convention. Sans adversaire (dossier de conseil), pas de "/" du tout —
    ce n'est pas un champ manquant, juste un dossier qui n'en a pas."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tr.libelle, COALESCE(pp.nom, pm.raison_sociale) AS nom
                FROM role_contact rc
                JOIN type_role tr ON tr.id = rc.type_role_id
                LEFT JOIN personne_physique pp ON pp.contact_id = rc.contact_id
                LEFT JOIN personne_morale pm ON pm.contact_id = rc.contact_id
                WHERE rc.dossier_id = %s AND tr.libelle IN ('client', 'adversaire')
                """,
                (dossier_id,),
            )
            lignes = cur.fetchall()

    clients = sorted({nom for libelle, nom in lignes if libelle == "client" and nom})
    adversaires = sorted({nom for libelle, nom in lignes if libelle == "adversaire" and nom})
    partie_clients = ", ".join(clients) if clients else "—"
    if adversaires:
        return f"{partie_clients} / {', '.join(adversaires)}"
    return partie_clients


def lister_ouverts() -> list[Dossier]:
    """Dossiers ouverts, triés par référence — page principale de la liste
    des dossiers."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Dossier)) as cur:
            cur.execute(
                """
                SELECT id, reference, statut, categorie, matiere_id,
                       date_ouverture, date_cloture, cree_par, cree_le,
                       modifie_par, modifie_le, numero_archive
                FROM dossier
                WHERE statut = 'ouvert'
                ORDER BY reference
                """
            )
            return cur.fetchall()


def lister_ouverts_recents(limite: int) -> list[Dossier]:
    """Les dossiers ouverts les plus récemment modifiés — utilisé par le
    tableau de bord d'accueil, où l'ordre par référence de lister_ouverts
    n'est pas ce qu'on veut mettre en avant."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Dossier)) as cur:
            cur.execute(
                """
                SELECT id, reference, statut, categorie, matiere_id,
                       date_ouverture, date_cloture, cree_par, cree_le,
                       modifie_par, modifie_le, numero_archive
                FROM dossier
                WHERE statut = 'ouvert'
                ORDER BY coalesce(modifie_le, cree_le) DESC
                LIMIT %s
                """,
                (limite,),
            )
            return cur.fetchall()


def lister_clos() -> list[Dossier]:
    """Dossiers clôturés, triés par référence."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Dossier)) as cur:
            cur.execute(
                """
                SELECT id, reference, statut, categorie, matiere_id,
                       date_ouverture, date_cloture, cree_par, cree_le,
                       modifie_par, modifie_le, numero_archive
                FROM dossier
                WHERE statut = 'clos'
                ORDER BY reference
                """
            )
            return cur.fetchall()


def lister_brouillons() -> list[Dossier]:
    """Dossiers en brouillon (pas encore de référence), triés du plus
    récent au plus ancien."""
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Dossier)) as cur:
            cur.execute(
                """
                SELECT id, reference, statut, categorie, matiere_id,
                       date_ouverture, date_cloture, cree_par, cree_le,
                       modifie_par, modifie_le, numero_archive
                FROM dossier
                WHERE statut = 'brouillon'
                ORDER BY cree_le DESC
                """
            )
            return cur.fetchall()


def lister_pour_contact(contact_id: int) -> list[tuple[Dossier, str]]:
    """Les dossiers d'un contact, avec le ou les rôles qu'il y tient — l'inverse
    de lister_intervenants, pour la section "Ses dossiers" de la fiche contact.
    Un contact ayant plusieurs qualités dans un même dossier n'apparaît qu'une
    fois, avec ses qualités regroupées sur une seule ligne."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.reference, d.statut, d.categorie, d.matiere_id,
                       d.date_ouverture, d.date_cloture, d.cree_par, d.cree_le,
                       d.modifie_par, d.modifie_le, d.numero_archive,
                       string_agg(tr.libelle, ', ' ORDER BY tr.libelle)
                FROM role_contact rc
                JOIN dossier d ON d.id = rc.dossier_id
                JOIN type_role tr ON tr.id = rc.type_role_id
                WHERE rc.contact_id = %s
                GROUP BY d.id
                ORDER BY d.cree_le DESC
                """,
                (contact_id,),
            )
            resultats = []
            for ligne in cur.fetchall():
                dossier = Dossier(*ligne[0:12])
                resultats.append((dossier, ligne[12]))
            return resultats


def lister_intervenants(dossier_id: int) -> list[dict]:
    """Tous les contacts attachés au dossier, avec leur rôle et, le cas
    échéant, le contact auquel ils sont liés (ex: l'avocat de l'adversaire).
    Renvoie des dictionnaires simples plutôt qu'une dataclass : c'est une
    vue composite pour l'affichage, pas une ligne de table."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    rc.id, tr.libelle,
                    c.id, c.type_contact,
                    COALESCE(
                        NULLIF(trim(COALESCE(pp.prenom || ' ', '') || pp.nom), ''),
                        pm.raison_sociale
                    ) AS nom_contact,
                    rc.contact_lie_id,
                    COALESCE(
                        NULLIF(trim(COALESCE(ppl.prenom || ' ', '') || ppl.nom), ''),
                        pml.raison_sociale
                    ) AS nom_contact_lie
                FROM role_contact rc
                JOIN type_role tr ON tr.id = rc.type_role_id
                JOIN contact c ON c.id = rc.contact_id
                LEFT JOIN personne_physique pp ON pp.contact_id = c.id
                LEFT JOIN personne_morale pm ON pm.contact_id = c.id
                LEFT JOIN personne_physique ppl ON ppl.contact_id = rc.contact_lie_id
                LEFT JOIN personne_morale pml ON pml.contact_id = rc.contact_lie_id
                WHERE rc.dossier_id = %s
                ORDER BY tr.libelle, nom_contact
                """,
                (dossier_id,),
            )
            return [
                {
                    "role_contact_id": ligne[0],
                    "role_libelle": ligne[1],
                    "contact_id": ligne[2],
                    "type_contact": ligne[3],
                    "nom_contact": ligne[4],
                    "contact_lie_id": ligne[5],
                    "nom_contact_lie": ligne[6],
                }
                for ligne in cur.fetchall()
            ]
