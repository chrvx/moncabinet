-- rollback retire unicite siren personne morale
ALTER TABLE personne_morale ADD CONSTRAINT personne_morale_siren_key UNIQUE (siren);
