-- cree tables qualification professionnelle
-- depends: 0013.retire-douteux-sur-coordonnees

-- Une personne physique peut exercer une profession réglementée fixe
-- (avocat, notaire, commissaire de justice). Ceci est distinct de
-- TYPE_ROLE/ROLE_CONTACT : un rôle décrit qui joue quel rôle *dans un
-- dossier donné* (souvent l'avocat adverse), alors qu'ici on décrit une
-- qualification permanente du contact, indépendante de tout dossier.
--
-- Une table par profession (plutôt qu'une table générique) car chacune a
-- vocation à porter ses propres colonnes/contraintes métier au fil du
-- temps (numéro de toque, date de prestation de serment...). Les trois
-- professions sont mutuellement exclusives (un contact ne peut être à la
-- fois avocat et notaire) : QUALIFICATION_PROFESSIONNELLE porte cette
-- exclusivité par la même astuce que CONTACT/PERSONNE_PHYSIQUE/
-- PERSONNE_MORALE (migration 0003) — une contrainte UNIQUE sur
-- (contact_id, profession), et chaque table de profession référence cette
-- paire par une clé étrangère composite après avoir fixé sa propre colonne
-- profession par CHECK. Impossible dès lors d'avoir une ligne dans deux
-- tables de profession pour le même contact.
--
-- Chaque table ne peut qualifier qu'une personne physique (contact_id
-- référence personne_physique, jamais contact directement) ; le
-- cabinet/l'étude d'exercice, quand il existe, est une personne_morale
-- distincte référencée par cabinet_id/office_id/etude_id (optionnelle :
-- exercice individuel possible).
CREATE TABLE barreau (
    id serial PRIMARY KEY,
    libelle text NOT NULL UNIQUE,
    actif boolean NOT NULL DEFAULT true
);

CREATE TABLE qualification_professionnelle (
    contact_id integer PRIMARY KEY REFERENCES personne_physique(contact_id),
    profession text NOT NULL CHECK (profession IN ('avocat', 'notaire', 'commissaire_justice')),
    UNIQUE (contact_id, profession)
);

CREATE TABLE avocat (
    contact_id integer PRIMARY KEY,
    profession text NOT NULL DEFAULT 'avocat' CHECK (profession = 'avocat'),
    barreau_id integer REFERENCES barreau(id),
    cabinet_id integer REFERENCES personne_morale(contact_id),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz,
    FOREIGN KEY (contact_id, profession) REFERENCES qualification_professionnelle (contact_id, profession) ON DELETE CASCADE
);

CREATE TABLE notaire (
    contact_id integer PRIMARY KEY,
    profession text NOT NULL DEFAULT 'notaire' CHECK (profession = 'notaire'),
    office_id integer REFERENCES personne_morale(contact_id),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz,
    FOREIGN KEY (contact_id, profession) REFERENCES qualification_professionnelle (contact_id, profession) ON DELETE CASCADE
);

CREATE TABLE commissaire_justice (
    contact_id integer PRIMARY KEY,
    profession text NOT NULL DEFAULT 'commissaire_justice' CHECK (profession = 'commissaire_justice'),
    etude_id integer REFERENCES personne_morale(contact_id),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    modifie_par integer REFERENCES utilisateur(id),
    modifie_le timestamptz,
    FOREIGN KEY (contact_id, profession) REFERENCES qualification_professionnelle (contact_id, profession) ON DELETE CASCADE
);

-- Liste des 164 barreaux français (source : jeu de données "Annuaire des
-- avocats de France" du Conseil national des barreaux, data.gouv.fr,
-- constant à la date de cette migration). Un barreau porte le nom de sa
-- ville de rattachement, sauf quand il est seul dans son département : il
-- porte alors le nom du département (ex: "barreau de l'Aube", pas "barreau
-- de Troyes").
INSERT INTO barreau (libelle) VALUES
    ('barreau d''Agen'), ('barreau d''Aix-en-Provence'), ('barreau d''Ajaccio'),
    ('barreau d''Albertville'), ('barreau d''Albi'), ('barreau d''Alençon'),
    ('barreau d''Alès'), ('barreau d''Amiens'), ('barreau d''Angers'),
    ('barreau d''Annecy'), ('barreau d''Argentan'), ('barreau d''Arras'),
    ('barreau d''Aurillac'), ('barreau d''Auxerre'), ('barreau d''Avesnes-sur-Helpe'),
    ('barreau d''Avignon'), ('barreau d''Orléans'), ('barreau d''Épinal'),
    ('barreau de Bastia'), ('barreau de Bayonne'), ('barreau de Beauvais'),
    ('barreau de Belfort'), ('barreau de Bergerac-Sarlat'), ('barreau de Besançon'),
    ('barreau de Blois'), ('barreau de Bonneville et les Pays du Mont-Blanc'), ('barreau de Bordeaux'),
    ('barreau de Boulogne-sur-Mer'), ('barreau de Bourges'), ('barreau de Bourgoin-Jallieu'),
    ('barreau de Brest'), ('barreau de Briey'), ('barreau de Brive'),
    ('barreau de Béthune'), ('barreau de Béziers'), ('barreau de Caen'),
    ('barreau de Cambrai'), ('barreau de Carcassonne'), ('barreau de Carpentras'),
    ('barreau de Castres'), ('barreau de Chalon-sur-Saône'), ('barreau de Chambéry'),
    ('barreau de Chartres'), ('barreau de Cherbourg'), ('barreau de Châlons-en-Champagne'),
    ('barreau de Châteauroux'), ('barreau de Clermont-Ferrand'), ('barreau de Colmar'),
    ('barreau de Compiègne'), ('barreau de Coutances-Avranches'), ('barreau de Cusset-Vichy'),
    ('barreau de Dax'), ('barreau de Dieppe'), ('barreau de Dijon'),
    ('barreau de Douai'), ('barreau de Draguignan'), ('barreau de Dunkerque'),
    ('barreau de Fontainebleau'), ('barreau de Fort-de-France (Martinique)'), ('barreau de Grasse'),
    ('barreau de Grenoble'), ('barreau de La Roche-sur-Yon'), ('barreau de La Rochelle-Rochefort'),
    ('barreau de Laon'), ('barreau de Laval'), ('barreau de Libourne'),
    ('barreau de Lille'), ('barreau de Limoges'), ('barreau de Lisieux'),
    ('barreau de Lorient'), ('barreau de Lyon'), ('barreau de Marseille'),
    ('barreau de Mayotte'), ('barreau de Meaux'), ('barreau de Melun'),
    ('barreau de Metz'), ('barreau de Mont-de-Marsan'), ('barreau de Montargis'),
    ('barreau de Montbéliard'), ('barreau de Montluçon'), ('barreau de Montpellier'),
    ('barreau de Moulins'), ('barreau de Mulhouse'), ('barreau de Mâcon'),
    ('barreau de Nancy'), ('barreau de Nantes'), ('barreau de Narbonne'),
    ('barreau de Nevers'), ('barreau de Nice'), ('barreau de Nouméa (Nouvelle-Calédonie)'),
    ('barreau de Nîmes'), ('barreau de Papeete - Tahiti (Polynésie française)'), ('barreau de Paris'),
    ('barreau de Pau'), ('barreau de Poitiers'), ('barreau de Périgueux'),
    ('barreau de Quimper'), ('barreau de Reims'), ('barreau de Rennes'),
    ('barreau de Roanne'), ('barreau de Rouen'), ('barreau de Saint-Brieuc'),
    ('barreau de Saint-Denis de La Réunion'), ('barreau de Saint-Gaudens'), ('barreau de Saint-Malo-Dinan'),
    ('barreau de Saint-Nazaire'), ('barreau de Saint-Omer'), ('barreau de Saint-Pierre de La Réunion'),
    ('barreau de Saint-Quentin'), ('barreau de Saint-Étienne'), ('barreau de Saintes'),
    ('barreau de Sarreguemines'), ('barreau de Saumur'), ('barreau de Saverne'),
    ('barreau de Senlis'), ('barreau de Sens'), ('barreau de Soissons'),
    ('barreau de Strasbourg'), ('barreau de Tarascon'), ('barreau de Tarbes'),
    ('barreau de Thionville'), ('barreau de Thonon-les-Bains, Léman et Genevois'), ('barreau de Toulon'),
    ('barreau de Toulouse'), ('barreau de Tours'), ('barreau de Tulle'),
    ('barreau de Valence'), ('barreau de Valenciennes'), ('barreau de Vannes'),
    ('barreau de Versailles'), ('barreau de Villefranche-sur-Saône'), ('barreau de l''Ain'),
    ('barreau de l''Ardèche'), ('barreau de l''Ariège'), ('barreau de l''Aube'),
    ('barreau de l''Aveyron'), ('barreau de l''Essonne'), ('barreau de l''Eure'),
    ('barreau de la Charente'), ('barreau de la Creuse'), ('barreau de la Guadeloupe, de Saint-Martin et de Saint-Barthélemy'),
    ('barreau de la Guyane'), ('barreau de la Haute-Loire'), ('barreau de la Haute-Marne'),
    ('barreau de la Haute-Saône'), ('barreau de la Lozère'), ('barreau de la Meuse'),
    ('barreau de la Seine-Saint-Denis'), ('barreau de la Vienne'), ('barreau des Alpes-de-Haute-Provence'),
    ('barreau des Ardennes'), ('barreau des Deux-Sèvres'), ('barreau des Hautes-Alpes'),
    ('barreau des Hauts-de-Seine'), ('barreau des Pyrénées-Orientales'), ('barreau des Sables-d''Olonne'),
    ('barreau du Gers'), ('barreau du Havre'), ('barreau du Jura'),
    ('barreau du Lot'), ('barreau du Mans'), ('barreau du Tarn-et-Garonne'),
    ('barreau du Val-d''Oise'), ('barreau du Val-de-Marne');
