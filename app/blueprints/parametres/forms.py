from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
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
    categorie_id = SelectField("Catégorie", validators=[DataRequired()])
    soumettre = SubmitField("Ajouter")


class ChangerCategorieMatiereForm(FlaskForm):
    """Affordance inline de reclassement d'une matière existante, une
    instance par ligne sur parametres/matieres."""

    categorie_id = SelectField("Catégorie", validators=[DataRequired()])
    soumettre = SubmitField("Changer la catégorie")


class NouvelleCategorieEcheanceForm(FlaskForm):
    libelle = StringField(
        "Nouvelle catégorie", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ajouter")


class NouvelleCategorieMatiereForm(FlaskForm):
    libelle = StringField(
        "Nouvelle catégorie", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ajouter")
