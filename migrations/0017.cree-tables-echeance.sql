-- cree tables echeance
-- depends: 0016.cree-table-dossier-document

-- Remplace le suivi papier des échéances (méthode des 43 dossiers) : chaque
-- audience, délai de procédure, rappel client ou entrée d'un calendrier de
-- procédure devient une ligne rattachée à un dossier. categorie est une
-- liste fixe plutôt qu'une table de référence : c'est un vocabulaire
-- structurel de l'application (filtrage/affichage), comme dossier.categorie
-- déjà ci-dessous, pas un vocabulaire métier extensible par l'utilisateur
-- comme type_role ou matiere.
CREATE TABLE echeance (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL REFERENCES dossier(id),
    categorie text NOT NULL
        CHECK (categorie IN ('audience', 'delai_procedure', 'rappel', 'calendrier_procedure', 'autre')),
    libelle text NOT NULL,
    date_echeance date NOT NULL,
    heure_echeance time,
    statut text NOT NULL DEFAULT 'a_faire'
        CHECK (statut IN ('a_faire', 'fait')),
    fait_le timestamptz,
    notes text,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);

-- Catalogue de délais suggérés par matière (ex: "Conclusions d'appelant" à
-- 90 jours pour la matière Appel). Table enfant de matiere, sur le même
-- principe que type_role : la règle (délai) est une donnée, lue
-- génériquement — ajouter ou modifier un délai pour une matière est une
-- simple migration de données (voir 0018), jamais une nouvelle branche dans
-- le code. delai_jours se compte à partir de dossier.date_ouverture ; la
-- date proposée reste modifiable par l'utilisateur avant enregistrement
-- (voir app/blueprints/dossiers/routes.py), pour les cas où le point de
-- départ réel diffère (ex: date de la déclaration d'appel).
CREATE TABLE matiere_modele_echeance (
    id serial PRIMARY KEY,
    matiere_id integer NOT NULL REFERENCES matiere(id),
    libelle text NOT NULL,
    categorie text NOT NULL
        CHECK (categorie IN ('audience', 'delai_procedure', 'rappel', 'calendrier_procedure', 'autre')),
    delai_jours integer NOT NULL,
    actif boolean NOT NULL DEFAULT true
);
