-- remplace categorie echeance par table dediee
-- depends: 0018.ajoute-modeles-echeance-appel-et-divorce

-- La liste des catégories d'échéance (Audience, Délai de procédure...) doit
-- pouvoir être complétée par le cabinet sans modification de code : comme
-- matiere, categorie devient une table de référence éditable depuis
-- parametres/ plutôt qu'une liste figée par CHECK.
CREATE TABLE categorie_echeance (
    id serial PRIMARY KEY,
    libelle text NOT NULL UNIQUE,
    actif boolean NOT NULL DEFAULT true
);

INSERT INTO categorie_echeance (libelle) VALUES
    ('Audience'),
    ('Délai de procédure'),
    ('Rappel'),
    ('Calendrier de procédure'),
    ('Autre');

ALTER TABLE echeance ADD COLUMN categorie_id integer REFERENCES categorie_echeance(id);
UPDATE echeance SET categorie_id = ce.id
FROM categorie_echeance ce
WHERE ce.libelle = CASE echeance.categorie
    WHEN 'audience' THEN 'Audience'
    WHEN 'delai_procedure' THEN 'Délai de procédure'
    WHEN 'rappel' THEN 'Rappel'
    WHEN 'calendrier_procedure' THEN 'Calendrier de procédure'
    WHEN 'autre' THEN 'Autre'
END;
ALTER TABLE echeance ALTER COLUMN categorie_id SET NOT NULL;
ALTER TABLE echeance DROP COLUMN categorie;

ALTER TABLE matiere_modele_echeance ADD COLUMN categorie_id integer REFERENCES categorie_echeance(id);
UPDATE matiere_modele_echeance SET categorie_id = ce.id
FROM categorie_echeance ce
WHERE ce.libelle = CASE matiere_modele_echeance.categorie
    WHEN 'audience' THEN 'Audience'
    WHEN 'delai_procedure' THEN 'Délai de procédure'
    WHEN 'rappel' THEN 'Rappel'
    WHEN 'calendrier_procedure' THEN 'Calendrier de procédure'
    WHEN 'autre' THEN 'Autre'
END;
ALTER TABLE matiere_modele_echeance ALTER COLUMN categorie_id SET NOT NULL;
ALTER TABLE matiere_modele_echeance DROP COLUMN categorie;
