# Phase — Documents et correspondance

Document de conception issu de sessions Claude.ai. À lire avant toute
implémentation : les décisions ci-dessous ont été discutées et arbitrées, les
justifications sont données pour qu'elles ne soient pas défaites par
inadvertance.

**La numérotation des sections est référencée depuis le code**
(`app/config.py`, `app/services/messagerie.py`,
`app/services/stockage_documents.py`, `app/repositories/documents.py`). Ne
pas renuméroter : ajouter en fin de section ou créer une sous-section.

État au moment de cette révision : migrations `0021` (refonte documents) et
`0022` (lien échéance) appliquées, synchronisation IMAP et écrans de base en
place. Dernière migration du dépôt : `0025`. Les travaux restants décrits ici
commencent donc à `0026`.

---

## 1. Objectif

Rattacher à chaque dossier l'ensemble des pièces qui le concernent —
documents générés, e-mails échangés, fichiers déposés — afin que
l'information cesse d'être éparpillée entre la messagerie, le disque et
l'application.

---

## 2. Le problème de modélisation, et sa résolution

La table `dossier_document` (migration 0016, supprimée depuis) était
spécifique aux documents générés par fusion Typst : `modele_slug`,
`chemin_typ` et `chemin_pdf` y étaient tous `NOT NULL`. Elle ne pouvait
accueillir ni un e-mail importé ni un fichier déposé.

L'analyse a fait apparaître que « type de document » mélangeait en réalité
**trois dimensions indépendantes** :

### 2.1 Comment le fichier est arrivé

Plus précisément : *ce que l'application sait en faire techniquement*. Trois
cas seulement :

- `genere` : l'application le fabrique, elle connaît le modèle et garde le
  `.typ` fusionné ;
- `email` : l'application le *parse* et en extrait des métadonnées
  structurées (expéditeur, date, objet) sans saisie humaine ;
- `depose` : tout le reste — scan, fichier issu d'un lien de téléchargement,
  clé USB, version retravaillée d'une pièce jointe. L'application ne peut
  rien en deviner.

**Important** : « scanné », « téléchargé depuis un lien », « apporté sur clé
USB » ne sont *pas* des types distincts. C'est la même structure de données
(un fichier uploadé sans métadonnées déductibles). Ne pas créer de tables
filles supplémentaires pour ces cas.

### 2.2 Est-ce de la correspondance ?

Un e-mail : toujours. Un courrier reçu scanné : toujours. Un document
généré : *parfois seulement* — une lettre au client oui, des conclusions ou
une assignation non. C'est donc une caractéristique transversale, pas un
type.

### 2.3 Est-ce une pièce (élément de preuve) ?

Transversal également, et cumulable avec la correspondance : un échange
d'e-mails peut être produit comme pièce.

D'où le modèle : une table mère `document` portant les champs communs, deux
tables filles pour les seules spécialisations ayant des champs propres, et
`document_piece` comme caractéristique optionnelle attachable à n'importe
quel document.

---

## 3. Schéma

### Migration 0021 — refonte des documents (appliquée)

Reprend **exactement** le patron d'héritage de `contact` /
`personne_physique` / `personne_morale` (migration 0003) : contrainte
`UNIQUE (id, type_document)` sur la mère, `CHECK` figeant le type sur chaque
fille, clé étrangère composite. Ce patron rend structurellement impossible
qu'un document soit à la fois `genere` et `email`, sans recourir à un
trigger.

