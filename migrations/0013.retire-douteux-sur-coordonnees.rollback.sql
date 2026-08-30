-- rollback: retire douteux sur coordonnees

ALTER TABLE contact_adresse ADD COLUMN douteux boolean NOT NULL DEFAULT false;
ALTER TABLE contact_telephone ADD COLUMN douteux boolean NOT NULL DEFAULT false;
ALTER TABLE contact_email ADD COLUMN douteux boolean NOT NULL DEFAULT false;
