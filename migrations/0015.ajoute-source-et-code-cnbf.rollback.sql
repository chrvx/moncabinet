ALTER TABLE avocat DROP COLUMN code_cnbf;

ALTER TABLE contact_adresse DROP COLUMN source;

ALTER TABLE contact_telephone
    DROP COLUMN source,
    DROP COLUMN valeur_annuaire_divergente,
    DROP COLUMN constatee_le;

ALTER TABLE contact_email
    DROP COLUMN source,
    DROP COLUMN valeur_annuaire_divergente,
    DROP COLUMN constatee_le;
