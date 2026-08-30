from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired


class ConnexionForm(FlaskForm):
    nom = StringField("Nom d'utilisateur", validators=[DataRequired(message="Ce champ est requis.")])
    mot_de_passe = PasswordField("Mot de passe", validators=[DataRequired(message="Ce champ est requis.")])
    soumettre = SubmitField("Se connecter")
