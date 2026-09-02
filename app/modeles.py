from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass
class Utilisateur:
    """Représente une ligne de la table `utilisateur`.

    Cette dataclass est un simple conteneur typé, sans logique ni lien avec
    la base de données : c'est le repository (repositories/utilisateurs.py)
    qui sait aller chercher ces objets en base et les construire.
    """

    id: int
    nom: str
    mot_de_passe_hash: str
    role: str
    actif: bool


# --- Tables de référence -----------------------------------------------

@dataclass
class Pays:
    code_iso: str
    libelle: str
    gentile_masculin: str | None
    gentile_feminin: str | None


@dataclass
class Departement:
    code: str
    libelle: str


@dataclass
class Civilite:
    code: str
    libelle: str
    abreviation: str | None


@dataclass
class TypeRole:
    id: int
    libelle: str
    dossier_regle: str
    contact_lie_regle: str
    exclusif: bool


@dataclass
class Barreau:
    id: int
    libelle: str
    actif: bool


# --- Contact et ses spécialisations --------------------------------------

@dataclass
class Contact:
    id: int
    type_contact: str
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class PersonnePhysique:
    contact_id: int
    nom: str
    prenom: str | None
    prenoms_secondaires: str | None
    nom_usage: str | None
    genre: str | None
    civilite_id: str | None
    date_naissance: date | None
    ville_naissance: str | None
    departement_naissance_id: str | None
    pays_naissance_id: str | None
    nationalite_id: str | None
    profession: str | None
    siren: str | None


@dataclass
class PersonneMorale:
    contact_id: int
    raison_sociale: str
    forme: str | None
    siren: str | None


@dataclass
class Avocat:
    """Qualification professionnelle d'une personne physique — voir
    migrations/0014.cree-tables-qualification-professionnelle.sql pour la
    distinction avec RoleContact (rôle joué dans un dossier).

    code_cnbf (migration 0015) est le numéro CNBF de l'annuaire national
    des avocats, quand ce contact a été créé ou rapproché par l'import de
    ce référentiel (app/services/annuaire_avocats.py) — voir
    repositories/qualifications.py::recuperer_avocat_par_code_cnbf."""

    contact_id: int
    barreau_id: int | None
    cabinet_id: int | None
    code_cnbf: str | None
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class Notaire:
    contact_id: int
    office_id: int | None
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class CommissaireJustice:
    contact_id: int
    etude_id: int | None
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class RoleContact:
    id: int
    contact_id: int
    type_role_id: int
    dossier_id: int | None
    contact_lie_id: int | None
    cree_par: int | None
    cree_le: datetime


# --- Coordonnées, historisées et partageables ---------------------------

@dataclass
class Adresse:
    id: int
    complement: str | None
    entree_batiment: str | None
    numero_voie: str | None
    libelle_voie: str | None
    mention_distribution_type: str | None
    mention_distribution_valeur: str | None
    code_postal: str | None
    code_cedex: str | None
    numero_cedex: str | None
    commune: str | None
    pays_id: str | None
    code_insee_commune: str | None
    latitude: float | None
    longitude: float | None
    libelle_complet_ban: str | None
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class ContactAdresse:
    id: int
    contact_id: int
    adresse_id: int
    mention_destinataire: str | None
    date_debut: date
    date_fin: date | None
    source: str


@dataclass
class Telephone:
    id: int
    numero: str
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class ContactTelephone:
    id: int
    contact_id: int
    telephone_id: int
    date_debut: date
    date_fin: date | None
    source: str
    valeur_annuaire_divergente: str | None
    constatee_le: date | None


@dataclass
class Email:
    id: int
    adresse_email: str
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class Matiere:
    id: int
    libelle: str
    actif: bool


@dataclass
class Dossier:
    id: int
    reference: str | None
    statut: str
    categorie: str | None
    matiere_id: int | None
    date_ouverture: date | None
    date_cloture: date | None
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None
    numero_archive: str | None


@dataclass
class ContactEmail:
    id: int
    contact_id: int
    email_id: int
    date_debut: date
    date_fin: date | None
    source: str
    valeur_annuaire_divergente: str | None
    constatee_le: date | None


@dataclass
class DossierDocument:
    """Un document généré par fusion d'un modèle Typst avec les données
    d'un dossier — voir app/services/generation_documents.py.
    chemin_pdf/chemin_typ sont relatifs à instance/documents/."""

    id: int
    dossier_id: int
    modele_slug: str
    titre: str
    chemin_pdf: str
    chemin_typ: str
    cree_par: int | None
    cree_le: datetime


@dataclass
class CategorieEcheance:
    """Une catégorie d'échéance (Audience, Délai de procédure...) — table de
    référence éditable depuis parametres/, comme Matiere, pour que le
    cabinet puisse la faire évoluer sans modification de code."""

    id: int
    libelle: str
    actif: bool


@dataclass
class Echeance:
    """Une échéance rattachée à un dossier : audience, délai de procédure,
    rappel client ou entrée d'un calendrier de procédure — voir
    app/repositories/echeances.py. heure_echeance est facultative, seule la
    date est obligatoire."""

    id: int
    dossier_id: int
    categorie_id: int
    libelle: str
    date_echeance: date
    heure_echeance: time | None
    statut: str
    fait_le: datetime | None
    notes: str | None
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class ModeleEcheance:
    """Un modèle d'échéance suggéré pour une matière donnée (ex: "Conclusions
    d'appelant" à 90 jours pour la matière Appel) — une suggestion à
    accepter, corriger ou ignorer à l'ouverture d'un dossier de cette
    matière, jamais une création automatique. Voir
    app/repositories/echeances.py::lister_modeles_non_instancies."""

    id: int
    matiere_id: int
    libelle: str
    categorie_id: int
    delai_jours: int
    actif: bool


@dataclass
class ResultatRecherche:
    """Une ligne de résultat de recherche de contact, personne physique ou
    morale confondues — utilisé notamment pour la recherche anti-conflit
    d'intérêts, qui doit balayer les deux indifféremment."""

    contact_id: int
    type_contact: str
    libelle: str


@dataclass
class LigneContact:
    """Une ligne de la liste des contacts (page contacts.recherche),
    affichée sous forme de table avec les coordonnées actives du contact."""

    contact_id: int
    type_contact: str
    nom: str
    prenom: str | None
    telephone: str | None
    email: str | None
