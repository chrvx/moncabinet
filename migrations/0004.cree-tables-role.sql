-- cree tables role
-- depends: 0003.cree-tables-contact-personne-physique-morale

-- TYPE_ROLE est une table de référence (pas un CHECK ni un ENUM) car,
-- contrairement à pays/departement/civilite, ce vocabulaire est propre au
-- cabinet et vous l'étendrez vous-même au fil du temps (notaire, expert...).
-- dossier_regle et contact_lie_regle pilotent la validation applicative :
-- pour un rôle donné, dossier_id et contact_lie_id sur role_contact
-- doivent-ils être renseignés, facultatifs, ou absents.
CREATE TABLE type_role (
    id serial PRIMARY KEY,
    libelle text NOT NULL UNIQUE,
    dossier_regle text NOT NULL
        CHECK (dossier_regle IN ('obligatoire', 'optionnel', 'interdit')),
    contact_lie_regle text NOT NULL
        CHECK (contact_lie_regle IN ('obligatoire', 'optionnel', 'interdit'))
);

INSERT INTO type_role (libelle, dossier_regle, contact_lie_regle) VALUES
    ('client', 'optionnel', 'interdit'),
    ('adversaire', 'obligatoire', 'interdit'),
    ('avocat', 'optionnel', 'optionnel'),
    ('enfant', 'optionnel', 'obligatoire'),
    ('demandeur', 'obligatoire', 'interdit'),
    ('défendeur', 'obligatoire', 'interdit');

-- dossier_id n'a volontairement PAS de contrainte de clé étrangère : la
-- table dossier n'existe pas encore (phase 3). La colonne est déjà là pour
-- ne pas avoir à modifier cette table plus tard ; la contrainte
-- "REFERENCES dossier(id)" sera ajoutée par une migration ALTER TABLE une
-- fois dossier créée.
CREATE TABLE role_contact (
    id serial PRIMARY KEY,
    contact_id integer NOT NULL REFERENCES contact(id),
    type_role_id integer NOT NULL REFERENCES type_role(id),
    dossier_id integer,
    contact_lie_id integer REFERENCES contact(id),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);
