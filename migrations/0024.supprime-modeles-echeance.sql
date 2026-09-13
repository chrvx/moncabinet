-- supprime modeles echeance
-- depends: 0023.retire-unicite-siren-personne-morale

-- Retrait de la fonctionnalité de catalogue de délais suggérés par matière
-- (voir 0017) : jugée peu utile à l'usage. Les échéances elles-mêmes
-- (table echeance) et categorie_echeance ne sont pas concernées.
--
-- CASCADE emporte matiere_modele_document et matiere_modele_email : deux
-- tables jamais introduites par une migration ni utilisées par le code
-- (déclenchement de document/e-mail depuis un modèle d'échéance,
-- expérimenté directement en base), qui référençaient matiere_modele_echeance
-- via declenche_par_modele_id.
DROP TABLE matiere_modele_echeance CASCADE;
