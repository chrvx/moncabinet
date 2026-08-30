from psycopg.rows import class_row

from app import db
from app.modeles import (
    Adresse,
    ContactAdresse,
    ContactEmail,
    ContactTelephone,
    Email,
    Telephone,
)
from app.normalisation import normaliser_email, normaliser_telephone

# --- Adresses -------------------------------------------------------------


def ajouter_adresse(
    contact_id: int,
    utilisateur_id: int,
    complement: str | None = None,
    entree_batiment: str | None = None,
    numero_voie: str | None = None,
    libelle_voie: str | None = None,
    mention_distribution_type: str | None = None,
    mention_distribution_valeur: str | None = None,
    code_postal: str | None = None,
    code_cedex: str | None = None,
    numero_cedex: str | None = None,
    commune: str | None = None,
    pays_id: str | None = None,
    code_insee_commune: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    libelle_complet_ban: str | None = None,
    mention_destinataire: str | None = None,
    source: str = "manuel",
) -> tuple[Adresse, ContactAdresse]:
    """Crée une nouvelle adresse et la relie immédiatement au contact.

    Pour relier un contact à une adresse qui existe déjà (le cas du couple
    qui partage un domicile), utiliser lier_adresse_existante plutôt que
    cette fonction, afin de ne pas dupliquer la ligne ADRESSE. Contrairement
    au téléphone et à l'email, ce choix reste manuel : deux adresses postales
    peuvent être écrites différemment (abréviations, ordre des lignes) sans
    être fausses pour autant, une comparaison automatique serait peu fiable."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO adresse (
                    complement, entree_batiment, numero_voie, libelle_voie,
                    mention_distribution_type, mention_distribution_valeur,
                    code_postal, code_cedex, numero_cedex, commune, pays_id,
                    code_insee_commune, latitude, longitude,
                    libelle_complet_ban, cree_par
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    complement, entree_batiment, numero_voie, libelle_voie,
                    mention_distribution_type, mention_distribution_valeur,
                    code_postal, code_cedex, numero_cedex, commune, pays_id,
                    code_insee_commune, latitude, longitude,
                    libelle_complet_ban, utilisateur_id,
                ),
            )
            adresse_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO contact_adresse
                    (contact_id, adresse_id, mention_destinataire, cree_par, source)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (contact_id, adresse_id, mention_destinataire, utilisateur_id, source),
            )
            contact_adresse_id = cur.fetchone()[0]
            conn.commit()
    return recuperer_adresse(adresse_id), recuperer_contact_adresse(contact_adresse_id)


def lier_adresse_existante(
    contact_id: int,
    adresse_id: int,
    utilisateur_id: int,
    mention_destinataire: str | None = None,
    source: str = "manuel",
) -> ContactAdresse:
    """Relie un contact à une adresse déjà enregistrée pour un autre contact
    — le cas du couple qui partage un même domicile."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contact_adresse
                    (contact_id, adresse_id, mention_destinataire, cree_par, source)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (contact_id, adresse_id, mention_destinataire, utilisateur_id, source),
            )
            contact_adresse_id = cur.fetchone()[0]
            conn.commit()
    return recuperer_contact_adresse(contact_adresse_id)