```sql
CREATE TABLE document (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL REFERENCES dossier(id),
    type_document text NOT NULL
        CHECK (type_document IN ('genere', 'email', 'depose')),
    titre text NOT NULL,
    -- Chemin du fichier principal, quel que soit le type : le PDF pour un
    -- document généré, le .eml pour un e-mail, le fichier uploadé pour un
    -- document déposé. Porté par la mère pour éviter de répéter la même
    -- colonne dans chaque fille.
    chemin_fichier text NOT NULL,
    -- Document dont celui-ci est issu : l'e-mail dont il a été extrait comme
    -- pièce jointe, ou dont il est une version retravaillée. Permet de
    -- répondre à « ce document, vous me l'avez transmis quand ? » en
    -- remontant à document_email.date_message.
    document_origine_id integer REFERENCES document(id),
    cree_par integer REFERENCES utilisateur(id),
    cree_le timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, type_document)
);

CREATE TABLE document_genere (
    document_id integer PRIMARY KEY,
    type_document text NOT NULL DEFAULT 'genere'
        CHECK (type_document = 'genere'),
    modele_slug text NOT NULL,
    chemin_typ text NOT NULL,
    FOREIGN KEY (document_id, type_document)
        REFERENCES document (id, type_document)
);

CREATE TABLE document_email (
    document_id integer PRIMARY KEY,
    type_document text NOT NULL DEFAULT 'email'
        CHECK (type_document = 'email'),
    sens text NOT NULL CHECK (sens IN ('recu', 'envoye')),
    expediteur text NOT NULL,
    destinataires text NOT NULL,
    objet text,
    -- Date de l'en-tête Date: du message, pas la date d'import.
    date_message timestamptz NOT NULL,
    -- En-tête Message-ID, identifiant unique attribué par le serveur
    -- d'envoi. Sert au dédoublonnage lors des synchronisations répétées.
    -- PAS de contrainte UNIQUE globale : un même message peut légitimement
    -- concerner deux dossiers (client ayant deux affaires en cours). Le
    -- contrôle d'unicité porte sur le couple (message_id, dossier_id) et se
    -- fait dans le repository par jointure sur document, dossier_id vivant
    -- sur la table mère.
    message_id text NOT NULL,
    FOREIGN KEY (document_id, type_document)
        REFERENCES document (id, type_document)
);

CREATE INDEX idx_document_email_message_id ON document_email (message_id);

-- Caractéristique optionnelle, applicable à un document de n'importe quel
-- type. Volontairement SANS clé étrangère composite : ce n'est pas une
-- spécialisation exclusive mais un attribut qui s'ajoute.
CREATE TABLE document_piece (
    document_id integer PRIMARY KEY REFERENCES document(id),
    -- Attribué seulement au moment de la communication formelle, d'où le
    -- caractère nullable. Texte et non entier : la numérotation réelle
    -- comporte des variantes (3 bis, 4-1...).
    numero_piece text,
    contact_provenance_id integer NOT NULL REFERENCES contact(id),
    -- Date à laquelle la pièce a été transmise au cabinet. Distincte de
    -- document.cree_le, qui n'est que la date d'import du fichier.
    -- Préremplie depuis document_origine → document_email.date_message
    -- quand la pièce vient d'un e-mail, saisie à la main sinon.
    date_transmission date,
    utilisee boolean NOT NULL DEFAULT false
);
```

**La qualité de la provenance (client, adversaire, confrère) n'est pas
stockée** : elle se déduit de `role_contact` / `type_role` pour le contact et
le dossier concernés, au moment de l'affichage. Même principe que
`dossier.nom_calcule` — pas de double source de vérité.

### Migration 0022 — lien échéance ↔ document (appliquée)

```sql
ALTER TABLE echeance
    ADD COLUMN document_id integer REFERENCES document(id);
```

Nullable, et posé sur la mère `document` (pas sur `document_email`) : un
document déposé peut tout autant faire courir un délai. Ne pas confondre avec
`categorie_id` (migration 0019) — la catégorie de l'échéance reste choisie
dans `categorie_echeance`.

### Migration 0026 — notes libres sur un document (à faire)

```sql
-- Note libre : « version retravaillée de la photo envoyée par le client »,
-- « communiquée le 12/04 », « pièce n°4 du bordereau adverse ». Sur la mère,
-- vaut pour les trois types.
ALTER TABLE document ADD COLUMN notes text;
```

À exposer dans le formulaire de dépôt et dans un écran de modification d'un
document, et à afficher dans les listes quand elle est renseignée.

---

## 4. Listage et tri

**Ne pas trier sur `cree_le`**, qui est la date d'import et placerait un
e-mail ancien importé aujourd'hui en tête de liste. Le repository calcule une
date de référence — `date_message` pour un e-mail, `date_transmission` pour
une pièce quand elle est renseignée, `cree_le` sinon — et trie dessus. Valeur
dérivée à l'affichage, jamais stockée (même principe que
`dossier.nom_calcule`).

Quatre fonctions de listage cohabitent, à ne pas confondre :

