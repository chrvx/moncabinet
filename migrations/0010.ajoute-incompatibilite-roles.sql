-- ajoute incompatibilite roles
-- depends: 0009.ajoute-modification-sur-coordonnees

-- Certains rôles ne peuvent pas être cumulés par un même contact sur un
-- même dossier. Deux mécanismes, en donnée plutôt qu'en code branché sur
-- le libellé du rôle (même logique que dossier_regle/contact_lie_regle) :
--   - exclusif : ce rôle ne tolère aucun autre rôle pour le même contact
--     sur le même dossier (avocat, enfant) ;
--   - type_role_incompatible : paires de rôles spécifiquement incompatibles
--     entre eux (client / adversaire), sans être exclusifs vis-à-vis du
--     reste (un client peut très bien être aussi demandeur).
ALTER TABLE type_role ADD COLUMN exclusif boolean NOT NULL DEFAULT false;

UPDATE type_role SET exclusif = true WHERE libelle IN ('avocat', 'enfant');

CREATE TABLE type_role_incompatible (
    type_role_id_1 integer NOT NULL REFERENCES type_role(id),
    type_role_id_2 integer NOT NULL REFERENCES type_role(id),
    CHECK (type_role_id_1 < type_role_id_2),
    PRIMARY KEY (type_role_id_1, type_role_id_2)
);

INSERT INTO type_role_incompatible (type_role_id_1, type_role_id_2)
SELECT least(c.id, a.id), greatest(c.id, a.id)
FROM type_role c, type_role a
WHERE c.libelle = 'client' AND a.libelle = 'adversaire';