def terminer_lien_adresse(contact_adresse_id: int, utilisateur_id: int) -> None:
    """Clôt un lien contact-adresse à la date du jour, sans jamais modifier
    ni supprimer la ligne ADRESSE elle-même : c'est ce qui préserve
    l'historique (voir ajouter_adresse pour ouvrir le lien suivant)."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_adresse
                SET date_fin = current_date, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, contact_adresse_id),
            )
            conn.commit()


def recuperer_adresse(adresse_id: int) -> Adresse | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Adresse)) as cur:
            cur.execute(
                """
                SELECT id, complement, entree_batiment, numero_voie, libelle_voie,
                       mention_distribution_type, mention_distribution_valeur,
                       code_postal, code_cedex, numero_cedex, commune, pays_id,
                       code_insee_commune, latitude, longitude, libelle_complet_ban,
                       modifie_par, modifie_le
                FROM adresse
                WHERE id = %s
                """,
                (adresse_id,),
            )
            return cur.fetchone()


def corriger_adresse(
    adresse_id: int,
    utilisateur_id: int,
    complement: str | None = None,
    entree_batiment: str | None = None,
    numero_voie: str | None = None,
    libelle_voie: str | None = None,
    mention_distribution_type: str | None = None,
    mention_distribution_valeur: str | None = None,
    code_postal: str | None = None,
    code_cedex: str | None = None,
    numero_cedex: str | None = None,
    commune: str | None = None,
    pays_id: str | None = None,
    code_insee_commune: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    libelle_complet_ban: str | None = None,
) -> Adresse | None:
    """Corrige une faute de frappe sur l'adresse elle-même, par UPDATE en
    place : contrairement à un déménagement (terminer_lien_adresse puis
    ajouter_adresse), ceci ne touche ni date_debut ni date_fin et ne laisse
    donc aucune trace dans l'historique du contact. Comme la ligne ADRESSE
    peut être partagée par plusieurs contacts, la correction s'applique à
    tous ceux qui la partagent — voir lister_autres_contacts_adresse pour
    prévenir l'utilisateur avant de corriger."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE adresse
                SET complement = %s, entree_batiment = %s, numero_voie = %s,
                    libelle_voie = %s, mention_distribution_type = %s,
                    mention_distribution_valeur = %s, code_postal = %s,
                    code_cedex = %s, numero_cedex = %s, commune = %s,
                    pays_id = %s, code_insee_commune = %s, latitude = %s,
                    longitude = %s, libelle_complet_ban = %s,
                    modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (
                    complement, entree_batiment, numero_voie, libelle_voie,
                    mention_distribution_type, mention_distribution_valeur,
                    code_postal, code_cedex, numero_cedex, commune, pays_id,
                    code_insee_commune, latitude, longitude,
                    libelle_complet_ban, utilisateur_id, adresse_id,
                ),
            )
            conn.commit()
    return recuperer_adresse(adresse_id)


