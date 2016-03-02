# The settings module should at least contain the following :

# You can use DEBUG = True, as it will automatically be changed to false during deployment

# To allow the website
ALLOWED_HOSTS = [DOMAIN, "127.0.0.1"]

# To use Postgres in production and staging, while still using sqlite during dev
try:
    from .db import DATABASES
except ImportError:
    print("Caution : Django is using an sqlite database instead of a PostgreSQL one. "
          "This might perform poorly when data increases.")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, '../database/db.sqlite3'),
        },
    }

# To prevent errors, you should define STATIC_URL, MEDIA_ROOT and MEDIA_URL

