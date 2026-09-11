from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.repositories import documents as documents_repo
from app.repositories import dossiers
from app.services import messagerie, stockage_documents
from app.services.messagerie import ErreurSynchronisation

bp = Blueprint("messagerie", __name__, url_prefix="/messagerie")


def _email_ou_404(document_id):
    document = documents_repo.recuperer(document_id)
    if document is None or document.type_document != "email":
        abort(404)
    return document


@bp.route("/")
@login_required
def index():
    return render_template("messagerie/index.html")


@bp.route("/synchroniser", methods=["POST"])
@login_required
def synchroniser():
    try:
        compte_rendu = messagerie.synchroniser()
    except ErreurSynchronisation as e:
        flash(f"Synchronisation impossible : {e}", "erreur")
        return redirect(url_for("messagerie.index"))
    return render_template("messagerie/compte_rendu.html", compte_rendu=compte_rendu)


@bp.route("/emails/<int:document_id>")
@login_required
def consulter_email(document_id):
    document = _email_ou_404(document_id)
    message = messagerie.lire_message(document)
    return render_template(
        "messagerie/email.html",
        document=document,
        document_email=documents_repo.recuperer_email(document_id),
        corps=messagerie.corps_texte(message),
        pieces_jointes=messagerie.pieces_jointes(message),
        dossier=dossiers.recuperer(document.dossier_id),
    )


@bp.route("/emails/<int:document_id>/pieces-jointes/<int:index>/verser", methods=["POST"])
@login_required
def verser_piece_jointe(document_id, index):
    document = _email_ou_404(document_id)
    message = messagerie.lire_message(document)
    try:
        nom, contenu = messagerie.extraire_piece_jointe(message, index)
    except ValueError:
        abort(404)

    chemin_fichier = stockage_documents.enregistrer(document.dossier_id, nom, contenu)
    documents_repo.creer_depose(
        dossier_id=document.dossier_id,
        titre=nom,
        chemin_fichier=chemin_fichier,
        utilisateur_id=current_user.id,
        document_origine_id=document.id,
    )
    flash(f"« {nom} » versé au dossier.", "succes")
    return redirect(url_for("messagerie.consulter_email", document_id=document_id))
