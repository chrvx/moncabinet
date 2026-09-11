from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional

from app.services.modeles_documents import ModeleDocument

#: Correspondance type de champ (metadata.json) -> classe de champ WTForms.
_CLASSES_CHAMP = {
    "texte": StringField,
    "zone_texte": TextAreaField,
    "case": BooleanField,
    "entier": IntegerField,
    "date": DateField,
}


def construire_formulaire(modele: ModeleDocument) -> FlaskForm:
    """Construit un FlaskForm à la volée à partir des champs_extra du
    modèle : ce sont des mentions non déductibles du dossier/contact
    (montant d'une prestation compensatoire, mentions particulières...),
    propres à ce modèle."""
    champs = {}
    for champ_extra in modele.champs_extra:
        classe_champ = _CLASSES_CHAMP[champ_extra.type]
        validateurs = [] if champ_extra.type == "case" else [Optional()]
        champs[champ_extra.nom] = classe_champ(champ_extra.label, validators=validateurs)
    champs["soumettre"] = SubmitField("Générer le document")

    classe_formulaire = type("FormulaireGenerationDocument", (FlaskForm,), champs)
    return classe_formulaire()


class DeposerDocumentForm(FlaskForm):
    """Dépôt d'un fichier externe (scan, pièce jointe récupérée à la main,
    clé USB...) — la case "c'est une pièce" révèle provenance et date de
    transmission ; le numéro de pièce n'est pas saisi ici, il n'est attribué
    qu'au moment de la communication formelle."""

    fichier = FileField("Fichier", validators=[FileRequired(message="Choisissez un fichier.")])
    titre = StringField("Titre", validators=[DataRequired(message="Ce champ est requis.")])
    est_piece = BooleanField("C'est une pièce")
    contact_provenance_id = SelectField("Provenance", validators=[Optional()])
    date_transmission = DateField("Date de transmission", validators=[Optional()])
    soumettre = SubmitField("Déposer")


class MarquerPieceForm(FlaskForm):
    """Marque un document déjà présent sur le dossier comme pièce —
    mêmes champs que la case "c'est une pièce" du dépôt."""

    contact_provenance_id = SelectField("Provenance", validators=[DataRequired()])
    date_transmission = DateField("Date de transmission", validators=[Optional()])
    soumettre = SubmitField("Marquer comme pièce")
