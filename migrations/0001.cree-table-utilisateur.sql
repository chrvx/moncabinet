-- cree la table utilisateur
-- depends:

-- Les comptes de connexion à l'application (vous, un futur collaborateur,
-- les stagiaires). Le champ `role` pilote les permissions (phase 5) : pour
-- l'instant, un seul rôle ('avocat') est réellement utilisé.
-- `actif` permet de désactiver le compte d'un stagiaire parti sans supprimer
-- la ligne ni perdre l'historique (cree_par sur les futures tables).
-- `nom` sert à la fois d'affichage et d'identifiant de connexion : il doit
-- donc être unique (deux personnes du cabinet ne peuvent pas porter
-- exactement le même nom d'utilisateur).
CREATE TABLE utilisateur (
    id serial PRIMARY KEY,
    nom text NOT NULL UNIQUE,
    mot_de_passe_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('avocat', 'collaborateur', 'stagiaire')),
    actif boolean NOT NULL DEFAULT true,
    cree_le timestamptz NOT NULL DEFAULT now()
);
