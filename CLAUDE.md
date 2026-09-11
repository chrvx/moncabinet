# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Mon Cabinet" — a small internal case/contact management web app for a law firm (2-3 users). Flask + psycopg3 (raw SQL, no ORM) + PostgreSQL. The codebase, comments, commit history and UI are entirely in French; match that when writing code, comments, flash messages, or docs in this repo.

## Commands

Run everything through the venv interpreter rather than activating it:

```bash
./venv/bin/pip install -r requirements.txt   # install/update dependencies
. env.sh                                     # load DB_HOST/PORT/NAME/USER/PASSWORD into the shell
./venv/bin/python wsgi.py                    # run the dev server (http://localhost:5000)
./venv/bin/yoyo apply                        # apply pending migrations (reads yoyo.ini)
./venv/bin/yoyo list                         # check migration status / DB connectivity
./venv/bin/flask creer-utilisateur           # create a user account (no signup form exists — see app/commandes.py)
PYTHONPATH=. ./venv/bin/python scripts/verifier_contacts.py   # manual end-to-end smoke check of the contact model
```

There is no automated test suite and no linter configured — `scripts/verifier_contacts.py` is the only correctness check, and it's a script you read the console output of, not a pass/fail runner.

The `typst` CLI must be installed and on `PATH` (a single static binary, see https://github.com/typst/typst/releases — no package to `pip install`) for document generation (`app/services/generation_documents.py`) to work.

`yoyo.ini` (copied from `yoyo.ini.example`, gitignored) must use the `postgresql+psycopg://` scheme, not `postgresql://` — the latter makes yoyo try to use psycopg2, which isn't installed in this project.

## Architecture

**Layering is strict and one-directional:** `blueprints/*/routes.py` (HTTP/forms) → `repositories/*.py` (all SQL) → `app/modeles.py` (plain dataclasses, no behavior). Routes never write SQL directly; only the repository layer does. Repositories return dataclasses (via `psycopg.rows.class_row`), never raw tuples/dicts, to route/template code.

- **`app/db.py`** — a single module-level `psycopg_pool.ConnectionPool` (`pool`), created once in `create_app()`. Every repository function does `with db.pool.connection() as conn: with conn.cursor(...) as cur: ...` and calls `conn.commit()` explicitly after writes.
- **`app/config.py`** — all config from environment variables (see `env.sh`), with dev-only defaults. Never hardcode secrets.
- **`app/securite.py`** — Flask-Login wiring (`UtilisateurConnecte` wraps the `Utilisateur` dataclass) plus `role_requis(*roles)`, a decorator used to gate routes by role (`avocat`, `collaborateur`, `stagiaire`). This is the only permission mechanism so far — no per-record/RGPD visibility rules yet.
- **`app/normalisation.py`** — input normalization applied at write time only (never at display time): names/`nom_usage` uppercased, first names/birth cities title-cased, phone numbers stripped to digits (+prefix kept), emails lowercased. `raison_sociale` (company names) is deliberately never touched. Always route new writable name/phone/email fields through these helpers rather than normalizing ad hoc.
- **Blueprints** (`app/blueprints/{accueil,auth,contacts,dossiers}/`) each own `routes.py` and, where forms exist, `forms.py` (Flask-WTF). Route handlers build WTForms `choices` lists dynamically from repository lookups (pattern: `_choix_avec_vide(items, cle, libelle)` — see `contacts/routes.py` and `dossiers/routes.py`) rather than hardcoding option lists.
- **Migrations** (`migrations/*.sql` + matching `*.rollback.sql`, run by yoyo) are numbered sequentially (`0001`, `0002`, ...) with a descriptive kebab-case slug, e.g. `0008.cree-tables-dossier-matiere.sql`. Every migration has a corresponding rollback file. When adding schema changes, follow this naming and always write the rollback alongside the forward migration.
- **Document generation** (`app/services/generation_documents.py`, `app/services/modeles_documents.py`, `app/blueprints/documents/`) merges dossier/contact data into Typst (`.typ`) templates and compiles them to PDF via `typst compile` (subprocess). Typst was chosen over docx/odt-based templating (docxtpl, py3o.template) for deterministic cross-platform rendering and a real conditional/loop language for clause-heavy legal documents — see the design discussion referenced in git history for the full comparison. Templates are plain files under `app/documents_modeles/<slug>/` (`modele.typ` + `metadata.json` describing the extra fields to collect from the user), managed directly on the server/filesystem by a technical user — there is no upload UI by design. Generated PDFs and their merged `.typ` source are written under `instance/documents/` (gitignored) and tracked via the `document`/`document_genere` tables (see Domain model below) so a user can re-download the merged `.typ` and personalize it further locally with their own Typst tooling. Uploaded files (`documents.deposer`) are stored under the same tree with a generated (UUID) filename — never the attacker-controllable original filename — and only `document.titre` (not the original filename) is kept for display/download.

### Domain model

- **Contact** is a supertype with two specializations sharing the same `contact_id`: `personne_physique` (individual) and `personne_morale` (company) — see `app/repositories/contacts.py` for the two-insert-one-commit pattern used to create either.
- **Coordonnées** (adresse/telephone/email) are historized and shareable: each is a standalone table plus a join table (`contact_adresse`, `contact_telephone`, `contact_email`) carrying `date_debut`/`date_fin`/`douteux` (flagged-as-questionable, non-closing) per contact-to-coordinate link. The same address/phone/email row can be linked from multiple contacts (e.g. a couple sharing a home) instead of being duplicated. Adding a phone/email auto-detects and reuses an existing normalized value (`app/repositories/coordonnees.py`) rather than creating a duplicate row.
- **`role_contact`** attaches a contact to a `type_role` (client, adversaire, avocat adverse, etc.), optionally scoped to a `dossier_id` and/or pointing at another `contact_lie_id`. Each `type_role` carries `dossier_regle`/`contact_lie_regle` (`obligatoire`/`optionnel`/`interdit`) as *data*, validated by `app/repositories/roles.py::_valider_regle` — add new role types by inserting rows, not by adding conditional branches keyed on role name.
- **`dossier`** (case file) lifecycle: brouillon (draft, no reference) → ouvert (reference assigned, format `YYNNN`, backed by a per-year `compteur_dossier`) → clos. A dossier's display name is computed at render time from its client/adversaire roles (never stored) — see `dossiers.nom_calcule`.
- Anti-conflict-of-interest search (`contacts.rechercher_par_nom` / `rechercher_suggestions`) always searches across both `personne_physique` and `personne_morale`, unfiltered by role/permission — this is intentional; don't add visibility restrictions to it.
- **`document`** is a supertype attached to a `dossier`, covering every piece that concerns it — generated document, imported e-mail, or uploaded file — with the same two-insert-one-commit inheritance pattern as `contact` (`UNIQUE (id, type_document)` + `CHECK`-pinned specialization + composite FK). `type_document` distinguishes only what the app technically knows how to do with the file (`genere`: it produced it and keeps the merged `.typ` in `document_genere`; `email`: it parsed structured metadata into `document_email`; `depose`: everything else — scan, download, USB key — a plain upload with no extra table). Whether a document is correspondence or a communicable exhibit (`document_piece`, optional, attachable to any type) are separate, cumulable, cross-cutting traits, not sub-types — see `docs/phase-documents-correspondance.md` for the full reasoning. Uploaded files are saved under a generated (UUID) filename, never the original one, to prevent path traversal; lists sort on a computed `date_tri` (e-mail date, transmission date, or import date) rather than the import-only `cree_le`.

### Frontend

Server-rendered Jinja templates (`app/templates/`) with `_macros.html` for shared form/list rendering. Minimal vanilla JS (`app/static/js/`): `recherche_contact.js` drives live-suggestion autocomplete against `/contacts/api/suggestions`; `adresse.js` calls the Géoplateforme geocoding API (`data.geopf.fr`) client-side to prefill address fields, with manual entry as fallback if that call fails. No JS build step, no frontend framework.
