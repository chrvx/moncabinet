-- rend contact lie obligatoire pour avocat
-- depends: 0011.ajoute-numero-archive-et-reouverture-dossier

-- Un avocat intervenant sur un dossier représente toujours quelqu'un
-- (le client, l'adversaire...) : contact_lie_id ne doit donc plus être
-- optionnel pour ce rôle. La validation elle-même (_valider_regle dans
-- app/repositories/roles.py) est déjà générique et lit cette colonne : rien
-- à changer côté code, seule la donnée était incorrecte.
UPDATE type_role SET contact_lie_regle = 'obligatoire' WHERE libelle = 'avocat';