def modifier_mention_destinataire_adresse(
    contact_adresse_id: int, mention_destinataire: str | None, utilisateur_id: int
) -> None:
    """La mention destinataire ("chez untel"...) est propre au lien
    contact-adresse, pas à l'adresse elle-même : la corriger n'a donc de
    toute façon aucun impact sur l'historique ni sur les autres contacts
    qui partagent la même adresse."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_adresse
                SET mention_destinataire = %s, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (mention_destinataire, utilisateur_id, contact_adresse_id),
            )
            conn.commit()


def lister_autres_contacts_adresse(adresse_id: int, contact_id: int) -> list[str]:
    """Libellés des autres contacts actuellement liés (lien actif) à cette
    même ligne ADRESSE, pour avertir avant une correction en place qu'elle
    les concerne aussi."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT coalesce(
                    trim(coalesce(pp.prenom || ' ', '') || pp.nom), pm.raison_sociale
                ) AS libelle
                FROM contact_adresse ca
                LEFT JOIN personne_physique pp ON pp.contact_id = ca.contact_id
                LEFT JOIN personne_morale pm ON pm.contact_id = ca.contact_id
                WHERE ca.adresse_id = %s AND ca.date_fin IS NULL AND ca.contact_id != %s
                """,
                (adresse_id, contact_id),
            )
            return [ligne[0] for ligne in cur.fetchall()]


def recuperer_contact_adresse(contact_adresse_id: int) -> ContactAdresse | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ContactAdresse)) as cur:
            cur.execute(
                """
                SELECT id, contact_id, adresse_id, mention_destinataire,
                       date_debut, date_fin, source
                FROM contact_adresse
                WHERE id = %s
                """,
                (contact_adresse_id,),
            )
            return cur.fetchone()


def lister_adresses(
    contact_id: int, actives_seulement: bool = True
) -> list[tuple[Adresse, ContactAdresse]]:
    # actives_seulement est un booléen fourni par le code, jamais une valeur
    # saisie par l'utilisateur : ajouter ce fragment à la requête ne risque
    # pas d'injection SQL, contrairement à une valeur qui viendrait d'un
    # formulaire.
    requete = """
        SELECT
            a.id, a.complement, a.entree_batiment, a.numero_voie, a.libelle_voie,
            a.mention_distribution_type, a.mention_distribution_valeur,
            a.code_postal, a.code_cedex, a.numero_cedex, a.commune, a.pays_id,
            a.code_insee_commune, a.latitude, a.longitude, a.libelle_complet_ban,
            a.modifie_par, a.modifie_le,
            ca.id, ca.contact_id, ca.adresse_id, ca.mention_destinataire,
            ca.date_debut, ca.date_fin, ca.source
        FROM contact_adresse ca
        JOIN adresse a ON a.id = ca.adresse_id
        WHERE ca.contact_id = %s
    """
    if actives_seulement:
        requete += " AND ca.date_fin IS NULL"
    requete += " ORDER BY ca.date_debut DESC"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(requete, (contact_id,))
            resultats = []
            for ligne in cur.fetchall():
                adresse = Adresse(*ligne[0:18])
                contact_adresse = ContactAdresse(*ligne[18:25])
                resultats.append((adresse, contact_adresse))
            return resultats


# --- Téléphones -------------------------------------------------------------


def _rechercher_telephone_par_numero(numero_normalise: str) -> Telephone | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Telephone)) as cur:
            cur.execute(
                "SELECT id, numero, modifie_par, modifie_le FROM telephone WHERE numero = %s",
                (numero_normalise,),
            )
            return cur.fetchone()


def ajouter_telephone(
    contact_id: int, numero: str, utilisateur_id: int, source: str = "manuel"
) -> tuple[ContactTelephone | None, str]:
    """Ajoute un téléphone après normalisation (chiffres seulement), avec
    trois issues possibles, renvoyées comme statut :
    - "nouveau" : numéro inédit, tout est créé ;
    - "partage" : le numéro existait déjà pour un autre contact — on relie
      ce contact à la ligne telephone existante plutôt que d'en dupliquer
      une, ce qui active au passage le partage entre contacts ;
    - "deja_actif" : ce contact a déjà ce numéro actif, rien n'est créé."""
    numero_normalise = normaliser_telephone(numero)
    telephone_existant = _rechercher_telephone_par_numero(numero_normalise)

    if telephone_existant:
        for t, lien in lister_telephones(contact_id):
            if t.id == telephone_existant.id and lien.date_fin is None:
                return lien, "deja_actif"
        lien = lier_telephone_existant(contact_id, telephone_existant.id, utilisateur_id, source)
        return lien, "partage"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO telephone (numero, cree_par) VALUES (%s, %s) RETURNING id",
                (numero_normalise, utilisateur_id),
            )
            telephone_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO contact_telephone (contact_id, telephone_id, cree_par, source)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (contact_id, telephone_id, utilisateur_id, source),
            )
            contact_telephone_id = cur.fetchone()[0]
            conn.commit()
    return recuperer_contact_telephone(contact_telephone_id), "nouveau"


def lier_telephone_existant(
    contact_id: int, telephone_id: int, utilisateur_id: int, source: str = "manuel"
) -> ContactTelephone:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contact_telephone (contact_id, telephone_id, cree_par, source)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (contact_id, telephone_id, utilisateur_id, source),
            )
            contact_telephone_id = cur.fetchone()[0]
            conn.commit()
    return recuperer_contact_telephone(contact_telephone_id)


def terminer_lien_telephone(contact_telephone_id: int, utilisateur_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_telephone
                SET date_fin = current_date, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, contact_telephone_id),
            )
            conn.commit()


def corriger_telephone(
    telephone_id: int, numero: str, utilisateur_id: int
) -> Telephone | str:
    """Corrige une faute de frappe sur le numéro lui-même, par UPDATE en
    place (pas de clôture/réouverture de lien, donc rien dans l'historique).
    Comme la ligne TELEPHONE peut être partagée, la correction s'applique à
    tous les contacts qui la partagent — voir lister_autres_contacts_telephone
    pour prévenir l'utilisateur avant de corriger.

    Si le numéro corrigé correspond en fait à un numéro déjà enregistré sous
    une autre ligne, la correction est refusée (retourne "doublon") : ce
    serait fusionner deux numéros différents, pas corriger une faute de
    frappe — il faut alors clôturer puis ajouter, pour profiter de la
    détection de partage normale."""
    numero_normalise = normaliser_telephone(numero)
    existant = _rechercher_telephone_par_numero(numero_normalise)
    if existant and existant.id != telephone_id:
        return "doublon"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE telephone
                SET numero = %s, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (numero_normalise, utilisateur_id, telephone_id),
            )
            conn.commit()
    return _recuperer_telephone(telephone_id)


