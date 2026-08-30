-- rollback: ajoute modification sur coordonnees

ALTER TABLE email
    DROP COLUMN modifie_par,
    DROP COLUMN modifie_le;

ALTER TABLE telephone
    DROP COLUMN modifie_par,
    DROP COLUMN modifie_le;

ALTER TABLE adresse
    DROP COLUMN modifie_par,
    DROP COLUMN modifie_le;
