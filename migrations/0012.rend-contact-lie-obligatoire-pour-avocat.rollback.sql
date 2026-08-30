-- rollback: rend contact lie obligatoire pour avocat

UPDATE type_role SET contact_lie_regle = 'optionnel' WHERE libelle = 'avocat';