def marquer_source_manuelle_telephone(contact_telephone_id: int) -> None:
    """Fait basculer un lien contact_telephone vers source='manuel' et
    efface un écart annuaire éventuellement consigné — à appeler après
    qu'un utilisateur corrige à la main un numéro importé de l'annuaire
    national (voir routes.corriger_telephone), pour qu'une
    resynchronisation ultérieure (coordonnees.synchroniser_telephone) ne
    puisse plus jamais écraser cette correction."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_telephone
                SET source = 'manuel', valeur_annuaire_divergente = NULL, constatee_le = NULL
                WHERE id = %s
                """,
                (contact_telephone_id,),
            )
            conn.commit()


def _recuperer_telephone(telephone_id: int) -> Telephone | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Telephone)) as cur:
            cur.execute(
                "SELECT id, numero, modifie_par, modifie_le FROM telephone WHERE id = %s",
                (telephone_id,),
            )
            return cur.fetchone()


def lister_autres_contacts_telephone(telephone_id: int, contact_id: int) -> list[str]:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT coalesce(
                    trim(coalesce(pp.prenom || ' ', '') || pp.nom), pm.raison_sociale
                ) AS libelle
                FROM contact_telephone ct
                LEFT JOIN personne_physique pp ON pp.contact_id = ct.contact_id
                LEFT JOIN personne_morale pm ON pm.contact_id = ct.contact_id
                WHERE ct.telephone_id = %s AND ct.date_fin IS NULL AND ct.contact_id != %s
                """,
                (telephone_id, contact_id),
            )
            return [ligne[0] for ligne in cur.fetchall()]


def recuperer_contact_telephone(contact_telephone_id: int) -> ContactTelephone | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ContactTelephone)) as cur:
            cur.execute(
                """
                SELECT id, contact_id, telephone_id, date_debut, date_fin,
                       source, valeur_annuaire_divergente, constatee_le
                FROM contact_telephone
                WHERE id = %s
                """,
                (contact_telephone_id,),
            )
            return cur.fetchone()


def lister_telephones(
    contact_id: int, actives_seulement: bool = True
) -> list[tuple[Telephone, ContactTelephone]]:
    requete = """
        SELECT t.id, t.numero, t.modifie_par, t.modifie_le,
               ct.id, ct.contact_id, ct.telephone_id,
               ct.date_debut, ct.date_fin,
               ct.source, ct.valeur_annuaire_divergente, ct.constatee_le
        FROM contact_telephone ct
        JOIN telephone t ON t.id = ct.telephone_id
        WHERE ct.contact_id = %s
    """
    if actives_seulement:
        requete += " AND ct.date_fin IS NULL"
    requete += " ORDER BY ct.date_debut DESC"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(requete, (contact_id,))
            resultats = []
            for ligne in cur.fetchall():
                telephone = Telephone(*ligne[0:4])
                contact_telephone = ContactTelephone(*ligne[4:12])
                resultats.append((telephone, contact_telephone))
            return resultats


def synchroniser_telephone(
    contact_id: int, numero_annuaire: str | None, utilisateur_id: int
) -> str:
    """Rapproche le téléphone actif d'un contact avec la valeur constatée
    dans l'annuaire national des avocats, lors d'un import/resynchronisation
    (voir migration 0015 et app/services/annuaire_avocats.py) :
    - pas de valeur annuaire : rien à faire ("ignore") ;
    - aucun téléphone actif encore enregistré : on le crée, source
      'import_annuaire' ("cree") ;
    - téléphone actif de source 'import_annuaire' et valeur différente :
      on clôture l'ancien lien et on ajoute le nouveau, toujours source
      'import_annuaire' ("maj") ;
    - téléphone actif de source 'manuel' et valeur différente : on ne
      touche à rien, on consigne seulement l'écart pour affichage sur la
      fiche contact ("divergence") ;
    - valeur identique : on efface un écart précédemment consigné, s'il y
      en avait un ("inchange")."""
    if not numero_annuaire:
        return "ignore"
    numero_normalise = normaliser_telephone(numero_annuaire)

    actifs = [(t, lien) for t, lien in lister_telephones(contact_id) if lien.date_fin is None]
    if not actifs:
        ajouter_telephone(contact_id, numero_normalise, utilisateur_id, source="import_annuaire")
        return "cree"
    telephone_actif, lien_actif = actifs[0]

    if telephone_actif.numero == numero_normalise:
        if lien_actif.valeur_annuaire_divergente is not None:
            _effacer_divergence_telephone(lien_actif.id)
        return "inchange"

    if lien_actif.source == "import_annuaire":
        terminer_lien_telephone(lien_actif.id, utilisateur_id)
        ajouter_telephone(contact_id, numero_normalise, utilisateur_id, source="import_annuaire")
        return "maj"

    _signaler_divergence_telephone(lien_actif.id, numero_normalise)
    return "divergence"


def _signaler_divergence_telephone(contact_telephone_id: int, valeur_annuaire: str) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_telephone
                SET valeur_annuaire_divergente = %s, constatee_le = current_date
                WHERE id = %s
                """,
                (valeur_annuaire, contact_telephone_id),
            )
            conn.commit()


