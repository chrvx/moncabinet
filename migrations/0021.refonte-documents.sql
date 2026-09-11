-- refonte documents
-- depends: 0020.cree-table-categorie-matiere

-- Remplace dossier_document (migration 0016), spécifique aux documents
-- générés par fusion Typst, par un modèle capable d'accueillir aussi les
-- e-mails importés et les fichiers déposés. Voir
-- docs/phase-documents-correspondance.md §2-3 pour la discussion de
-- modélisation.
--
-- Reprend le patron d'héritage de contact / personne_physique /
-- personne_morale (migration 0003) : UNIQUE (id, type_document) sur la
-- mère, CHECK figeant le type sur chaque fille, clé étrangère composite.
-- Rien n'est en production : aucune donnée à transférer.
DROP TABLE dossier_document;

CREATE TABLE document (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL REFERENCES dossier(id),
    type_document text NOT NULL
        CHECK (type_document IN ('genere', 'email', 'depose')),
    titre text NOT NULL,
    -- Chemin du fichier principal, quel que soit le type : le PDF pour un
    -- document généré, le .eml pour un e-mail, le fichier uploadé pour un
    -- document déposé. Porté par la mère pour éviter de répéter la même
    -- colonne dans chaque fille.
    chemin_fichier text NOT NULL,
    -- Document dont celui-ci est issu : typiquement l'e-mail dont il a été
    -- extrait comme pièce jointe. Permet de répondre à « ce document, vous
    -- me l'avez transmis quand ? » en remontant à document_email.date_message.
    document_origine_id integer REFERENCES document(id),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, type_document)
);

CREATE TABLE document_genere (
    document_id integer PRIMARY KEY,
    type_document text NOT NULL DEFAULT 'genere'
        CHECK (type_document = 'genere'),
    modele_slug text NOT NULL,
    chemin_typ text NOT NULL,
    FOREIGN KEY (document_id, type_document)
        REFERENCES document (id, type_document)
);

CREATE TABLE document_email (
    document_id integer PRIMARY KEY,
    type_document text NOT NULL DEFAULT 'email'
        CHECK (type_document = 'email'),
    sens text NOT NULL CHECK (sens IN ('recu', 'envoye')),
    expediteur text NOT NULL,
    destinataires text NOT NULL,
    objet text,
    -- Date de l'en-tête Date: du message, pas la date d'import.
    date_message timestamptz NOT NULL,
    -- En-tête Message-ID, identifiant unique attribué par le serveur
    -- d'envoi. Sert au dédoublonnage lors des synchronisations répétées.
    -- PAS de contrainte UNIQUE globale : un même message peut légitimement
    -- concerner deux dossiers (client ayant deux affaires en cours). Le
    -- contrôle d'unicité porte sur le couple (message_id, dossier_id) et se
    -- fait dans le repository par jointure sur document, dossier_id vivant
    -- sur la table mère.
    message_id text NOT NULL,
    FOREIGN KEY (document_id, type_document)
        REFERENCES document (id, type_document)
);

CREATE INDEX idx_document_email_message_id ON document_email (message_id);

-- Caractéristique optionnelle, applicable à un document de n'importe quel
-- type. Volontairement SANS clé étrangère composite : ce n'est pas une
-- spécialisation exclusive mais un attribut qui s'ajoute.
CREATE TABLE document_piece (
    document_id integer PRIMARY KEY REFERENCES document(id),
    -- Attribué seulement au moment de la communication formelle, d'où le
    -- caractère nullable. Texte et non entier : la numérotation réelle
    -- comporte des variantes (3 bis, 4-1...).
    numero_piece text,
    contact_provenance_id integer NOT NULL REFERENCES contact(id),
    -- Date à laquelle la pièce a été transmise au cabinet. Distincte de
    -- document.cree_le, qui n'est que la date d'import du fichier.
    -- Préremplie depuis document_origine → document_email.date_message
    -- quand la pièce vient d'un e-mail, saisie à la main sinon.
    date_transmission date,
    utilisee boolean NOT NULL DEFAULT false
);
