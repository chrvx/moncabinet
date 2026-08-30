-- cree tables contact personne physique morale
-- depends: 0002.cree-tables-reference-pays-departement-civilite

-- CONTACT est le pivot commun à toute personne ou organisation inscrite au
-- cabinet (clients, adversaires, confrères, experts...). PERSONNE_PHYSIQUE
-- et PERSONNE_MORALE le spécialisent, un contact étant strictement l'un ou
-- l'autre, jamais les deux.
--
-- L'exclusivité est garantie sans trigger grâce à une astuce classique :
-- contact porte une contrainte UNIQUE sur (id, type_contact), et chaque
-- sous-table fixe sa propre colonne type_contact à une valeur unique via
-- CHECK, puis référence contact par une clé étrangère composite sur
-- (contact_id, type_contact). Il devient alors impossible d'insérer une
-- ligne personne_physique pour un contact dont le type_contact vaut
-- 'personne_morale' (la clé étrangère composite échouerait) — et donc
-- impossible qu'un même contact ait les deux à la fois.
CREATE TABLE contact (
    id serial PRIMARY KEY,
    type_contact text NOT NULL CHECK (type_contact IN ('personne_physique', 'personne_morale')),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz,
    UNIQUE (id, type_contact)
);

CREATE TABLE personne_physique (
    contact_id integer PRIMARY KEY,
    type_contact text NOT NULL DEFAULT 'personne_physique' CHECK (type_contact = 'personne_physique'),
    nom text NOT NULL,
    prenom text,
    prenoms_secondaires text,
    nom_usage text,
    genre text CHECK (genre IN ('M', 'F')),
    civilite_id text REFERENCES civilite(code),
    date_naissance date,
    ville_naissance text,
    departement_naissance_id text REFERENCES departement(code),
    pays_naissance_id char(2) REFERENCES pays(code_iso),
    nationalite_id char(2) REFERENCES pays(code_iso),
    profession text,
    siren text UNIQUE,
    FOREIGN KEY (contact_id, type_contact) REFERENCES contact (id, type_contact)
);

CREATE TABLE personne_morale (
    contact_id integer PRIMARY KEY,
    type_contact text NOT NULL DEFAULT 'personne_morale' CHECK (type_contact = 'personne_morale'),
    raison_sociale text NOT NULL,
    forme text,
    siren text UNIQUE,
    FOREIGN KEY (contact_id, type_contact) REFERENCES contact (id, type_contact)
);
