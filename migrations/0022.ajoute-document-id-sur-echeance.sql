-- ajoute document_id sur echeance
-- depends: 0021.refonte-documents

-- Une échéance peut naître d'un document : un e-mail annonçant un délai, un
-- jugement scanné qui fait courir un recours. Le lien répond à « pourquoi ce
-- délai existe-t-il ? » en un clic depuis l'échéance.
--
-- Nullable, et posé sur la mère document (pas sur document_email) : un
-- document déposé peut tout autant faire courir un délai.
ALTER TABLE echeance
    ADD COLUMN document_id integer REFERENCES document(id);
