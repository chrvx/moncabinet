-- cree tables adresse
-- depends: 0004.cree-tables-role

-- ADRESSE porte la valeur brute, structurée selon les 6 lignes de la norme
-- postale française (les colonnes ci-dessous correspondent aux lignes 2 à
-- 6 ; la ligne 1, l'identité du destinataire, vient du contact lui-même et
-- n'est donc pas stockée ici). mention_distribution_type couvre les
-- lignes 5 spéciales (BP/TSA/CS/lieu-dit) ; code_cedex et numero_cedex
-- couvrent le format CEDEX de la ligne 6, distinct du code postal
-- classique. pays_id ne sert que pour une adresse à l'étranger (ligne 7) ;
-- NULL signifie France par convention.
--
-- CONTACT_ADRESSE relie un contact à une adresse pour une période donnée
-- (date_debut/date_fin). Une même ligne ADRESSE peut être partagée par
-- plusieurs contacts (un couple au même domicile) : chacun a sa propre
-- ligne CONTACT_ADRESSE, donc sa propre période et sa propre mention de
-- destinataire ("chez untel", "service juridique"...), qui ne concerne que
-- ce contact-là et non l'adresse elle-même.
CREATE TABLE adresse (
    id serial PRIMARY KEY,
    complement text,
    entree_batiment text,
    numero_voie text,
    libelle_voie text,
    mention_distribution_type text
        CHECK (mention_distribution_type IN ('BP', 'TSA', 'CS', 'LIEU_DIT')),
    mention_distribution_valeur text,
    code_postal text,
    code_cedex text,
    numero_cedex text,
    commune text,
    pays_id char(2) REFERENCES pays(code_iso),
    code_insee_commune text,
    latitude double precision,
    longitude double precision,
    libelle_complet_ban text,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE contact_adresse (
    id serial PRIMARY KEY,
    contact_id integer NOT NULL REFERENCES contact(id),
    adresse_id integer NOT NULL REFERENCES adresse(id),
    mention_destinataire text,
    date_debut date NOT NULL DEFAULT current_date,
    date_fin date,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz
);
