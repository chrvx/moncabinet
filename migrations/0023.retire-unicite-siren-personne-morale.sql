-- retire unicite siren personne morale
-- depends: 0022.ajoute-document-id-sur-echeance

-- Une structure nationale (ex: FIDAL) peut avoir plusieurs bureaux, donc
-- plusieurs contacts personne_morale distincts (chacun avec sa propre
-- adresse/téléphone), partageant pourtant le même SIREN (identifiant de
-- l'entité juridique, pas de l'établissement). La contrainte UNIQUE
-- empêchait de modéliser ce cas — voir _resoudre_cabinet dans
-- app/services/import_avocats.py, qui rapproche désormais un cabinet par
-- (siren, ville) plutôt que par siren seul.
ALTER TABLE personne_morale DROP CONSTRAINT personne_morale_siren_key;
