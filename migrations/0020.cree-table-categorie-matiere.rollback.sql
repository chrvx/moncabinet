-- rollback: cree table categorie matiere

ALTER TABLE matiere DROP COLUMN categorie_id;
DROP TABLE categorie_matiere;
