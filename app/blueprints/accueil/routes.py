from flask import Blueprint, render_template
from flask_login import login_required

from app.repositories import contacts, documents, dossiers, matieres

# Un "blueprint" regroupe un ensemble de routes qui vont ensemble (ici, les
# pages d'accueil). Chaque futur domaine métier (contacts, dossiers...) aura
# le sien, enregistré dans app/__init__.py comme celui-ci.
bp = Blueprint("accueil", __name__)

NB_DOSSIERS_RECENTS = 5
NB_DOCUMENTS_RECENTS = 5


@bp.route("/")
@login_required
def index():
    dossiers_recents = [
        (d, dossiers.nom_calcule(d.id))
        for d in dossiers.lister_ouverts_recents(NB_DOSSIERS_RECENTS)
    ]

    return render_template(
        "accueil/index.html",
        nb_dossiers_ouverts=len(dossiers.lister_ouverts()),
        nb_dossiers_brouillons=len(dossiers.lister_brouillons()),
        nb_contacts=contacts.compter(),
        nb_documents_ce_mois=documents.compter_ce_mois(),
        dossiers_recents=dossiers_recents,
        matiere_libelles={m.id: m.libelle for m in matieres.lister(actives_seulement=False)},
        documents_recents=documents.lister_recents(NB_DOCUMENTS_RECENTS),
    )