| Fonction | Filtre | Consommateur |
|---|---|---|
| `lister_pour_dossier` | aucun | `dossiers.chronologie` |
| `lister_emails_pour_dossier` | `type_document = 'email'` | onglet Messagerie |
| `lister_documents_pour_dossier` | `type_document <> 'email'` | onglet Documents |
| `lister_pieces_pour_dossier` | jointure `document_piece`, tous types | page Pièces |

**`lister_pour_dossier` doit rester non filtrée** : la chronologie est la
seule vue qui replace les e-mails dans le flux du dossier aux côtés des
événements. La filtrer les en ferait disparaître.

---

## 5. Synchronisation IMAP

### Le principe, et pourquoi il est aussi simple

L'utilisateur classe déjà ses e-mails dans Thunderbird selon une convention
stricte :

- boîte de réception = messages **non traités** uniquement ;
- messages liés à un dossier → dossier IMAP `/dossier/YYNNN_nom_du_client` ;
- autres messages traités → dossier `traité` ;
- Thunderbird est configuré pour ranger la réponse dans le dossier du message
  auquel elle répond.

**Le classement est donc déjà fait, et la référence du dossier est lisible
dans le nom du répertoire IMAP.** L'application n'a rien à deviner : elle
lit.

Conséquence directe, à ne pas défaire : **aucune logique de suggestion n'est
nécessaire**. Une conception intermédiaire prévoyait de proposer un dossier
par correspondance d'adresse e-mail ou par détection de la référence dans
l'objet, avec validation humaine message par message. Tout cela a été
abandonné une fois la convention de classement connue — c'était résoudre par
l'heuristique un problème déjà résolu par l'organisation.

Ne sont **pas** lus : la boîte de réception, le dossier `traité`, le dossier
« Envoyés ». L'application est passive sur la messagerie : elle ne lit que
`/dossier/*`, ne déplace rien, ne supprime rien, ne marque rien comme lu.

Les messages initiés hors réponse (qui partent dans « Envoyés » sans être
rangés) sont déplacés manuellement par l'utilisateur vers le dossier voulu —
choix assumé, pas de traitement applicatif.

### Algorithme

1. Énumérer les dossiers IMAP sous `/dossier/`.
2. Pour chacun, extraire les cinq chiffres de tête du nom et chercher le
   dossier correspondant par sa référence en base. Ignorer le reste du nom :
   l'utilisateur doit pouvoir renommer la partie « nom du client » sans rien
   casser.
3. Si aucun dossier ne correspond (faute de frappe, affaire pas encore
   saisie) : **ne rien deviner**. Signaler dans le compte rendu et passer.
   Une erreur visible vaut mieux qu'un mauvais classement silencieux — enjeu
   de secret professionnel.
4. Importer les messages dont le `message_id` n'est pas déjà rattaché à ce
   dossier.
5. Afficher un compte rendu : nombre de messages importés, répartition par
   dossier, anomalies rencontrées.

### Déduction du `sens`

Réceptions et envois cohabitent dans un même dossier IMAP, le nom ne dit donc
pas le sens. Il se déduit du message : si l'adresse d'expéditeur figure parmi
les adresses du cabinet (`ADRESSES_CABINET`, cf. §6), c'est `envoye` ; sinon
`recu`.

### Performance et non-intrusion

- **En-têtes seuls pour l'inventaire**, message complet uniquement à
  l'import. Sinon la synchronisation télécharge inutilement chaque pièce
  jointe volumineuse.
- **Utiliser `BODY.PEEK[...]`** et non `BODY[...]` : la seconde forme marque
  les messages comme lus côté serveur, ce qui perturberait Thunderbird.

### Bibliothèques

`imaplib` et `email`, tous deux dans la bibliothèque standard. **Aucune
dépendance à ajouter.**

---

## 6. Configuration

Dans `app/config.py`, patron existant (`os.environ.get` avec valeur par
défaut de développement) :

| Variable | Rôle |
|---|---|
| `IMAP_HOST` | `mail.infomaniak.com` |
| `IMAP_PORT` | `993` (SSL) |
| `IMAP_USER` | adresse de la boîte partagée |
| `IMAP_PASSWORD` | **mot de passe « appareil » dédié à l'application** |
| `IMAP_PREFIXE_DOSSIERS` | `dossier` — préfixe des répertoires à synchroniser |
| `ADRESSES_CABINET` | liste séparée par virgules, pour déduire le `sens` |

