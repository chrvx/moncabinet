-- cree table categorie matiere
-- depends: 0019.remplace-categorie-echeance-par-table-dediee

-- CATEGORIE_MATIERE : regroupe les matières par grande famille de droit
-- (Droit de la famille, Droit immobilier...) pour l'affichage groupé du
-- menu "Matière" du dossier — référentiel modifiable comme matiere/
-- categorie_echeance, donc avec actif plutôt qu'une liste figée.
CREATE TABLE categorie_matiere (
    id serial PRIMARY KEY,
    libelle text NOT NULL UNIQUE,
    actif boolean NOT NULL DEFAULT true
);

INSERT INTO categorie_matiere (libelle) VALUES
    ('Droit de la famille'),
    ('Droit immobilier'),
    ('Droit du travail'),
    ('Droit des sociétés'),
    ('Droit pénal'),
    ('Autre');

-- Nullable, contrairement à categorie_echeance (migration 0019) : les
-- matières existantes ont pu être ajoutées librement depuis l'écran
-- d'administration au fil du temps et ne peuvent pas toutes être rattachées
-- automatiquement à une catégorie de façon fiable. Seules les deux matières
-- historiques de la migration 0008 sont rattachées ci-dessous ; les autres
-- restent NULL ("non classée" côté écran d'administration) et se classent
-- manuellement depuis parametres/matieres. La catégorie n'est obligatoire
-- qu'à la création d'une nouvelle matière, imposé par NouvelleMatiereForm
-- (validateur applicatif), pas par le schéma.
ALTER TABLE matiere ADD COLUMN categorie_id integer REFERENCES categorie_matiere(id);

UPDATE matiere SET categorie_id = (SELECT id FROM categorie_matiere WHERE libelle = 'Droit immobilier')
WHERE libelle = 'Droit immobilier';
UPDATE matiere SET categorie_id = (SELECT id FROM categorie_matiere WHERE libelle = 'Droit de la famille')
WHERE libelle = 'Divorce par consentement mutuel';
