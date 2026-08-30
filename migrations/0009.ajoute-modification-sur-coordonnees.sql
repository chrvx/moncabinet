-- ajoute modification sur coordonnees
-- depends: 0008.cree-tables-dossier-matiere

-- Permet de corriger une faute de frappe sur une adresse/téléphone/email en
-- place (UPDATE de la ligne elle-même), sans passer par une clôture puis un
-- nouvel ajout : contrairement à un déménagement ou un changement de
-- numéro, une simple correction ne doit pas apparaître comme un changement
-- dans l'historique du lien contact_adresse/telephone/email (date_fin puis
-- nouvelle période). Comme la ligne peut être partagée entre plusieurs
-- contacts, la correction s'applique à tous ceux qui la partagent.
ALTER TABLE adresse
    ADD COLUMN modifie_par integer REFERENCES utilisateur(id),
    ADD COLUMN modifie_le timestamptz;

ALTER TABLE telephone
    ADD COLUMN modifie_par integer REFERENCES utilisateur(id),
    ADD COLUMN modifie_le timestamptz;

ALTER TABLE email
    ADD COLUMN modifie_par integer REFERENCES utilisateur(id),
    ADD COLUMN modifie_le timestamptz;
