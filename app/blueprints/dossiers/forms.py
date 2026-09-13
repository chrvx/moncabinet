from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, IntegerField, SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, NumberRange, Optional


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
    # Rempli quand le formulaire est ouvert depuis le lien "créer une
    # échéance" d'un document (compte rendu de synchronisation, fiche
    # e-mail) — voir dossiers.routes::fiche et documents.Document.
    document_id = HiddenField(validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class EvenementForm(FlaskForm):
    """Sert à la fois pour ajouter un événement et pour le corriger. Les
    choix de type_evenement_id sont peuplés dynamiquement dans la route
    depuis types_evenement (table de référence éditable), comme
    categorie_id pour EcheanceForm."""

    type_evenement_id = SelectField("Type", validators=[DataRequired()])
    date_evenement = DateField("Date", validators=[DataRequired(message="Ce champ est requis.")])
    duree_minutes = IntegerField(
        "Durée (minutes, facultatif)", validators=[Optional(), NumberRange(min=1)]
    )
    contenu = TextAreaField("Contenu", validators=[DataRequired(message="Ce champ est requis.")])
    # Rempli quand le formulaire est ouvert depuis le lien "Clôturer avec
    # compte-rendu" d'une échéance — voir dossiers.routes::fiche.
    echeance_id = HiddenField(validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class AnnulerEvenementForm(FlaskForm):
    motif_annulation = StringField("Motif (facultatif)", validators=[Optional()])
    soumettre = SubmitField("Annuler l'événement")


class DeplacerEvenementForm(FlaskForm):
    """Changement de dossier de rattachement d'un événement — réservé
    avocat/collaborateur (voir dossiers.deplacer_evenement). Les choix de
    nouveau_dossier_id sont peuplés dynamiquement dans la route avec les
    dossiers ouverts, référence et nom calculé à l'appui."""

    nouveau_dossier_id = SelectField("Nouveau dossier", validators=[DataRequired()])
    soumettre = SubmitField("Déplacer l'événement")


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
