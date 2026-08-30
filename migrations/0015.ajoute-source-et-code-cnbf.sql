-- ajoute source et code cnbf
-- depends: 0014.cree-tables-qualification-professionnelle

-- Support de la synchronisation avec l'Annuaire des avocats de France
-- (data.gouv.fr) : voir app/services/annuaire_avocats.py.
--
-- `source` distingue une coordonnée saisie à la main d'une coordonnée
-- créée par l'import de l'annuaire, pour qu'une resynchronisation ne
-- puisse jamais écraser silencieusement une correction manuelle :
-- - source = 'import_annuaire' : la resynchronisation peut mettre à jour
--   librement (personne n'a validé cette valeur à la main) ;
-- - source = 'manuel' : la resynchronisation ne touche jamais la valeur,
--   elle consigne seulement un écart éventuel dans
--   valeur_annuaire_divergente/constatee_le pour affichage sur la fiche
--   contact, effacé dès que l'utilisateur corrige la valeur ou que
--   l'écart disparaît lors d'un import suivant.
--
-- Valeur par défaut 'manuel' pour les lignes existantes : toutes ont été
-- saisies à la main jusqu'ici, avant l'existence de cet import.
ALTER TABLE contact_email
    ADD COLUMN source text NOT NULL DEFAULT 'manuel'
        CHECK (source IN ('manuel', 'import_annuaire')),
    ADD COLUMN valeur_annuaire_divergente text,
    ADD COLUMN constatee_le date;

ALTER TABLE contact_telephone
    ADD COLUMN source text NOT NULL DEFAULT 'manuel'
        CHECK (source IN ('manuel', 'import_annuaire')),
    ADD COLUMN valeur_annuaire_divergente text,
    ADD COLUMN constatee_le date;

ALTER TABLE contact_adresse
    ADD COLUMN source text NOT NULL DEFAULT 'manuel'
        CHECK (source IN ('manuel', 'import_annuaire'));

-- Identifiant CNBF (numéro de toque national), stable et unique par
-- avocat dans l'annuaire : sert de clé de rapprochement pour la
-- détection de doublons lors de l'import/resynchronisation, à la place
-- d'un matching approximatif sur le nom et le prénom.
ALTER TABLE avocat ADD COLUMN code_cnbf text UNIQUE;
