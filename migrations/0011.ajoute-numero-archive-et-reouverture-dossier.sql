-- ajoute numero archive et reouverture dossier
-- depends: 0010.ajoute-incompatibilite-roles

-- Numéro d'archive généré à la clôture (format YYMMDDHHMM), distinct de la
-- référence (format YYNNN attribuée à l'ouverture) : il identifie le
-- classement physique/l'archivage, pas le dossier lui-même, et n'est donc
-- ni unique ni obligatoire (un dossier jamais clos n'en a pas).
ALTER TABLE dossier ADD COLUMN numero_archive text;
