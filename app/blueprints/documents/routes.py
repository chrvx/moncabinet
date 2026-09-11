from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.blueprints.documents.forms import DeposerDocumentForm, MarquerPieceForm, construire_formulaire
from app.repositories import documents as documents_repo
from app.repositories import dossiers
from app.services import generation_documents, modeles_documents, stockage_documents
from app.services.generation_documents import ErreurGenerationDocument

bp = Blueprint("documents", __name__, url_prefix="/dossiers/<int:dossier_id>/documents")


def _dossier_ou_404(dossier_id):
    dossier = dossiers.recuperer(dossier_id)
    if dossier is None:
        abort(404)
    return dossier


def _document_ou_404(dossier_id, document_id):
    document = documents_repo.recuperer(document_id)
    if document is None or document.dossier_id != dossier_id:
        abort(404)
    return document


def _choix_contacts_dossier(dossier_id, avec_vide=True):
    """Contacts déjà liés au dossier, dédoublonnés (un même contact peut
    porter plusieurs rôles) — utilisé comme liste de provenance pour une
    pièce, patron _choix_avec_vide de app/blueprints/dossiers/routes.py."""
    vus = {}
    for i in dossiers.lister_intervenants(dossier_id):
        vus.setdefault(i["contact_id"], i["nom_contact"])
    choix = sorted(vus.items(), key=lambda c: c[1])
    return ([("", "—")] + choix) if avec_vide else choix


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


@bp.route("/deposer", methods=["GET", "POST"])
@login_required
def deposer(dossier_id):
    dossier = _dossier_ou_404(dossier_id)
    if dossier.statut == "clos":
        flash("Ce dossier est clos : rouvrez-le avant de déposer un document.", "erreur")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))

    formulaire = DeposerDocumentForm()
    formulaire.contact_provenance_id.choices = _choix_contacts_dossier(dossier_id)

    if formulaire.validate_on_submit():
        if formulaire.est_piece.data and not formulaire.contact_provenance_id.data:
            flash("Choisissez la provenance de la pièce.", "erreur")
        else:
            chemin_fichier = stockage_documents.enregistrer(
                dossier_id, formulaire.fichier.data.filename, formulaire.fichier.data.read()
            )
            document = documents_repo.creer_depose(
                dossier_id=dossier_id,
                titre=formulaire.titre.data,
                chemin_fichier=chemin_fichier,
                utilisateur_id=current_user.id,
            )
            if formulaire.est_piece.data:
                documents_repo.marquer_piece(
                    document_id=document.id,
                    contact_provenance_id=int(formulaire.contact_provenance_id.data),
                    date_transmission=formulaire.date_transmission.data,
                )
            flash(f"Document « {document.titre} » déposé.", "succes")
            return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))

    return render_template("documents/deposer.html", dossier=dossier, formulaire=formulaire)


@bp.route("/<int:document_id>/marquer-piece", methods=["GET", "POST"])
@login_required
def marquer_piece(dossier_id, document_id):
    dossier = _dossier_ou_404(dossier_id)
    document = _document_ou_404(dossier_id, document_id)
    if documents_repo.recuperer_piece(document_id) is not None:
        flash(f"« {document.titre} » est déjà marqué comme pièce.", "info")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))

    formulaire = MarquerPieceForm()
    formulaire.contact_provenance_id.choices = _choix_contacts_dossier(dossier_id, avec_vide=False)

    if formulaire.validate_on_submit():
        documents_repo.marquer_piece(
            document_id=document.id,
            contact_provenance_id=int(formulaire.contact_provenance_id.data),
            date_transmission=formulaire.date_transmission.data,
        )
        flash(f"Document « {document.titre} » marqué comme pièce.", "succes")
        return redirect(url_for("dossiers.fiche", dossier_id=dossier_id))

    return render_template(
        "documents/marquer_piece.html", dossier=dossier, document=document, formulaire=formulaire
    )


@bp.route("/<int:document_id>/telecharger")
@login_required
def telecharger(dossier_id, document_id):
    document = _document_ou_404(dossier_id, document_id)
    extension = Path(document.chemin_fichier).suffix
    return send_file(
        generation_documents.resoudre_chemin(document.chemin_fichier),
        download_name=f"{document.titre}{extension}",
    )


@bp.route("/<int:document_id>/telecharger/typ")
@login_required
def telecharger_typ(dossier_id, document_id):
    document = _document_ou_404(dossier_id, document_id)
    document_genere = documents_repo.recuperer_genere(document_id)
    if document_genere is None:
        abort(404)
    return send_file(
        generation_documents.resoudre_chemin(document_genere.chemin_typ),
        download_name=f"{document.titre}.typ",
        as_attachment=True,
    )
