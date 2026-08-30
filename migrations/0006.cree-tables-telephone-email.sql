-- cree tables telephone email
-- depends: 0005.cree-tables-adresse

-- Même principe que pour l'adresse (valeur + table de liaison datée), en
-- plus simple : une seule colonne de valeur suffit, pas de mention de
-- destinataire (on n'a pas identifié de besoin équivalent au "chez untel"
-- pour un numéro ou une boîte mail).
CREATE TABLE telephone (
    id serial PRIMARY KEY,
    numero text NOT NULL,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE contact_telephone (
    id serial PRIMARY KEY,
    contact_id integer NOT NULL REFERENCES contact(id),
    telephone_id integer NOT NULL REFERENCES telephone(id),
    date_debut date NOT NULL DEFAULT current_date,
    date_fin date,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);

CREATE TABLE email (
    id serial PRIMARY KEY,
    adresse_email text NOT NULL,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE contact_email (
    id serial PRIMARY KEY,
    contact_id integer NOT NULL REFERENCES contact(id),
    email_id integer NOT NULL REFERENCES email(id),
    date_debut date NOT NULL DEFAULT current_date,
    date_fin date,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);
