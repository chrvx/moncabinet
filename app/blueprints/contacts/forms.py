import re

from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, ValidationError

# Les SelectField ci-dessous ont leurs choix remplis dynamiquement dans la
# route, à partir des tables de référence en base (civilite, departement,
# pays) — WTForms ne sait pas interroger la base tout seul. La valeur ""
# représente "non renseigné" ; elle est convertie en None avant d'être
# transmise au repository (voir routes.py).


class NouvellePersonnePhysiqueForm(FlaskForm):
    """Formulaire minimal : seul le nom est obligatoire. Le reste se
    complète depuis la fiche, une fois le contact créé."""

    nom = StringField("Nom", validators=[DataRequired(message="Ce champ est requis.")])
    prenom = StringField("Prénom", validators=[Optional()])
    soumettre = SubmitField("Créer")


class NouvellePersonneMoraleForm(FlaskForm):
    raison_sociale = StringField(
        "Raison sociale", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Créer")


class ModifierPersonnePhysiqueForm(FlaskForm):
    nom = StringField("Nom", validators=[DataRequired(message="Ce champ est requis.")])
    prenom = StringField("Prénom", validators=[Optional()])
    prenoms_secondaires = StringField("Prénoms secondaires", validators=[Optional()])
    nom_usage = StringField("Nom d'usage", validators=[Optional()])
    genre = SelectField("Genre", validators=[Optional()])
    civilite_id = SelectField("Civilité", validators=[Optional()])
    date_naissance = DateField("Date de naissance", validators=[Optional()])
    ville_naissance = StringField("Ville de naissance", validators=[Optional()])
    departement_naissance_id = SelectField(
        "Département de naissance (si né en France)", validators=[Optional()]
    )
    pays_naissance_id = SelectField(
        "Pays de naissance (si né à l'étranger)", validators=[Optional()]
    )
    nationalite_id = SelectField("Nationalité", validators=[Optional()])
    profession = StringField("Profession", validators=[Optional()])
    siren = StringField("SIREN", validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class ModifierPersonneMoraleForm(FlaskForm):
    raison_sociale = StringField(
        "Raison sociale", validators=[DataRequired(message="Ce champ est requis.")]
    )
    forme = StringField("Forme juridique", validators=[Optional()])
    siren = StringField("SIREN", validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class AjouterAdresseForm(FlaskForm):
    # adresse_recherche + les cinq champs cachés qui suivent sont remplis
    # par le JavaScript d'autocomplétion (voir fiche.html) quand
    # l'utilisateur choisit une suggestion. Rien n'empêche de les modifier
    # ou de les remplir à la main si l'autocomplétion échoue.
    adresse_recherche = StringField(
        "Rechercher l'adresse (numéro, voie, commune)", validators=[Optional()]
    )
    numero_voie = StringField("Numéro de voie", validators=[Optional()])
    libelle_voie = StringField("Libellé de la voie", validators=[Optional()])
    code_postal = StringField("Code postal", validators=[Optional()])
    commune = StringField("Commune", validators=[Optional()])
    code_insee_commune = HiddenField(validators=[Optional()])
    latitude = HiddenField(validators=[Optional()])
    longitude = HiddenField(validators=[Optional()])
    libelle_complet_ban = HiddenField(validators=[Optional()])
    # Champs que l'API BAN ne connaît pas : toujours saisis à la main.
    complement = StringField(
        "Complément (appartement, étage, boîte aux lettres...)",
        validators=[Optional()],
    )
    entree_batiment = StringField(
        "Entrée / bâtiment / résidence", validators=[Optional()]
    )
    mention_distribution_type = SelectField(
        "Mention spéciale de distribution",
        choices=[
            ("", "—"), ("BP", "BP"), ("TSA", "TSA"),
            ("CS", "CS"), ("LIEU_DIT", "Lieu-dit"),
        ],
        validators=[Optional()],
    )
    mention_distribution_valeur = StringField(
        "Numéro ou libellé de la mention", validators=[Optional()]
    )
    code_cedex = StringField("Code CEDEX (si applicable)", validators=[Optional()])
    numero_cedex = StringField("Numéro CEDEX (si applicable)", validators=[Optional()])
    pays_id = SelectField("Pays (laisser vide si France)", validators=[Optional()])
    mention_destinataire = StringField(
        'Mention destinataire ("chez untel", "service juridique"...)',
        validators=[Optional()],
    )
    soumettre = SubmitField("Ajouter cette adresse")


class CorrigerAdresseForm(AjouterAdresseForm):
    """Mêmes champs que AjouterAdresseForm, mais pour corriger une faute de
    frappe sur une adresse existante (UPDATE en place, pas de nouveau lien)
    plutôt qu'en ajouter une nouvelle — voir contacts.corriger_adresse."""

    soumettre = SubmitField("Corriger cette adresse")


def valider_numero_telephone(form, field):
    """N'exige pas le format français à 10 chiffres (un numéro étranger
    reste valide), mais rejette les caractères non plausibles (lettres...)
    et les longueurs manifestement absurdes."""
    valeur = field.data or ""
    if not re.fullmatch(r"[0-9 .+()-]*", valeur):
        raise ValidationError(
            "Le numéro ne doit contenir que des chiffres et des séparateurs "
            "(espace, -, ., parenthèses)."
        )
    nb_chiffres = len(re.sub(r"\D", "", valeur))
    if not 6 <= nb_chiffres <= 15:
        raise ValidationError("Le numéro doit comporter entre 6 et 15 chiffres.")


class AjouterTelephoneForm(FlaskForm):
    numero = StringField(
        "Numéro de téléphone",
        validators=[DataRequired(message="Ce champ est requis."), valider_numero_telephone],
    )
    soumettre = SubmitField("Ajouter")


class CorrigerTelephoneForm(FlaskForm):
    numero = StringField(
        "Numéro de téléphone",
        validators=[DataRequired(message="Ce champ est requis."), valider_numero_telephone],
    )
    soumettre = SubmitField("Corriger")


class AjouterEmailForm(FlaskForm):
    adresse_email = StringField(
        "Adresse email", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Ajouter")


class CorrigerEmailForm(FlaskForm):
    adresse_email = StringField(
        "Adresse email", validators=[DataRequired(message="Ce champ est requis.")]
    )
    soumettre = SubmitField("Corriger")


class PartagerAdresseForm(FlaskForm):
    """Retrouver un contact déjà enregistré pour réutiliser une de ses
    adresses actives (couple partageant un domicile) plutôt que d'en
    ressaisir une nouvelle."""

    terme = StringField("Nom du contact qui a déjà cette adresse", validators=[Optional()])
    soumettre = SubmitField("Chercher")


# Les champs *_recherche + *_id (caché) ci-dessous suivent le même
# mécanisme que AjouterIntervenantForm côté dossiers : le texte libre
# alimente les suggestions de static/js/recherche_contact.js (mode
# "selectionner"), qui remplit le champ caché avec le contact_id choisi —
# aucune liste déroulante de toutes les personnes morales du cabinet.


class QualificationAvocatForm(FlaskForm):
    barreau_id = SelectField("Barreau", validators=[Optional()])
    cabinet_recherche = StringField("Cabinet (personne morale)", validators=[Optional()])
    cabinet_id = HiddenField(validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class QualificationNotaireForm(FlaskForm):
    office_recherche = StringField("Office notarial (personne morale)", validators=[Optional()])
    office_id = HiddenField(validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class QualificationCommissaireJusticeForm(FlaskForm):
    etude_recherche = StringField("Étude (personne morale)", validators=[Optional()])
    etude_id = HiddenField(validators=[Optional()])
    soumettre = SubmitField("Enregistrer")


class NouvelAvocatAnnuaireForm(FlaskForm):
    """Formulaire technique (un seul champ cache) qui porte le jeton CSRF
    pour la création d'un contact depuis un résultat de l'Annuaire national
    choisi en JavaScript — voir static/js/annuaire_avocats.js."""

    code_cnbf = HiddenField(validators=[DataRequired(message="Aucun résultat sélectionné.")])
    soumettre = SubmitField("Créer le contact")


class NouvelOfficeNotarialAnnuaireForm(FlaskForm):
    """Comme NouvelAvocatAnnuaireForm, mais sans identifiant à re-résoudre
    côté serveur : le répertoire local des notaires (voir
    app/services/annuaire_notaires.py) est un petit CSV statique, pas une
    ressource distante mise en cache — on transmet donc directement les
    champs du résultat choisi en JavaScript plutôt qu'un code à
    re-rechercher dans un cache."""

    nom = HiddenField(validators=[DataRequired(message="Aucun résultat sélectionné.")])
    siren = HiddenField(validators=[Optional()])
    numero_voie = HiddenField(validators=[Optional()])
    libelle_voie = HiddenField(validators=[Optional()])
    code_postal = HiddenField(validators=[Optional()])
    commune = HiddenField(validators=[Optional()])
    soumettre = SubmitField("Créer le contact")
