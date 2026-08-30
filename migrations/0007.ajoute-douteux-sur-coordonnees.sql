-- ajoute douteux sur coordonnees
-- depends: 0006.cree-tables-telephone-email

-- Une coordonnée "douteuse" (courrier retourné, "ligne non attribuée" au
-- téléphone...) reste active et visible tant qu'on ne connaît pas la
-- nouvelle valeur : c'est un avertissement, pas une clôture. Elle ne quitte
-- l'historique actif que via terminer_lien_* comme avant. modifie_par /
-- modifie_le, déjà présentes, suffisent à savoir qui a signalé le doute et
-- quand.
ALTER TABLE contact_adresse ADD COLUMN douteux boolean NOT NULL DEFAULT false;
ALTER TABLE contact_telephone ADD COLUMN douteux boolean NOT NULL DEFAULT false;
ALTER TABLE contact_email ADD COLUMN douteux boolean NOT NULL DEFAULT false;
