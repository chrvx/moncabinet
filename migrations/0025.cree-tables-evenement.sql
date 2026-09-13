-- cree tables evenement
-- depends: 0024.supprime-modeles-echeance

-- Table de référence, éditable depuis parametres/ — même principe que
-- categorie_echeance (voir migration 0019).
CREATE TABLE type_evenement (
    id serial PRIMARY KEY,
    libelle text NOT NULL UNIQUE,
    actif boolean NOT NULL DEFAULT true
);

INSERT INTO type_evenement (libelle) VALUES
    ('Rendez-vous'),
    ('Entretien téléphonique'),
    ('Audience'),
    ('Autre');

-- Ce qui s'est passé sur un dossier, par opposition à ce qui est prévu
-- (echeance). contenu est NOT NULL sans exception. Pas de suppression :
-- annulation réversible et tracée (annule_le/annule_par/motif_annulation)
-- sur le modèle du flag douteux déjà utilisé sur les coordonnées.
CREATE TABLE evenement (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL REFERENCES dossier(id),
    type_evenement_id integer NOT NULL REFERENCES type_evenement(id),
    date_evenement date NOT NULL,
    duree_minutes integer
        CHECK (duree_minutes IS NULL OR duree_minutes > 0),
    contenu text NOT NULL
        CHECK (btrim(contenu) <> ''),
    -- Rempli quand l'événement vient clôturer une échéance prévue
    -- (audience, rdv planifié) ; NULL pour un appel imprévu.
    echeance_id integer REFERENCES echeance(id),
    -- Rempli si un compte-rendu écrit a été généré a posteriori à partir
    -- de cet événement (usage futur, pas nécessaire au départ).
    document_id integer REFERENCES document(id),
    -- Annulation réversible : les trois colonnes vont ensemble (voir
    -- CHECK ci-dessous) ; motif_annulation reste facultatif même en cas
    -- d'annulation, pour ne pas alourdir un geste qui doit rester rapide.
    annule_le timestamptz,
    annule_par integer REFERENCES utilisateur(id),
    motif_annulation text,
    CHECK ((annule_le IS NULL) = (annule_par IS NULL)),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    -- Reflète toujours la DERNIÈRE écriture uniquement — voir
    -- evenement_historique ci-dessous pour les versions intermédiaires.
    -- Affiché à l'écran (pas seulement stocké) : une correction ne doit
    -- jamais passer inaperçue.
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);

-- Historique complet : une copie de la ligne evenement est insérée ici
-- juste AVANT chaque écriture qui la modifie (contenu, type, date, durée,
-- dossier de rattachement, annulation, réactivation) — un seul mécanisme
-- pour tous les cas, appliqué en code Python (voir
-- app/repositories/evenements.py), pas par trigger. modifie_par/modifie_le
-- identifient qui a produit ce changement et quand ; les colonnes
-- restantes sont l'état de la ligne juste avant ce changement.
CREATE TABLE evenement_historique (
    id serial PRIMARY KEY,
    evenement_id integer NOT NULL REFERENCES evenement(id),
    dossier_id integer NOT NULL,
    type_evenement_id integer NOT NULL,
    date_evenement date NOT NULL,
    duree_minutes integer,
    contenu text NOT NULL,
    annule_le timestamptz,
    annule_par integer REFERENCES utilisateur(id),
    motif_annulation text,
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz NOT NULL DEFAULT now()
);
