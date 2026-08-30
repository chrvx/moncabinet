from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import Optional

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
