-- cree tables dossier matiere
-- depends: 0007.ajoute-douteux-sur-coordonnees

-- MATIERE : référentiel modifiable (contrairement à pays/departement/
-- civilite), donc avec actif pour retirer une matière obsolète sans casser
-- l'historique des dossiers qui la référencent déjà.
CREATE TABLE matiere (
    id serial PRIMARY KEY,
    libelle text NOT NULL UNIQUE,
    actif boolean NOT NULL DEFAULT true
);

INSERT INTO matiere (libelle) VALUES
    ('Droit immobilier'),
    ('Divorce par consentement mutuel');

-- Un compteur par année : la référence YYNNN est calculée à l'ouverture du
-- dossier (pas à sa création en brouillon), voir la fonction ouvrir() du
-- repository. dernier_numero représente le plus haut numéro réellement
-- utilisé, qu'il vienne de la suggestion automatique ou d'une correction
-- manuelle (reprise d'un dossier déjà existant hors application).
CREATE TABLE compteur_dossier (
    annee integer PRIMARY KEY,
    dernier_numero integer NOT NULL
);

-- reference est nullable : un brouillon n'en a pas encore. categorie est
-- une distinction fixe (juridique/judiciaire), donc une contrainte CHECK
-- plutôt qu'une table de référence, contrairement à matiere.
CREATE TABLE dossier (
    id serial PRIMARY KEY,
    reference text UNIQUE,
    statut text NOT NULL DEFAULT 'brouillon'
        CHECK (statut IN ('brouillon', 'ouvert', 'clos')),
    categorie text
        CHECK (categorie IN ('juridique', 'judiciaire')),
    matiere_id integer REFERENCES matiere(id),
    date_ouverture date,
    date_cloture date,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);

-- La contrainte laissée en attente depuis la phase 2 (role_contact.dossier_id
-- existait déjà, sans référence vers une table dossier qui n'existait pas
-- encore) se referme enfin ici.
ALTER TABLE role_contact
    ADD CONSTRAINT role_contact_dossier_id_fkey
    FOREIGN KEY (dossier_id) REFERENCES dossier(id);
