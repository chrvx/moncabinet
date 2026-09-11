import os


class Config:
    """Configuration de l'application.

    Toutes les valeurs sensibles (mot de passe, clé secrète) sont lues depuis
    les variables d'environnement, jamais écrites en dur dans le code. Les
    valeurs par défaut ci-dessous ne servent qu'au développement local.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "cle-de-developpement-a-changer")

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "moncabinet")
    DB_USER = os.environ.get("DB_USER", "moncabinet_app")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")

    # Synchronisation IMAP (app/services/messagerie.py) : boîte partagée du
    # cabinet, lue en lecture seule. IMAP_PASSWORD doit être un mot de passe
    # "appareil" dédié à l'application (révocable indépendamment des boîtes
    # Thunderbird), jamais le mot de passe principal du compte — voir
    # docs/phase-documents-correspondance.md §6.
    IMAP_HOST = os.environ.get("IMAP_HOST", "mail.infomaniak.com")
    IMAP_PORT = os.environ.get("IMAP_PORT", "993")
    IMAP_USER = os.environ.get("IMAP_USER", "")
    IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", "")
    IMAP_PREFIXE_DOSSIERS = os.environ.get("IMAP_PREFIXE_DOSSIERS", "dossier")
    # Liste séparée par virgules, pour déduire le sens (recu/envoye) d'un
    # message importé : expéditeur dans cette liste -> envoyé par le cabinet.
    ADRESSES_CABINET = os.environ.get("ADRESSES_CABINET", "")

    @property
    def DB_CONNINFO(self):
        """Chaîne de connexion au format attendu par psycopg3."""
        return (
            f"host={self.DB_HOST} port={self.DB_PORT} "
            f"dbname={self.DB_NAME} user={self.DB_USER} password={self.DB_PASSWORD}"
        )
