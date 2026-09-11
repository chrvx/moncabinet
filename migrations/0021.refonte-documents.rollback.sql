DROP TABLE document_piece;
DROP INDEX idx_document_email_message_id;
DROP TABLE document_email;
DROP TABLE document_genere;
DROP TABLE document;

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
