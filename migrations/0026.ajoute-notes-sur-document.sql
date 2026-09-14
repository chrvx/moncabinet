-- ajoute notes sur document
-- depends: 0025.cree-tables-evenement

-- Note libre : « version retravaillée de la photo envoyée par le client »,
-- « communiquée le 12/04 », « pièce n°4 du bordereau adverse ». Sur la mère,
-- vaut pour les trois types — voir docs/phase-documents-correspondance.md §3.
ALTER TABLE document ADD COLUMN notes text;