Infomaniak permet de créer plusieurs mots de passe distincts pour une même
adresse (onglet « Appareils »), révocables individuellement. Trois sont
prévus : Thunderbird de l'avocat, Thunderbird de la collaboratrice, et
l'application. Le mot de passe de l'application ne doit jamais servir
ailleurs.

Le fichier de secrets vit **hors du dépôt** (`/etc/mon-cabinet/`,
`chmod 600`, chargé via `EnvironmentFile=` dans l'unité systemd), pas
seulement protégé par `.gitignore`.

Architecture des adresses retenue : une boîte réelle unique (`contact@`),
avec des alias nominatifs et `info@` pointant dessus. Un seul jeu
d'identifiants IMAP à sécuriser.

---

## 7. Écrans

### 7.1 Réorganisation de la fiche dossier (à faire)

La fiche utilise un patron d'onglets en **CSS pur** (radios `.onglet-radio` +
labels + `.onglet-panneau`), sans JavaScript. L'onglet actif est piloté par
la variable `onglet_actif` passée au template, et les actions reviennent sur
leur onglet via l'ancre `#panneau-<nom>`.

L'onglet **Documents** unique est scindé en deux :

- **Messagerie** — `lister_emails_pour_dossier`
- **Documents** — `lister_documents_pour_dossier`

Motif : sur un dossier contentieux qui dure, quelques dizaines de documents
cohabiteraient avec plusieurs centaines d'e-mails, et la liste unique
deviendrait inutilisable. Les deux se consultent d'ailleurs différemment —
la messagerie comme un fil qu'on remonte, les documents comme un inventaire
où l'on cherche un élément précis.

**Pièges d'implémentation** :

- La feuille de style énumère les onglets un par un dans deux sélecteurs
  groupés (`#onglet-X:checked ~ ...`). Ajouter `#onglet-messagerie` **aux
  deux**, sinon le panneau ne s'affichera jamais.
- Ajouter `messagerie` aux valeurs acceptées pour `onglet_actif` dans
  `dossiers.fiche`.

### 7.2 Page Pièces (à faire)

**Page séparée, pas un cinquième onglet** — sur le modèle de
`dossiers.chronologie`. Motif : préparer une communication de pièces est une
tâche ponctuelle et concentrée, qui appelle un écran à elle ; et la fiche
passerait sinon à six onglets dans une barre horizontale.

Alimentée par `lister_pieces_pour_dossier`, sans condition de type : un
e-mail produit comme pièce doit y figurer au même titre qu'un document
déposé.

### 7.3 Liens à préserver entre les deux onglets

C'est le vrai risque de la séparation, à traiter dans les requêtes :

- **Dans Documents** : une pièce jointe versée se retrouve loin de son
  e-mail. Sa ligne doit porter sa provenance — « reçu par e-mail du 12/03 de
  M. Martin » — cliquable vers le message. Jointure depuis
  `document_origine_id` vers `document_email` pour `date_message` et
  `expediteur`.
- **Dans Messagerie** : un e-mail dont des pièces jointes ont déjà été
  versées doit le signaler, sinon risque de double versement. Décompte des
  documents dont `document_origine_id` pointe vers cet e-mail.

### 7.4 Consultation d'un e-mail importé

En-têtes, corps en texte brut (cf. §8), liste des pièces jointes. Chaque
pièce jointe porte **deux** actions :

- **« Verser au dossier »** — extrait la pièce jointe du `.eml`, l'écrit
  comme fichier autonome et crée un `document` de type `depose` avec
  `document_origine_id` pointant vers l'e-mail.
- **« Verser une version retravaillée »** — ouvre le formulaire de dépôt
  avec `document_origine_id` **déjà positionné** sur l'e-mail. Répond au cas
  fréquent de la photo de téléphone mal cadrée de 25 Mo, ou des cinq photos
  à assembler en un seul PDF. `creer_depose` accepte déjà le paramètre : il
  n'y a qu'à le transmettre depuis ce point d'entrée.

Ne pas laisser l'utilisateur déposer la version retravaillée par le
formulaire générique sans origine : il perdrait la traçabilité qui est
l'objet même de la colonne.

