from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional


class NouveauDossierForm(FlaskForm):
    """Pas de champ métier : la création se fait en un clic depuis la
    fiche d'un contact, qui devient automatiquement client du dossier."""

    contact_id = HiddenField(validators=[DataRequired()])
    soumettre = SubmitField("Nouveau dossier")


class OuvrirDossierForm(FlaskForm):
    reference = StringField(
        "Référence", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ouvrir le dossier")


class ModifierDossierForm(FlaskForm):
    categorie = SelectField(
        "Catégorie",
        choices=[("", "—"), ("juridique", "Juridique (conseil)"), ("judiciaire", "Judiciaire (contentieux)")],
        validators=[Optional()],
    )
    matiere_id = SelectField("Matière", validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class AjouterIntervenantForm(FlaskForm):
    contact_id = HiddenField(validators=[DataRequired(message="Choisissez un contact dans les suggestions.")])
    type_role_id = SelectField("Rôle", validators=[DataRequired()])
    contact_lie_id = SelectField(
        "Contact lié (si le rôle l'exige)", validators=[Optional()]
    )
    soumettre = SubmitField("Ajouter au dossier")


class AjouterRoleForm(FlaskForm):
    """Comme AjouterIntervenantForm, mais pour un contact déjà présent sur
    le dossier : pas de champ contact_id, il vient de l'URL
    (dossiers.ajouter_role) plutôt que d'un champ cible rempli par
    recherche_contact.js — ce contact est déjà connu, inutile de le
    rechercher à nouveau."""

    type_role_id = SelectField("Rôle", validators=[DataRequired()])
    contact_lie_id = SelectField(
        "Contact lié (si le rôle l'exige)", validators=[Optional()]
    )
    soumettre = SubmitField("Ajouter ce rôle")
