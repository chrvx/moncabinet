-- rollback: ajoute modeles echeance appel et divorce

-- On ne supprime pas la matière "Appel" elle-même : de vrais dossiers
-- peuvent déjà la référencer au moment du rollback.
DELETE FROM matiere_modele_echeance
WHERE (libelle, categorie, delai_jours) IN (
    ('Conclusions d''appelant', 'delai_procedure', 90),
    ('Relancer le client', 'rappel', 30)
);