Bouton « créer une échéance » disponible ici également, pour le cas fréquent
où l'action attendue n'apparaît que quelques jours plus tard.

**Le retraitement d'image lui-même reste hors de l'application** : recadrage,
redressement, conversion, compression sont faits par des outils existants.
Les intégrer supposerait des dépendances de traitement d'image dont on
n'utiliserait qu'une fraction. L'application classe et relie, elle ne
transforme pas.

### 7.5 Consultation des fichiers

**Lien vers un nouvel onglet, pas de visionneuse intégrée.** Firefox et
Chrome embarquent un lecteur PDF complet (zoom, recherche, navigation,
impression) et gèrent l'affichage des images. Embarquer PDF.js reviendrait à
reconstruire moins bien, dans un cadre étroit, ce que le navigateur fait
déjà — et priverait de la possibilité de mettre la pièce d'un côté et le
dossier de l'autre.

Route servant le fichier depuis `instance/documents/` via `send_file`, avec
`Content-Disposition: inline` (et non `attachment`, qui forcerait le
téléchargement).

- **Vérifier les droits** dans la route : une URL devinée doit échouer. Ne
  pas s'appuyer sur le fait que le lien n'est visible que depuis la fiche.
- **Ne jamais construire le chemin à partir de l'URL** : la route reçoit un
  identifiant de document, lit `chemin_fichier` en base, sert ce fichier-là.

**Cas particulier — pièces jointes non versées** : elles n'ont ni ligne
`document` ni fichier autonome, elles sont encore dans le `.eml`. La route
doit ouvrir le `.eml`, retrouver la partie par son index et la servir à la
volée, **sans rien écrire sur le disque**. Le module `email` le permet
directement. Permet de consulter une pièce jointe avant de décider de la
verser.

### 7.6 Dépôt d'un fichier

Fichier, titre, notes (§3, migration 0026), case « c'est une pièce » révélant
provenance et date de transmission. La provenance est une liste déroulante
des contacts déjà liés au dossier, construite avec le patron
`_choix_avec_vide`. Le numéro de pièce reste vide à ce stade.

### 7.7 Synchronisation

Blueprint `messagerie`, préfixe `/messagerie` — hors du périmètre des
dossiers, puisque le point de départ est la boîte. Un bouton, un compte
rendu.

Chaque ligne du compte rendu porte un lien « créer une échéance », qui ouvre
le formulaire existant prérempli avec le `document_id` et l'objet du message
comme libellé par défaut.

**Ne pas transformer cela en question obligatoire par message.** L'option a
été examinée et écartée : la synchronisation est une opération par lots, une
question posée quinze fois de suite est expédiée machinalement, ce qui donne
l'illusion d'un contrôle sans en avoir la substance. Le lien non bloquant est
un second regard, pas un formulaire à subir.

---

## 8. Points de sécurité et d'intégrité

**Noms de fichiers.** Le nom d'une pièce jointe vient de l'extérieur, donc
potentiellement d'une partie adverse. Ne jamais l'utiliser comme nom de
fichier réel : un nom contenant `../` permettrait d'écrire hors du répertoire
prévu. Stocker sous un nom généré (UUID) dans
`instance/documents/<dossier_id>/`, conserver le nom d'origine uniquement en
base pour l'affichage et le téléchargement. Règle du même coup les collisions
de noms identiques.

**Corps HTML des e-mails.** Ne pas rendre le HTML d'un message dans la page :
les images distantes signalent la lecture à l'expéditeur (pixels de traçage)
et le HTML injecté peut interférer avec la page. Afficher la partie texte
brut, et proposer le `.eml` en téléchargement pour consultation dans
Thunderbird si le rendu importe. Évite aussi une dépendance d'assainissement
HTML pour un besoin marginal.

**Conservation du `.eml` brut.** Choix délibéré plutôt qu'un export PDF : les
en-têtes portent la date d'envoi, l'adresse exacte et le chemin des serveurs
traversés — valeur probatoire qu'un rendu visuel perd. Conséquence utile : la
pièce jointe originale reste toujours disponible même quand une version
retravaillée a été versée au dossier (§7.4). L'utilisateur peut donc
retravailler librement sans jamais perdre la source.

