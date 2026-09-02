-- ajoute modeles echeance appel et divorce
-- depends: 0017.cree-tables-echeance

-- Deux modèles d'échéance de démonstration pour amorcer le catalogue de
-- suggestions (voir parametres/ pour en ajouter d'autres). La matière
-- "Appel" n'existait pas encore : migrations/0008 ne seedait que "Droit
-- immobilier" et "Divorce par consentement mutuel".
INSERT INTO matiere (libelle) VALUES ('Appel')
    ON CONFLICT (libelle) DO NOTHING;

INSERT INTO matiere_modele_echeance (matiere_id, libelle, categorie, delai_jours)
SELECT id, 'Conclusions d''appelant', 'delai_procedure', 90
FROM matiere WHERE libelle = 'Appel';

INSERT INTO matiere_modele_echeance (matiere_id, libelle, categorie, delai_jours)
SELECT id, 'Relancer le client', 'rappel', 30
FROM matiere WHERE libelle = 'Divorce par consentement mutuel';