def _effacer_divergence_telephone(contact_telephone_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_telephone
                SET valeur_annuaire_divergente = NULL, constatee_le = NULL
                WHERE id = %s
                """,
                (contact_telephone_id,),
            )
            conn.commit()


# --- Emails -------------------------------------------------------------


def _rechercher_email_par_adresse(adresse_normalisee: str) -> Email | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Email)) as cur:
            cur.execute(
                "SELECT id, adresse_email, modifie_par, modifie_le FROM email WHERE adresse_email = %s",
                (adresse_normalisee,),
            )
            return cur.fetchone()


def ajouter_email(
    contact_id: int, adresse_email: str, utilisateur_id: int, source: str = "manuel"
) -> tuple[ContactEmail | None, str]:
    """Même logique que ajouter_telephone : "nouveau", "partage" (email
    déjà utilisé par un autre contact, désormais lié aux deux) ou
    "deja_actif" (ce contact a déjà cet email actif)."""
    adresse_normalisee = normaliser_email(adresse_email)
    email_existant = _rechercher_email_par_adresse(adresse_normalisee)

    if email_existant:
        for e, lien in lister_emails(contact_id):
            if e.id == email_existant.id and lien.date_fin is None:
                return lien, "deja_actif"
        lien = lier_email_existant(contact_id, email_existant.id, utilisateur_id, source)
        return lien, "partage"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO email (adresse_email, cree_par) VALUES (%s, %s) RETURNING id",
                (adresse_normalisee, utilisateur_id),
            )
            email_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO contact_email (contact_id, email_id, cree_par, source)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (contact_id, email_id, utilisateur_id, source),
            )
            contact_email_id = cur.fetchone()[0]
            conn.commit()
    return recuperer_contact_email(contact_email_id), "nouveau"


def lier_email_existant(
    contact_id: int, email_id: int, utilisateur_id: int, source: str = "manuel"
) -> ContactEmail:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contact_email (contact_id, email_id, cree_par, source)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (contact_id, email_id, utilisateur_id, source),
            )
            contact_email_id = cur.fetchone()[0]
            conn.commit()
    return recuperer_contact_email(contact_email_id)


def terminer_lien_email(contact_email_id: int, utilisateur_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_email
                SET date_fin = current_date, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (utilisateur_id, contact_email_id),
            )
            conn.commit()


def corriger_email(email_id: int, adresse_email: str, utilisateur_id: int) -> Email | str:
    """Même logique que corriger_telephone : UPDATE en place de la ligne
    EMAIL (aucun impact sur l'historique du lien), refusé si l'adresse
    corrigée correspond en fait à une autre ligne EMAIL déjà existante
    ("doublon" — ce serait une fusion, pas une correction)."""
    adresse_normalisee = normaliser_email(adresse_email)
    existant = _rechercher_email_par_adresse(adresse_normalisee)
    if existant and existant.id != email_id:
        return "doublon"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE email
                SET adresse_email = %s, modifie_par = %s, modifie_le = now()
                WHERE id = %s
                """,
                (adresse_normalisee, utilisateur_id, email_id),
            )
            conn.commit()
    return _recuperer_email(email_id)


def marquer_source_manuelle_email(contact_email_id: int) -> None:
    """Pendant de marquer_source_manuelle_telephone pour l'email — voir sa
    docstring."""
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_email
                SET source = 'manuel', valeur_annuaire_divergente = NULL, constatee_le = NULL
                WHERE id = %s
                """,
                (contact_email_id,),
            )
            conn.commit()


def _recuperer_email(email_id: int) -> Email | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(Email)) as cur:
            cur.execute(
                "SELECT id, adresse_email, modifie_par, modifie_le FROM email WHERE id = %s",
                (email_id,),
            )
            return cur.fetchone()


def lister_autres_contacts_email(email_id: int, contact_id: int) -> list[str]:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT coalesce(
                    trim(coalesce(pp.prenom || ' ', '') || pp.nom), pm.raison_sociale
                ) AS libelle
                FROM contact_email ce
                LEFT JOIN personne_physique pp ON pp.contact_id = ce.contact_id
                LEFT JOIN personne_morale pm ON pm.contact_id = ce.contact_id
                WHERE ce.email_id = %s AND ce.date_fin IS NULL AND ce.contact_id != %s
                """,
                (email_id, contact_id),
            )
            return [ligne[0] for ligne in cur.fetchall()]


