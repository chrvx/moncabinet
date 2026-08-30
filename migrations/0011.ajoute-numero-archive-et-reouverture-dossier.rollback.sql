-- rollback: ajoute numero archive et reouverture dossier

ALTER TABLE dossier DROP COLUMN numero_archive;
