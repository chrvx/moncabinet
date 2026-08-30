from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
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
