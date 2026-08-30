from psycopg_pool import ConnectionPool

# Le pool est créé une seule fois au démarrage de l'application (voir
# create_app dans app/__init__.py) puis réutilisé pour toutes les requêtes.
# Chaque route emprunte une connexion via `with pool.connection() as conn:`,
# l'utilise, puis la rend automatiquement au pool en sortant du bloc `with`.
pool: ConnectionPool | None = None


def init_pool(conninfo: str) -> ConnectionPool:
    global pool
    pool = ConnectionPool(conninfo, min_size=1, max_size=5, open=True)
    return pool
