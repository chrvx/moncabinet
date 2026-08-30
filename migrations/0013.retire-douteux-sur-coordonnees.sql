-- retire douteux sur coordonnees
-- depends: 0012.rend-contact-lie-obligatoire-pour-avocat

-- Retrait du signalement "douteux" ajouté en 0007 : fonctionnalité
-- abandonnée à la demande du cabinet.
ALTER TABLE contact_adresse DROP COLUMN douteux;
ALTER TABLE contact_telephone DROP COLUMN douteux;
ALTER TABLE contact_email DROP COLUMN douteux;
