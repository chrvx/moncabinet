from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired


class NouveauBarreauForm(FlaskForm):
    libelle = StringField(
        "Nouveau barreau", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ajouter")


class NouvelleMatiereForm(FlaskForm):
    libelle = StringField(
        "Nouvelle matière", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ajouter")


class NouveauModeleEcheanceForm(FlaskForm):
    matiere_id = SelectField("Matière", validators=[DataRequired()])
    libelle = StringField("Libellé", validators=[DataRequired(message="Ce champ est requis.")])
    categorie_id = SelectField("Catégorie", validators=[DataRequired()])
    delai_jours = IntegerField(
        "Délai (en jours, à compter de l'ouverture du dossier)",
        validators=[DataRequired(message="Ce champ est requis.")],
    )
    soumettre = SubmitField("Ajouter")


class NouvelleCategorieEcheanceForm(FlaskForm):
    libelle = StringField(
        "Nouvelle catégorie", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ajouter")
