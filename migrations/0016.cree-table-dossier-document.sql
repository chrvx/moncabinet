-- cree table dossier_document
-- depends: 0015.ajoute-source-et-code-cnbf

-- Trace chaque document généré (courrier, acte...) par fusion d'un modèle
-- Typst avec les données d'un dossier — voir app/services/generation_documents.py.
-- modele_slug référence un répertoire sous app/documents_modeles/, pas une
-- ligne de table : les modèles sont des fichiers gérés directement sur le
-- serveur par un utilisateur technique (pas d'écran d'upload), donc rien à
-- normaliser en base au-delà de ce nom.
--
-- chemin_pdf et chemin_typ sont des chemins relatifs à instance/ (voir
-- app.instance_path) : le PDF final et le source .typ fusionné (données
-- déjà injectées), que l'utilisateur peut retélécharger pour le
-- personnaliser localement avec son propre outillage Typst.
CREATE TABLE dossier_document (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL REFERENCES dossier(id),
    modele_slug text NOT NULL,
    titre text NOT NULL,
    chemin_pdf text NOT NULL,
    chemin_typ text NOT NULL,
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now()
);
