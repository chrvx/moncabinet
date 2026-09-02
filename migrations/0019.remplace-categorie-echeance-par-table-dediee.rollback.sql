-- rollback: remplace categorie echeance par table dediee

-- Toute catégorie ajoutée depuis l'écran d'administration (donc absente des
-- cinq valeurs d'origine) retombe sur 'autre' plutôt que de faire échouer
-- le rollback.
ALTER TABLE matiere_modele_echeance ADD COLUMN categorie text;
UPDATE matiere_modele_echeance SET categorie = CASE ce.libelle
    WHEN 'Audience' THEN 'audience'
    WHEN 'Délai de procédure' THEN 'delai_procedure'
    WHEN 'Rappel' THEN 'rappel'
    WHEN 'Calendrier de procédure' THEN 'calendrier_procedure'
    WHEN 'Autre' THEN 'autre'
    ELSE 'autre'
END
FROM categorie_echeance ce
WHERE ce.id = matiere_modele_echeance.categorie_id;
ALTER TABLE matiere_modele_echeance ALTER COLUMN categorie SET NOT NULL;
ALTER TABLE matiere_modele_echeance ADD CONSTRAINT matiere_modele_echeance_categorie_check
    CHECK (categorie IN ('audience', 'delai_procedure', 'rappel', 'calendrier_procedure', 'autre'));
ALTER TABLE matiere_modele_echeance DROP COLUMN categorie_id;

ALTER TABLE echeance ADD COLUMN categorie text;
UPDATE echeance SET categorie = CASE ce.libelle
    WHEN 'Audience' THEN 'audience'
    WHEN 'Délai de procédure' THEN 'delai_procedure'
    WHEN 'Rappel' THEN 'rappel'
    WHEN 'Calendrier de procédure' THEN 'calendrier_procedure'
    WHEN 'Autre' THEN 'autre'
    ELSE 'autre'
END
FROM categorie_echeance ce
WHERE ce.id = echeance.categorie_id;
ALTER TABLE echeance ALTER COLUMN categorie SET NOT NULL;
ALTER TABLE echeance ADD CONSTRAINT echeance_categorie_check
    CHECK (categorie IN ('audience', 'delai_procedure', 'rappel', 'calendrier_procedure', 'autre'));
ALTER TABLE echeance DROP COLUMN categorie_id;

DROP TABLE categorie_echeance;
