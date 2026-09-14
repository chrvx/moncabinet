# Phase — Suivi des événements de dossier

## Contexte et problème

Le dossier sait aujourd'hui tracer ce qui est *prévu* (`echeance`) et ce qui
arrive *par écrit* (`document` : e-mail, pièce déposée, document généré).
Rien ne capture ce qui se passe *oralement* — un rendez-vous, un appel
téléphonique, une audience — ni le temps qui y est consacré.

Symptôme concret : un entretien téléphonique a lieu, rien n'est noté sur le
moment ("je le ferai plus tard"), et au moment de revenir sur le dossier, le
contenu de l'échange n'est plus certain. Objectif de cette phase : qu'un
entretien oral donne systématiquement lieu à une trace écrite, avec sa durée
si pertinent (justification du temps passé, calibrage des forfaits
d'honoraires par matière), et que cette trace reste fiable dans la durée —
ni disparition, ni réécriture silencieuse.

## Décisions actées

1. **Table dédiée `evenement`**, distincte de `echeance`. Les deux
   répondent à des questions différentes : `echeance` = "qu'est-ce qui est
   prévu ?" (tourné vers l'avenir, cycle à_faire → fait) ; `evenement` =
   "qu'est-ce qui s'est passé ?" (tourné vers le passé, la trace textuelle
   *est* la donnée, pas un détail annexe).

2. **Pas de patron d'héritage** (contrairement à `contact` ou `document`).
   Un rdv, un appel et une audience ont la même forme (date, durée
   éventuelle, contenu texte) — seule une étiquette change. Le type est une
   donnée (`type_evenement`, table de référence éditable), sur le même
   principe que `matiere` ou `categorie_echeance` — pas une sous-table
   figée par migration.

3. **`contenu` obligatoire, sans exception, y compris pour le type
   "Autre"**. Impossible en base de créer un événement sans indiquer ce
   qu'il en est ressorti.

4. **L'e-mail n'est pas dupliqué ici** : il reste dans `document` /
   `document_email`. `evenement` ne couvre que l'oral. Voir la section
   Chronologie plus bas pour la vue combinée.

5. **Lien optionnel avec `echeance`** (`evenement.echeance_id`, nullable) :
   un raccourci "clôturer avec compte-rendu" sur une échéance préremplit la
   création d'un événement plutôt que de forcer un aller-retour manuel
   entre les deux écrans.

6. **Vue "Chronologie"** combinant événements et documents triés par date —
   fusion applicative des deux listes existantes, pas de nouvelle table.

7. **Pas de suppression réelle.** Une suppression effacerait la trace
   elle-même, ce qui va à l'encontre de l'objectif de départ. À la place :
   un mécanisme d'**annulation réversible et tracée** (point 8) et une
   **modification illimitée mais visible** (point 9). Écarté par la
   discussion : suppression réservée à certains rôles (ne protège pas
   contre l'auteur lui-même), fenêtre de suppression limitée dans le temps
   (règle de plus pour un cas déjà couvert autrement).

8. **Annulation, pas suppression.** Sur le modèle du flag `douteux` déjà
   utilisé sur les coordonnées (adresse/téléphone/email) : un événement
   annulé reste en base et consultable, mais sort de l'affichage par
   défaut, avec un avertissement en cas de consultation explicite. Motif
   texte optionnel à l'annulation (`motif_annulation`, ex. "doublon",
   "mauvais dossier"). Réversible (« Réactiver »), sur le modèle exact de
   `marquer_fait`/`marquer_a_faire` déjà en place pour `echeance`.

9. **Modification du contenu autorisée sans limite, mais jamais
   silencieuse.** `modifie_par`/`modifie_le` doivent être **affichés** dans
   l'interface (pas seulement stockés), pour qu'une correction ne passe
   jamais inaperçue. Le **changement de dossier de rattachement**
   (correction d'un événement saisi sur le mauvais dossier) est autorisé
   mais **réservé aux comptes `avocat`/`collaborateur`** — une portée
   différente d'une simple faute de frappe corrigée.

10. **Historique complet des modifications**, au-delà du simple
    `modifie_par`/`modifie_le` : sans historique, deux corrections
    successives masquent la première (seule la dernière reste visible),
    ce qui rouvre exactement le problème de fiabilité que cette phase
    cherche à résoudre. Une table `evenement_historique` reçoit une copie
    de la ligne *avant* toute écriture qui la modifie (contenu, type,
    date, durée, dossier de rattachement, annulation, réactivation) — un
    seul mécanisme générique, pas une variante par type d'action.

11. **Historisation en code Python explicite, pas par trigger
    PostgreSQL.** Décision motivée en détail plus bas (section *Pourquoi
    pas un trigger*) — en résumé : le seul chemin de contournement possible
    (une modification manuelle via `psql`) ne peut venir que du titulaire
    lui-même, qui aurait de toute façon les moyens de modifier un trigger
    tout autant qu'une fonction Python. Le trigger n'apporterait donc
    aucune garantie réelle supplémentaire dans ce contexte précis, pour le
    prix d'une brique technique (PL/pgSQL) absente du reste du projet et
    d'une perte de lisibilité (la logique d'écriture ne serait plus
    entièrement visible dans `evenements.py`).

12. **Verrouillage à la clôture du dossier**, dès cette itération. Le
    projet a déjà un mécanisme générique pour ça : `_bloquer_si_clos()`
    dans `app/blueprints/dossiers/routes.py`, déjà appelé en tête de
    *toutes* les routes d'écriture du blueprint dossiers. Aucun nouveau
    mécanisme à construire : les routes d'écriture sur `evenement`
    (création, modification, changement de dossier, annulation,
    réactivation) appellent ce même helper, exactement comme le reste du
    blueprint — un dossier clos n'accepte alors plus aucune action sur ses
    événements, cohérent avec le fait qu'il s'agit déjà d'un dossier qu'on
    ne retouche plus.

## Pourquoi pas un trigger (détail du point 11)

Un trigger `BEFORE UPDATE` garantirait la capture d'historique
indépendamment du chemin de code emprunté — y compris une modification
faite à la main depuis `psql`. C'est un vrai avantage en théorie. Mais :

- Le seul utilisateur capable d'exécuter une requête `psql` directe sur la
  base est le titulaire (accès serveur), qui a par construction aussi les
  moyens de modifier ou désactiver un trigger. Le trigger ne protège donc
  contre aucun scénario réel dans ce contexte à 2-3 utilisateurs.
- Aucune des 24 migrations existantes n'utilise de fonction PL/pgSQL ni de
  trigger : ce serait une brique technique entièrement nouvelle, pour un
  seul besoin.
- La couche repository impose déjà que toute écriture applicative passe
  par une fonction Python unique (`routes.py` n'écrit jamais de SQL
  directement) — le trigger dupliquerait une garantie déjà largement
  couverte par cette discipline architecturale.

Historisation donc entièrement en Python, dans la même transaction que
l'écriture qu'elle précède.

## Schéma proposé

Numéro de migration à vérifier avant de commencer (`0025` en l'état de la
dernière synchronisation avec GitHub — peut avoir avancé côté poste de
travail) :

```sql
-- migrations/00XX.cree-tables-evenement.sql
-- depends: 00XX-1.<dernière migration en date>

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
-- pour tous les cas, appliqué en code Python (voir plus bas), pas par
-- trigger. modifie_par/modifie_le identifient qui a produit ce
-- changement et quand ; les colonnes restantes sont l'état de la ligne
-- juste avant ce changement.
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
```

Rollback symétrique classique (`DROP TABLE evenement_historique; DROP TABLE
evenement; DROP TABLE type_evenement;` — l'ordre inverse des créations, à
cause des clés étrangères).

**Choix délibérément écartés à ce stade** (simplicité d'abord, ajout non
cassant possible plus tard par un simple `ALTER TABLE ADD COLUMN`) :
- Pas de colonne `heure_debut` — la date suffit pour la chronologie, la
  durée suffit pour la justification du temps passé.
- Pas d'index explicite sur `dossier_id` — cohérent avec le reste du
  schéma actuel (seul `document_email.message_id` a un index dédié).

## Dataclasses (`app/modeles.py`)

```python
@dataclass
class TypeEvenement:
    id: int
    libelle: str
    actif: bool


@dataclass
class Evenement:
    """Ce qui s'est passé sur un dossier (rdv, appel, audience...), par
    opposition à echeance qui porte sur ce qui est prévu. contenu est
    toujours renseigné. Pas de suppression : annule_le/annule_par/
    motif_annulation portent une annulation réversible. modifie_par/
    modifie_le ne reflètent que la dernière écriture — voir
    evenement_historique (app/repositories/evenements.py) pour
    l'historique complet."""

    id: int
    dossier_id: int
    type_evenement_id: int
    date_evenement: date
    duree_minutes: int | None
    contenu: str
    echeance_id: int | None
    document_id: int | None
    annule_le: datetime | None
    annule_par: int | None
    motif_annulation: str | None
    cree_par: int | None
    cree_le: datetime
    modifie_par: int | None
    modifie_le: datetime | None


@dataclass
class EvenementHistorique:
    id: int
    evenement_id: int
    dossier_id: int
    type_evenement_id: int
    date_evenement: date
    duree_minutes: int | None
    contenu: str
    annule_le: datetime | None
    annule_par: int | None
    motif_annulation: str | None
    modifie_par: int | None
    modifie_le: datetime
```

## Repositories

- **`app/repositories/types_evenement.py`** — copie conforme de
  `categories_echeance.py` : `lister(actives_seulement=True)`,
  `creer(libelle)`, `basculer_actif(type_id)`.

- **`app/repositories/evenements.py`** :
  - `creer(dossier_id, type_evenement_id, date_evenement, duree_minutes, contenu, utilisateur_id, echeance_id=None)`
  - `modifier(evenement_id, type_evenement_id, date_evenement, duree_minutes, contenu, utilisateur_id)` —
    historise puis met à jour ; ne touche jamais `dossier_id`.
  - `changer_dossier(evenement_id, nouveau_dossier_id, utilisateur_id)` —
    historise puis met à jour uniquement `dossier_id` ; fonction séparée de
    `modifier()` car sa route sera gatée `@role_requis("avocat", "collaborateur")`,
    contrairement au reste.
  - `annuler(evenement_id, utilisateur_id, motif=None)` — historise puis
    renseigne `annule_le`/`annule_par`/`motif_annulation`.
  - `reactiver(evenement_id, utilisateur_id)` — historise puis remet les
    trois colonnes d'annulation à `NULL`.
  - `recuperer(evenement_id)`, `lister_pour_dossier(dossier_id, inclure_annules=False)`
    (tri par date décroissante — historique, contrairement à
    `echeances.lister_pour_dossier`).
  - `lister_historique(evenement_id)` — pour l'écran "voir l'historique".
  - Une fonction interne `_historiser(cur, evenement_id)` (appelée par les
    quatre fonctions d'écriture ci-dessus, dans la même transaction) :
    `INSERT INTO evenement_historique SELECT ... FROM evenement WHERE id = %s`
    puis l'`UPDATE` proprement dit — un seul endroit qui porte cette
    logique plutôt que la répéter quatre fois.

## Routes et interface

### `parametres/` — gestion des types d'événement

Copie conforme du bloc "Catégories d'échéance" existant (`routes.py`,
`forms.py`, template, lien de menu). Réservé `avocat`/`collaborateur`.

### `dossiers/` — création, consultation, cycle de vie

Toutes les routes d'écriture ci-dessous commencent par
`blocage = _bloquer_si_clos(dossier_id)` (`if blocage: return blocage`),
exactement comme les routes `echeances` existantes — pas de nouveau
mécanisme de verrouillage, réutilisation du helper déjà en place.

- `POST /<dossier_id>/evenements` — création.
- `POST /<dossier_id>/evenements/<evenement_id>/modifier` — correction du
  contenu/type/date/durée. Accessible à tout compte connecté.
- `POST /<dossier_id>/evenements/<evenement_id>/deplacer` — changement de
  dossier de rattachement. `@role_requis("avocat", "collaborateur")` en
  plus du `_bloquer_si_clos` (sur le dossier d'origine).
- `POST /<dossier_id>/evenements/<evenement_id>/annuler` — annulation,
  avec champ de motif optionnel dans le formulaire.
- `POST /<dossier_id>/evenements/<evenement_id>/reactiver` — réactivation.
- `GET /<dossier_id>/evenements/<evenement_id>/historique` — liste des
  versions passées (`evenement_historique`), en lecture seule.

Sur la fiche dossier : section "Événements" sur le modèle de la section
"Échéances" actuelle. Chaque ligne affiche `modifie_par`/`modifie_le`
quand ils sont renseignés ("modifié le 12/09 à 14h32 par [nom]"), un lien
"historique" si des versions passées existent, et — pour les événements
annulés, masqués par défaut — un lien "Afficher aussi les événements
annulés" (même idiome que `actives_seulement` sur `matiere`/
`categorie_echeance`).

### Raccourci échéance → événement

Réutilise l'idiome déjà présent (préremplissage par paramètre de requête,
voir `echeance_document_id` existant sur la fiche dossier) : un lien
« Clôturer avec compte-rendu » à côté du bouton « Marquer fait » sur
chaque échéance, préremplissant la création d'un événement
(`echeance_id` cadré, date du jour). À la soumission, l'événement est créé
puis, si `echeance_id` est renseigné, `echeances_repo.marquer_fait` est
appelé dans la foulée. Le bouton « Marquer fait » simple reste disponible
pour les échéances qui ne sont pas des échanges oraux.

### Chronologie

`GET /<dossier_id>/chronologie` — fusionne en mémoire (pas de nouvelle
table) `evenements_repo.lister_pour_dossier(dossier_id)` (date =
`date_evenement`, événements annulés exclus) et
`documents_repo.lister_pour_dossier(dossier_id)` (date = `date_tri`),
triés ensemble par date décroissante. Pur Python stdlib (`sorted()`), pas
de dépendance nouvelle.

## Détails à trancher pendant l'implémentation (mineurs, non bloquants)

1. **Suggestion de type par catégorie d'échéance** lors du raccourci
   clôture (une échéance "Audience" pourrait présuggérer le type
   d'événement "Audience") : confort, pas indispensable au départ.
2. **Annulation d'un événement lié à une échéance déjà marquée "fait" par
   ce biais** : faut-il proposer de rouvrir l'échéance en même temps ? À
   voir à l'usage — ne pas construire cette symétrie avant qu'un besoin
   réel se présente.
3. Une fois posé, ajouter un paragraphe dans la section *Domain model* de
   `CLAUDE.md`, sur le modèle des paragraphes `dossier`/`document`
   existants.

## Ordre de mise en œuvre suggéré

Ce morceau est plus gros que les précédents (deux tables, deux
repositories, cinq routes d'écriture, quatre templates) — d'où l'intérêt
de le découper en étapes vérifiables une à une, chacune plus petite qu'un
commit du projet jusqu'ici, plutôt que d'écrire tout d'un bloc et de
découvrir les problèmes seulement à la fin. Il n'y a pas de suite de tests
automatisés dans ce projet (voir `CLAUDE.md`) : chaque étape doit donc
rester vérifiable à la main, sur le modèle de
`scripts/verifier_contacts.py`, avant de passer à la suivante.

1. **Migration seule** (`type_evenement`, `evenement`,
   `evenement_historique`). Appliquer (`yoyo apply`), vérifier la structure
   (`psql`, `\d evenement`), et tester à la main les deux contraintes qui
   portent la fiabilité de toute la fonctionnalité : un `INSERT` avec
   `contenu` vide ou uniquement des espaces doit être rejeté ; un `INSERT`
   avec `annule_le` renseigné et `annule_par` `NULL` (ou l'inverse) aussi.
   Rien d'autre à coder à ce stade.

2. **Dataclasses** (`TypeEvenement`, `Evenement`, `EvenementHistorique`
   dans `app/modeles.py`) — mécanique, pas de logique, pas de vérification
   à part une relecture.

3. **`app/repositories/types_evenement.py`** (copie conforme de
   `categories_echeance.py`). Vérifiable directement en Python
   (`./venv/bin/python`, appel des trois fonctions à la main) sans
   toucher à Flask.

4. **`app/repositories/evenements.py`**, y compris `_historiser` et les
   six fonctions d'écriture/lecture. C'est le cœur de la fonctionnalité :
   je recommande d'écrire un petit script de vérification dédié (sur le
   modèle de `scripts/verifier_contacts.py`) qui crée un événement, le
   modifie deux fois de suite, l'annule puis le réactive, et affiche à
   chaque étape le contenu de `evenement_historique` — pour confirmer que
   l'historique capture bien chaque version *avant* qu'elle soit écrasée,
   avant d'aller plus loin. C'est l'endroit où un bug serait le plus coûteux
   à détecter tardivement, une fois caché derrière une interface qui a l'air
   de fonctionner.

5. **Gestion des types d'événement dans `parametres/`** (routes, forms,
   template, lien de menu). Petit et sans risque, copie conforme d'un bloc
   existant — mais nécessaire avant l'étape 6 pour avoir de vraies valeurs
   à proposer dans le formulaire de création d'événement. Vérifiable au
   navigateur : créer/désactiver un type.

6. **Boucle de base sur `dossiers/`** : `EvenementForm`, routes de création
   et de modification, section "Événements" sur la fiche dossier
   (affichage simple, y compris `modifie_par`/`modifie_le` quand
   renseignés). Objectif de cette étape : pouvoir créer et corriger un
   événement de bout en bout au navigateur. Tout le reste (annulation,
   déplacement, raccourci, historique, chronologie) est un ajout sur cette
   base, pas une dépendance pour qu'elle fonctionne.

7. **Annulation / réactivation** (routes, formulaire avec motif optionnel,
   affichage "masqué par défaut" + lien pour les faire réapparaître).

8. **Changement de dossier de rattachement** (route réservée
   `avocat`/`collaborateur`). Mis après le reste volontairement : c'est la
   pièce qui demande le plus d'interface neuve (choisir un autre dossier),
   pour la fonctionnalité la moins fréquente des cinq actions d'écriture.

9. **Raccourci échéance → événement** (lien "Clôturer avec compte-rendu",
   préremplissage par paramètre de requête, `marquer_fait` déclenché après
   création). Dépend de l'étape 6 (le formulaire de création doit déjà
   exister) mais de rien d'autre.

10. **Écran d'historique** (`GET .../historique`, template dédié).
    `evenements_repo.lister_historique` existe déjà depuis l'étape 4 ; il
    ne reste que la route et l'affichage.

11. **Chronologie** (fusion événements + documents, route, template).
    Entièrement en lecture seule et indépendante du reste : peut se faire
    à n'importe quel moment après l'étape 6, mais logiquement en dernier
    puisqu'elle assemble des briques déjà posées.

12. **`CLAUDE.md`** — paragraphe *Domain model* décrivant `evenement`, une
    fois le comportement réel stabilisé par l'usage (pas avant, pour ne
    pas documenter une intention qui pourrait encore bouger à l'étape 6-7).

Comme pour les phases précédentes (`git log` : un commit par étape
cohérente — "Ajout échéances", "Catégories matieres"...), un commit après
chacune des étapes 1, 4, 6, 8/9 et 11 parait un bon découpage : assez fin
pour revenir en arrière facilement en cas de souci, assez grossier pour ne
pas fragmenter l'historique.

## Fichiers à créer ou modifier

```
migrations/00XX.cree-tables-evenement.sql          (nouveau)
migrations/00XX.cree-tables-evenement.rollback.sql (nouveau)
app/modeles.py                                     (+ TypeEvenement, Evenement,
                                                       EvenementHistorique)
app/repositories/types_evenement.py                (nouveau)
app/repositories/evenements.py                     (nouveau)
app/blueprints/parametres/forms.py                 (+ NouveauTypeEvenementForm)
app/blueprints/parametres/routes.py                (+ bloc types d'événement)
app/templates/parametres/types_evenement.html      (nouveau)
app/blueprints/dossiers/forms.py                   (+ EvenementForm,
                                                       + AnnulerEvenementForm,
                                                       + DeplacerEvenementForm)
app/blueprints/dossiers/routes.py                  (+ routes evenements,
                                                       + raccourci clôture,
                                                       + route chronologie,
                                                       + route historique)
app/templates/dossiers/fiche.html                  (+ section Événements,
                                                       + lien Chronologie)
app/templates/dossiers/chronologie.html            (nouveau)
app/templates/dossiers/evenement_historique.html   (nouveau)
CLAUDE.md                                          (+ paragraphe Domain model,
                                                       une fois implémenté)
```