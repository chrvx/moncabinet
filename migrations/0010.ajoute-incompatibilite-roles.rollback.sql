-- rollback: ajoute incompatibilite roles

DROP TABLE type_role_incompatible;

ALTER TABLE type_role DROP COLUMN exclusif;
