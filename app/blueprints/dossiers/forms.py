from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, SelectField, StringField, SubmitField, TimeField
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


class EcheanceForm(FlaskForm):
    """Sert à la fois pour ajouter une échéance et pour la modifier. Les
    choix de categorie_id sont peuplés dynamiquement dans la route depuis
    categories_echeance (table de référence éditable), comme matiere_id
    pour ModifierDossierForm."""

    categorie_id = SelectField("Catégorie", validators=[DataRequired()])
    libelle = StringField("Libellé", validators=[DataRequired(message="Ce champ est requis.")])
    date_echeance = DateField("Date", validators=[DataRequired(message="Ce champ est requis.")])
    heure_echeance = TimeField("Heure (facultatif)", validators=[Optional()])
    notes = StringField("Notes", validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class AjouterModeleEcheanceForm(FlaskForm):
    """Instanciation d'un modèle d'échéance suggéré : mêmes champs que
    EcheanceForm, pré-remplis depuis le modèle (libellé, catégorie, date
    calculée à partir de la date d'ouverture) mais modifiables avant
    enregistrement — notamment la date, quand le point de départ réel
    diffère de l'ouverture du dossier (ex: date de la déclaration d'appel)."""

    modele_id = HiddenField(validators=[DataRequired()])
    categorie_id = SelectField("Catégorie", validators=[DataRequired()])
    libelle = StringField("Libellé", validators=[DataRequired(message="Ce champ est requis.")])
    date_echeance = DateField("Date", validators=[DataRequired(message="Ce champ est requis.")])
    heure_echeance = TimeField("Heure (facultatif)", validators=[Optional()])
    soumettre = SubmitField("Ajouter cette échéance")


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
