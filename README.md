# Mon Cabinet — phase 0 : fondations techniques

Ce squelette prouve juste une chose : Flask, psycopg3 et PostgreSQL
communiquent correctement ensemble. Aucune table métier n'existe encore
(contacts, dossiers...) — ça viendra en phase 1 et 2.

## 1. Installer PostgreSQL 18 sur le mini PC

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Si votre distribution ne propose pas encore PostgreSQL 18 par défaut,
ajoutez le dépôt officiel PGDG (voir https://www.postgresql.org/download/linux/ubuntu/)
avant cette commande.

## 2. Créer la base et le rôle applicatif

```bash
sudo -u postgres psql
```

Puis, dans le prompt `psql` :

```sql
CREATE ROLE moncabinet_app WITH LOGIN PASSWORD 'choisissez_un_mot_de_passe_solide';
CREATE DATABASE moncabinet OWNER moncabinet_app;
\q
```

## 3. Préparer l'environnement Python

Depuis le dossier du projet :

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

On n'active pas forcément le venv (`source venv/bin/activate`) : appeler
directement `./venv/bin/python` ou `./venv/bin/pip` fonctionne aussi bien et
évite une commande à retenir.

## 4. Définir les variables d'environnement

Avant de lancer l'application, indiquez-lui comment se connecter à la base.
Le plus simple : un petit script non versionné (déjà exclu par
`.gitignore`) que vous sourcez avant de travailler.

Créez un fichier `env.sh` :

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=moncabinet
export DB_USER=moncabinet_app
export DB_PASSWORD=choisissez_un_mot_de_passe_solide
```

Puis avant de lancer l'appli :

```bash
. env.sh
```

## 5. Lancer l'application

```bash
./venv/bin/python wsgi.py
```

Ouvrez http://localhost:5000 dans un navigateur : la page doit afficher
« Ça fonctionne » suivi de la version de PostgreSQL détectée. Si vous voyez
ça, toute la chaîne (Flask → psycopg3 → PostgreSQL) est opérationnelle.

## 6. Préparer les migrations (yoyo)

Copiez le modèle et adaptez-le avec votre vrai mot de passe (ce fichier
`yoyo.ini` ne doit jamais être versionné, il est déjà dans `.gitignore`) :

```bash
cp yoyo.ini.example yoyo.ini
```

Éditez `yoyo.ini` pour remplacer `VOTRE_MOT_DE_PASSE` par le mot de passe
choisi à l'étape 2. Vérifiez que la connexion fonctionne :

```bash
./venv/bin/yoyo list
```

Une table vide (« STATUS / ID / SOURCE » sans ligne dessous) est le résultat
attendu : aucune migration n'a encore été écrite, mais yoyo se connecte bien
à la base. Les premières vraies migrations (table `utilisateur`, puis
`contact`) arriveront en phase 1.

## 7. Initialiser git

```bash
git init
git add -A
git commit -m "Phase 0 : squelette Flask + PostgreSQL + psycopg3"
```

## Phase 1 : identification et traçabilité

Une fois la phase 0 en place (venv, base créée, `yoyo.ini` réglé), voici ce
qui s'ajoute.

### Installer les nouvelles dépendances

```bash
./venv/bin/pip install -r requirements.txt
```

(Flask-Login et Flask-WTF ont été ajoutés à `requirements.txt`.)

### Appliquer la migration de la table utilisateur

```bash
./venv/bin/yoyo apply
```

### Créer votre propre compte

Il n'y a pas de page d'inscription : les comptes se créent depuis le
terminal, par vous (le titulaire). C'est volontaire — ça évite d'exposer un
formulaire d'inscription pour un usage qui ne concernera jamais plus de 2-3
personnes.

```bash
./venv/bin/flask creer-utilisateur
```

La commande vous demandera votre nom (qui servira aussi d'identifiant de
connexion — il n'y a pas d'email dans cette application), un mot de passe
(saisi deux fois), et votre rôle (choisissez `avocat`).

### Tester

```bash
./venv/bin/python wsgi.py
```

Ouvrez http://localhost:5000 : vous devez être redirigé vers `/connexion`
(la page de test est maintenant protégée). Connectez-vous avec le compte que
vous venez de créer — vous devez retrouver la page « Ça fonctionne », avec
votre nom affiché en haut à droite et un lien de déconnexion.

### Pour ajouter un stagiaire plus tard

Même commande, avec le rôle `stagiaire` :

```bash
./venv/bin/flask creer-utilisateur --nom "Prénom Nom" --role stagiaire
```

(Les restrictions d'accès propres aux stagiaires arrivent en phase 4 — pour
l'instant, tous les comptes actifs peuvent se connecter et accéder à la même
page de test.)

## Phase 2 : contacts, coordonnées et rôles

Six nouvelles tables de référence et de données, en plus de `utilisateur` :
`pays`, `departement`, `civilite` (référence), `contact` / `personne_physique`
/ `personne_morale`, `type_role` / `role_contact`, et les coordonnées
historisées (`adresse` / `contact_adresse`, `telephone` / `contact_telephone`,
`email` / `contact_email`).

### Installer et migrer

```bash
./venv/bin/pip install -r requirements.txt
./venv/bin/yoyo apply
```

Ça applique automatiquement les migrations 0002 à 0006, y compris les
données de référence : 193 pays (depuis votre CSV), 101 départements, 3
civilités, 6 rôles.

### Vérifier que tout fonctionne

Un script parcourt tout le modèle (création de contacts, partage d'adresse
entre deux contacts, historisation, recherche anti-conflit, validation des
règles de rôle) et affiche chaque étape :

```bash
PYTHONPATH=. ./venv/bin/python scripts/verifier_contacts.py
```

Le `PYTHONPATH=.` est nécessaire parce que le script vit dans `scripts/` et
a besoin de trouver le module `app` à la racine du projet.

### Ce qui n'est délibérément pas encore là

- **Aucun formulaire web** pour créer un contact : seule la couche
  d'accès aux données (migrations, dataclasses, repositories) est prête.
  Les formulaires méritent leur propre discussion avant d'être codés, vu
  la richesse du modèle de coordonnées.
- **`role_contact.dossier_id` n'a pas de contrainte de clé étrangère.**
  La table `dossier` n'existe pas encore (phase 3). La colonne est déjà là
  et fonctionne, mais rien n'empêche pour l'instant d'y mettre un numéro de
  dossier qui n'existe pas — la contrainte sera ajoutée par une migration
  `ALTER TABLE` une fois `dossier` créée.

## Interface web des contacts (création + recherche)

Trois pages accessibles depuis le lien « Contacts » en haut de chaque page
une fois connecté :

- `/contacts/` — recherche par nom (personnes physiques et morales
  confondues, c'est la recherche anti-conflit d'intérêts)
- `/contacts/nouveau` — choix du type de contact
- `/contacts/nouveau/personne-physique` et `/contacts/nouveau/personne-morale`
  — les deux formulaires de création

Rien de nouveau à installer ni à migrer : ces pages s'appuient entièrement
sur les tables et les fonctions déjà en place depuis la livraison
précédente.

### Ce qui n'est délibérément pas encore là

- **Pas de fiche contact détaillée.** Créer un contact renvoie vers la
  recherche, pas vers une page qui lui serait propre — cette page n'existe
  pas encore.
- **Pas de gestion des coordonnées depuis l'interface** (ajouter une
  adresse, un téléphone, un email à un contact existant, ou déclarer un
  déménagement). Les fonctions Python le permettent déjà
  (`app/repositories/coordonnees.py`), mais aucun formulaire ne les
  appelle pour l'instant.
- **Aucune auto-complétion** (API adresse.data.gouv.fr, API Sirene) :
  saisie entièrement manuelle, comme convenu.
- **Pas d'attribution de rôle** depuis l'interface — ça viendra avec la
  phase 3, une fois `dossier` en place.

## Interface web des contacts

Complète la phase 2 : formulaires de création, fiche contact avec édition
progressive, coordonnées (adresses, téléphones, emails), recherche.

### Ce qui est inclus

- **Création minimale** : `/contacts/nouveau` propose personne physique ou
  morale, chacune ne demandant que le nom (ou la raison sociale). Le reste
  se remplit ensuite depuis la fiche.
- **Fiche contact** (`/contacts/<id>`) : formulaire d'édition de tous les
  champs, sections adresses / téléphones / emails avec ajout et (pour les
  adresses) clôture du lien à la date du jour.
- **Autocomplétion d'adresse** : le champ de recherche d'adresse sur la
  fiche interroge, en JavaScript pur, l'API de géocodage de la
  Géoplateforme (`data.geopf.fr`) et préremplit les champs structurés au
  clic sur une suggestion. Le reste (complément, BP/TSA/CS, CEDEX,
  mention destinataire) se saisit toujours à la main, cette API ne les
  connaissant pas. Si l'appel échoue (réseau, changement futur de l'API),
  un message apparaît et la saisie manuelle reste possible juste en dessous.
- **Partage d'adresse** : sur la fiche, une recherche par nom retrouve un
  autre contact et permet de relier son adresse active plutôt que d'en
  ressaisir une — c'est ce qui permet à un couple de partager le même
  domicile sans dupliquer la ligne `adresse`.
- **Recherche** (`/contacts/`) : la recherche anti-conflit d'intérêts,
  balayant personnes physiques et morales sans distinction.

### Ce qui n'est pas inclus

Rien sur les rôles (`role_contact`) : l'écran d'attribution des rôles
viendra avec la phase 3, une fois `dossier` en place, pour ne pas
construire un écran à moitié fonctionnel qu'il faudrait reprendre.

### Tester

```bash
./venv/bin/python wsgi.py
```

Connectez-vous, puis « Contacts » dans la barre du haut. Pour
l'autocomplétion d'adresse, une connexion internet est nécessaire (l'appel
part du navigateur, pas du serveur).

## Retouches de forme (après premier retour d'usage)

- **Casse normalisée à la saisie** (`app/normalisation.py`) : `nom`/`nom_usage`
  en MAJUSCULES, `prenom`/`prenoms_secondaires`/`ville_naissance` en casse
  titre, `raison_sociale` inchangée (une stylisation officielle ne doit pas
  être écrasée).
- **Suggestions au fil de la frappe** sur la recherche de contact et le
  partage d'adresse (`static/js/recherche_contact.js`, endpoint JSON
  `/contacts/api/suggestions`).
- **Page d'accueil des contacts** : liste désormais tous les contacts par
  défaut (25 par page, pagination classique) plutôt que rien tant qu'aucune
  recherche n'est lancée.
- **Coordonnées douteuses** : bouton "Signaler douteuse/douteux" sur
  adresses, téléphones, emails (migration 0007). Reste actif et visible
  avec un avertissement, ne se clôture que volontairement.
- **Clôture téléphone/email** : les boutons manquants ont été ajoutés
  (les fonctions existaient déjà côté repository, seule l'interface les
  reliait pas).
- **Détection de doublons** sur téléphone et email : normalisation avant
  comparaison (chiffres seuls pour un numéro, minuscules pour un email).
  Un doublon sur le même contact est simplement refusé ; un numéro/email
  déjà utilisé par un autre contact relie automatiquement ce contact à la
  ligne existante (partage), sans étape de recherche manuelle contrairement
  à l'adresse.
- **Nationalité** : France en tête de liste, le reste par ordre alphabétique.

## Retouches sur l'interface contacts

Suite à vos remarques après premier usage :

- **Casse normalisée à la saisie** (`app/normalisation.py`) : `nom` et
  `nom_usage` en MAJUSCULES, `prenom` / `prenoms_secondaires` /
  `ville_naissance` en casse titre. `raison_sociale` n'est jamais touchée
  (une stylisation officielle comme "TotalEnergies" doit rester intacte).
- **Suggestions au fil de la frappe** sur la recherche de contact et sur le
  partage d'adresse (`static/js/recherche_contact.js`, endpoint JSON
  `/contacts/api/suggestions`).
- **Page d'accueil des contacts** : liste désormais tous les contacts par
  défaut (25 par page, pagination simple), plutôt que rien tant qu'on n'a
  pas cherché.
- **Coordonnées douteuses** : un bouton "Signaler douteuse/douteux" sur
  chaque adresse/téléphone/email, sans clôturer le lien — reste actif et
  visible avec un avertissement, jusqu'à ce que la bonne valeur soit connue
  (migration 0007, colonne `douteux`).
- **Clôture manquante pour téléphone et email**, ajoutée (elle existait déjà
  pour les adresses, mais pas pour les deux autres — trou comblé plutôt que
  nouvelle question de conception).
- **Détection de doublon avec réutilisation automatique** sur téléphone et
  email : une valeur normalisée déjà associée à ce contact ne se recrée pas ;
  déjà associée à un *autre* contact, ce contact est relié à la ligne
  existante (partage automatique) plutôt que d'en dupliquer une.
- **Nationalité** : France en tête de liste, le reste par ordre
  alphabétique (le pays de naissance à l'étranger, lui, reste en ordre
  alphabétique pur).

## Dossiers

Complète la boucle contacts ↔ dossiers, et referme la contrainte de clé
étrangère laissée en attente sur `role_contact.dossier_id` depuis la
phase 2.

### Nouvelles tables (migration 0008)

- `matiere` : référentiel modifiable (droit immobilier, divorce par
  consentement mutuel en exemples de départ), gestion réservée aux comptes
  `avocat` et `collaborateur` — première restriction de permission de
  l'application, via un décorateur `@role_requis(...)` réutilisable.
- `compteur_dossier` : un compteur par année, mis à jour uniquement à
  l'ouverture d'un dossier (pas à sa création en brouillon).
- `dossier` : `statut` (brouillon / ouvert / clos), `categorie` (juridique
  ou judiciaire — contrainte fixe, contrairement à `matiere`),
  `matiere_id`, dates d'ouverture et de clôture.

### Cycle de vie

1. **Brouillon** : bouton « Nouveau dossier » sur la fiche d'un contact —
   crée le dossier et attribue automatiquement ce contact comme client, en
   une seule opération. Pas de référence à ce stade.
2. **Ouverture** : la référence (format YYNNN) est proposée automatiquement
   mais reste modifiable — testé en corrigeant manuellement le numéro
   suggéré pour reprendre la numérotation de vos dossiers déjà en cours ;
   le compteur se recale ensuite sur cette correction pour les dossiers
   suivants.
3. **Clôture** : fixe la date de clôture.

### Fiche dossier

Nom calculé à l'affichage (jamais stocké) à partir des rôles client et
adversaire : `"DUPONT / MARTIN"`, ou simplement `"DUPONT"` sans adversaire
— un dossier de conseil n'en a souvent aucun, ce n'est pas un champ
manquant. Liste tous les intervenants avec lien vers leur fiche contact ;
réciproquement, la fiche contact liste tous ses dossiers.

### Tester

```bash
./venv/bin/python wsgi.py
```

La gestion des matières (`/dossiers/matieres`) n'apparaît dans le menu et
n'est accessible que pour un compte `avocat` ou `collaborateur` — un
`stagiaire` reçoit une page d'accès refusé (403).

### Retrait d'un intervenant

Bouton « Retirer » à côté de chaque intervenant sur la fiche dossier.
Protégé : impossible de retirer le dernier rôle client d'un dossier (un
dossier n'existe jamais sans client). Le choix du contact lié
(`contact_lie_id`) était déjà restreint aux seuls contacts présents sur le
dossier — vérifié à nouveau, ça fonctionne bien.

**Bug corrigé au passage** : le nom affiché pour un contact sans prénom
renseigné (le cas courant à la création minimale) s'affichait `None` dans
la liste des intervenants et dans le champ contact lié — la concaténation
SQL `prenom || ' ' || nom` ne tolérait pas un prénom NULL. Corrigé avec le
même motif de protection déjà utilisé ailleurs dans le code
(`recherches` de contacts).

## Génération de documents

Fusionne les données d'un dossier (intervenants, référence...) dans un
modèle Typst (`.typ`), compile le résultat en PDF, et trace le tout en
base — objectif : arrêter de recopier à la main les coordonnées d'un
client dans chaque courrier/acte.

### Pourquoi Typst plutôt que .docx/.odt

Plusieurs approches ont été comparées (Markdown/Pandoc, WeasyPrint, LaTeX,
py3o.template, docxtpl) avant de retenir Typst :

- Un document .docx/.odt ouvert dans LibreOffice ne rend pas exactement
  pareil selon l'OS et la version du logiciel (pagination, coupures de
  paragraphe, titres orphelins en bas de page) — problème rencontré en
  pratique en travaillant entre Linux et Windows.
- Typst compile de façon déterministe (même rendu quel que soit l'OS) et
  gère correctement la pagination automatique.
- Typst intègre un vrai langage de programmation (`if/else`, `for`,
  variables) directement dans le modèle, nécessaire pour des actes à
  clauses conditionnelles (ex. convention de divorce : mentions différentes
  selon présence/âge des enfants, existence d'une prestation compensatoire).

### Installer Typst

Télécharger le binaire statique correspondant à votre plateforme depuis
https://github.com/typst/typst/releases et le placer dans un répertoire du
`PATH` (ex. `~/.local/bin/typst`) — pas de paquet `pip`, `typst compile` est
appelé par `subprocess` depuis `app/services/generation_documents.py`.

### Modèles de documents

Chaque modèle est un répertoire sous `app/documents_modeles/<slug>/` :

- `modele.typ` — le gabarit, qui lit ses données via
  `#let data = json("data.json")` (fichier généré à la volée à la fusion).
- `metadata.json` — libellé du modèle et liste des champs à saisir à la
  main (non déductibles du dossier/contact, ex. montant d'une prestation
  compensatoire).

Ce sont des fichiers gérés directement sur le serveur, pas depuis
l'interface web : c'est un choix délibéré, la conception d'un modèle relève
de l'édition d'un fichier Typst (avec aperçu live via `typst watch`), pas
d'un formulaire d'upload. Un modèle d'exemple (`lettre_simple`) est fourni
pour servir de point de départ.

### Utilisation

Depuis la fiche d'un dossier ouvert : choisir un modèle dans la liste,
renseigner les champs propres à ce modèle, valider. Le PDF généré et le
`.typ` fusionné (données déjà injectées) sont ensuite téléchargeables
depuis la section "Documents" de la fiche — le `.typ` peut être repris et
personnalisé localement avec `typst watch` avant un usage final, la mise en
page du modèle restant volontairement fixe (seul le texte varie d'un
dossier à l'autre).

## Point d'attention important

Le schéma de connexion utilisé par yoyo est `postgresql+psycopg://` et non
`postgresql://` tout court. La différence compte : `postgresql://` indique à
yoyo d'utiliser psycopg2 (l'ancienne version, absente de ce projet), tandis
que `postgresql+psycopg://` lui indique d'utiliser psycopg3 (celui que nous
avons choisi). C'est déjà réglé dans `yoyo.ini.example`, mais bon à savoir si
vous modifiez ce fichier plus tard.
