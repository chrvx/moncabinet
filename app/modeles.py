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
class CategorieMatiere:
    """Une catégorie de matière (Droit de la famille, Droit immobilier...) —
    table de référence éditable depuis parametres/, comme CategorieEcheance,
    utilisée pour regrouper les matières dans le menu déroulant du dossier."""

    id: int
    libelle: str
    actif: bool


@dataclass
class Matiere:
    id: int
    libelle: str
    actif: bool
    categorie_id: int | None


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
class Document:
    """Une pièce rattachée à un dossier, quelle que soit son origine —
    document généré par fusion Typst, e-mail importé ou fichier déposé (voir
    type_document). chemin_fichier est relatif à instance/documents/ et
    pointe vers le fichier principal : le PDF pour un document généré, le
    .eml pour un e-mail, le fichier uploadé pour un dépôt. Les champs propres
    à chaque type vivent dans la table fille correspondante (DocumentGenere,
    DocumentEmail) — voir app/repositories/documents.py."""

    id: int
    dossier_id: int
    type_document: str
    titre: str
    chemin_fichier: str
    document_origine_id: int | None
    cree_par: int | None
    cree_le: datetime


@dataclass
class DocumentGenere:
    """Spécialisation de Document pour type_document == 'genere' : garde le
    modèle Typst utilisé et le .typ fusionné, que l'utilisateur peut
    retélécharger pour le personnaliser localement."""

    document_id: int
    modele_slug: str
    chemin_typ: str


@dataclass
class DocumentEmail:
    """Spécialisation de Document pour type_document == 'email'. message_id
    sert au dédoublonnage lors des synchronisations IMAP répétées — voir
    app/repositories/documents.py pour le contrôle d'unicité par dossier."""

    document_id: int
    sens: str
    expediteur: str
    destinataires: str
    objet: str | None
    date_message: datetime
    message_id: str


@dataclass
class DocumentPiece:
    """Caractéristique optionnelle d'un document, de n'importe quel type :
    en fait une pièce (élément de preuve) communicable. numero_piece est
    nullable tant que la pièce n'a pas encore été formellement communiquée."""

    document_id: int
    numero_piece: str | None
    contact_provenance_id: int
    date_transmission: date | None
    utilisee: bool


@dataclass
class DocumentListe:
    """Vue composite d'un document pour son affichage en liste (fiche
    dossier, tableau de bord) : les champs des tables filles utiles à
    l'affichage, aplatis, plus date_tri — la date de référence pour le tri
    (date_message pour un e-mail, date_transmission pour une pièce quand
    elle est renseignée, cree_le sinon), calculée par la requête et jamais
    stockée. Voir app/repositories/documents.py::lister_pour_dossier."""

    id: int
    dossier_id: int
    type_document: str
    titre: str
    chemin_fichier: str
    cree_le: datetime
    date_tri: datetime
    est_piece: bool
    numero_piece: str | None


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
    document_id: int | None


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