**Ne pas purger les pièces jointes à l'intérieur d'un `.eml`.** Cela
supposerait de réécrire le fichier, qui ne serait alors plus l'e-mail tel que
reçu — affaiblissant sa valeur probatoire, et rendant invérifiables les
signatures DKIM ou S/MIME qui couvrent le corps du message. Si le volume
devenait un problème réel (rare : 10 000 messages à 500 Ko ≈ 5 Go), la
réponse propre est de supprimer **l'e-mail entier** après extraction de ce
qui compte, pas de vider partiellement le fichier. Si une purge sélective
devait malgré tout être implémentée, elle exigerait une colonne
`eml_purge_le` sur `document_email` : un fichier altéré sans trace serait le
pire des deux mondes.

**Suppression d'un e-mail dont des documents sont issus.** La clé étrangère
`document_origine_id` empêchera la suppression. Bloquer explicitement avec un
message clair (« cet e-mail est à l'origine de 2 documents versés au
dossier ») plutôt que de laisser remonter une erreur technique ou de basculer
le lien à `NULL` : la traçabilité « cette pièce m'a été transmise par ce
message, à cette date » est l'objectif de la colonne, elle ne doit pas
disparaître silencieusement.

**Granularité de `document_origine_id`** : le lien pointe vers l'e-mail, pas
vers la pièce jointe précise. Si un message contient trois fichiers et qu'un
seul est retravaillé, le lien dira « provient de ce message » sans préciser
lequel. Choix assumé : ce qui compte juridiquement est l'événement de
transmission (le message et sa date). Descendre plus fin obligerait à stocker
des index de parties MIME pour un gain théorique.

---

## 9. Hors périmètre de cette phase

Conçu, discuté, mais volontairement non implémenté ici :

- **Numérisation et classement des fichiers scannés** — fera l'objet d'une
  phase séparée. Rien à anticiper dans le schéma : un fichier numérisé est un
  `document` de type `depose` comme un autre.
- **Répondre à un e-mail depuis l'application** (`smtplib` + `email`, tous
  deux stdlib). Nécessitera de relire le `Message-ID` du `.eml` d'origine
  pour renseigner `In-Reply-To` et `References`, et un `APPEND` IMAP dans le
  dossier de destination pour que la réponse reste visible dans Thunderbird.
  Le schéma actuel n'a besoin d'aucun ajustement pour l'accueillir.
- **Envoi de pièces jointes** (`EmailMessage.add_attachment`). Puiserait dans
  les documents déjà rattachés au dossier — d'où l'intérêt du modèle
  générique. Limite Infomaniak : 201 Mo par message, en-têtes et corps
  compris ; prévoir un message d'erreur explicite plutôt qu'un échec
  silencieux. L'encodage base64 alourdit une pièce d'environ 33 %.
- **Bordereau de communication de pièces** : quasi gratuit une fois la page
  Pièces en place — un modèle Typst de plus, alimenté par
  `lister_pieces_pour_dossier`. La chaîne de génération existante suffit.
- **Reprise d'historique par dossier** : recherche IMAP ciblée sur les
  adresses des contacts d'un dossier, utile à l'ouverture d'une affaire déjà
  ancienne. Complément éventuel, pas le mécanisme principal.
- **Indicateur « à examiner » sur un message importé** : à n'envisager que si
  le lien « créer une échéance » du compte rendu se révèle insuffisant à
  l'usage. Coût certain, bénéfice hypothétique.
- **Visionneuse intégrée (PDF.js)** : ne se justifierait que pour des
  fonctions absentes du navigateur — annoter, surligner, apposer un tampon de
  numérotation. À décider pour elle-même le jour où le besoin apparaît, pas
  pour remplacer un affichage qui fonctionne.

Écarté après examen, à ne pas réintroduire :

- **Paperless-ngx** — une application complète à faire tourner à côté (base,
  authentification, interface, déploiement Docker), à synchroniser via son
  API, pour un besoin que la stdlib couvre. Resterait pertinent un jour pour
  l'OCR de documents scannés, besoin distinct.
- **`keyring`** pour les identifiants — fragile sur un service systemd sans
  session de bureau, et déplace le problème plutôt qu'il ne le résout.
- **Chiffrement du fichier de secrets** avec une clé stockée sur la même
  machine : complexité sans protection réelle.
