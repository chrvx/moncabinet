from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.blueprints.documents.forms import construire_formulaire
from app.repositories import documents as documents_repo
from app.repositories import dossiers
from app.services import generation_documents, modeles_documents
from app.services.generation_documents import ErreurGenerationDocument

bp = Blueprint("documents", __name__, url_prefix="/dossiers/<int:dossier_id>/documents")


def _dossier_ou_404(dossier_id):
    dossier = dossiers.recuperer(dossier_id)
    if dossier is None:
        abort(404)
    return dossier


@bp.route("/nouveau", methods=["GET", "POST"])
@login_required
def nouveau(dossier_id):
    dossier = _dossier_ou_404(dossier_id)
    if dossier.statut == "clos":
        flash("Ce dossier est clos : rouvrez-le avant de générer un document.", "erreur")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))

    slug = request.values.get("modele")
    modele = modeles_documents.recuperer(slug) if slug else None
    if modele is None:
        flash("Modèle de document introuvable.", "erreur")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))

    formulaire = construire_formulaire(modele)
    if formulaire.validate_on_submit():
        champs_extra = {
            champ_extra.nom: getattr(formulaire, champ_extra.nom).data
            for champ_extra in modele.champs_extra
        }
        try:
            generation_documents.generer(dossier_id, modele, champs_extra, current_user.id)
            flash(f"Document « {modele.libelle} » généré.", "succes")
            return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))
        except ErreurGenerationDocument as e:
            flash(f"Échec de la génération : {e}", "erreur")

    return render_template(
        "documents/nouveau.html", dossier=dossier, modele=modele, formulaire=formulaire
    )


def _document_ou_404(dossier_id, document_id):
    document = documents_repo.recuperer(document_id)
    if document is None or document.dossier_id != dossier_id:
        abort(404)
    return document


@bp.route("/<int:document_id>/telecharger/pdf")
@login_required
def telecharger_pdf(dossier_id, document_id):
    document = _document_ou_404(dossier_id, document_id)
    return send_file(
        generation_documents.resoudre_chemin(document.chemin_pdf),
        download_name=f"{document.titre}.pdf",
    )


@bp.route("/<int:document_id>/telecharger/typ")
@login_required
def telecharger_typ(dossier_id, document_id):
    document = _document_ou_404(dossier_id, document_id)
    return send_file(
        generation_documents.resoudre_chemin(document.chemin_typ),
        download_name=f"{document.titre}.typ",
        as_attachment=True,
    )
