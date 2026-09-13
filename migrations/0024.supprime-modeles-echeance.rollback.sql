-- rollback supprime modeles echeance

-- Ne restaure que le schéma, pas les données emportées par le CASCADE
-- (voir la migration forward).
CREATE TABLE matiere_modele_echeance (
    id serial PRIMARY KEY,
    matiere_id integer NOT NULL REFERENCES matiere(id),
    libelle text NOT NULL,
    categorie_id integer NOT NULL REFERENCES categorie_echeance(id),
    delai_jours integer NOT NULL,
    actif boolean NOT NULL DEFAULT true
);

CREATE TABLE matiere_modele_document (
    id serial PRIMARY KEY,
    matiere_id integer NOT NULL REFERENCES matiere(id),
    ordre integer NOT NULL,
    modele_slug text NOT NULL,
    libelle text NOT NULL,
    declenche_par_modele_id integer REFERENCES matiere_modele_echeance(id),
    actif boolean NOT NULL DEFAULT true
);

CREATE TABLE matiere_modele_email (
    id serial PRIMARY KEY,
    matiere_id integer NOT NULL REFERENCES matiere(id),
    ordre integer NOT NULL,
    libelle text NOT NULL,
    sujet text NOT NULL,
    corps text NOT NULL,
    declenche_par_modele_id integer REFERENCES matiere_modele_echeance(id),
    actif boolean NOT NULL DEFAULT true
);