def recuperer_contact_email(contact_email_id: int) -> ContactEmail | None:
    with db.pool.connection() as conn:
        with conn.cursor(row_factory=class_row(ContactEmail)) as cur:
            cur.execute(
                """
                SELECT id, contact_id, email_id, date_debut, date_fin,
                       source, valeur_annuaire_divergente, constatee_le
                FROM contact_email
                WHERE id = %s
                """,
                (contact_email_id,),
            )
            return cur.fetchone()


def lister_emails(
    contact_id: int, actives_seulement: bool = True
) -> list[tuple[Email, ContactEmail]]:
    requete = """
        SELECT e.id, e.adresse_email, e.modifie_par, e.modifie_le,
               ce.id, ce.contact_id, ce.email_id,
               ce.date_debut, ce.date_fin,
               ce.source, ce.valeur_annuaire_divergente, ce.constatee_le
        FROM contact_email ce
        JOIN email e ON e.id = ce.email_id
        WHERE ce.contact_id = %s
    """
    if actives_seulement:
        requete += " AND ce.date_fin IS NULL"
    requete += " ORDER BY ce.date_debut DESC"

    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(requete, (contact_id,))
            resultats = []
            for ligne in cur.fetchall():
                email = Email(*ligne[0:4])
                contact_email = ContactEmail(*ligne[4:12])
                resultats.append((email, contact_email))
            return resultats


def synchroniser_email(
    contact_id: int, adresse_email_annuaire: str | None, utilisateur_id: int
) -> str:
    """Pendant de synchroniser_telephone pour l'email — voir sa docstring
    pour le détail des quatre issues possibles ("cree", "maj",
    "divergence", "inchange"/"ignore")."""
    if not adresse_email_annuaire:
        return "ignore"
    adresse_normalisee = normaliser_email(adresse_email_annuaire)

    actifs = [(e, lien) for e, lien in lister_emails(contact_id) if lien.date_fin is None]
    if not actifs:
        ajouter_email(contact_id, adresse_normalisee, utilisateur_id, source="import_annuaire")
        return "cree"
    email_actif, lien_actif = actifs[0]

    if email_actif.adresse_email == adresse_normalisee:
        if lien_actif.valeur_annuaire_divergente is not None:
            _effacer_divergence_email(lien_actif.id)
        return "inchange"

    if lien_actif.source == "import_annuaire":
        terminer_lien_email(lien_actif.id, utilisateur_id)
        ajouter_email(contact_id, adresse_normalisee, utilisateur_id, source="import_annuaire")
        return "maj"

    _signaler_divergence_email(lien_actif.id, adresse_normalisee)
    return "divergence"


def _signaler_divergence_email(contact_email_id: int, valeur_annuaire: str) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_email
                SET valeur_annuaire_divergente = %s, constatee_le = current_date
                WHERE id = %s
                """,
                (valeur_annuaire, contact_email_id),
            )
            conn.commit()


def _effacer_divergence_email(contact_email_id: int) -> None:
    with db.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contact_email
                SET valeur_annuaire_divergente = NULL, constatee_le = NULL
                WHERE id = %s
                """,
                (contact_email_id,),
            )
            conn.commit()
