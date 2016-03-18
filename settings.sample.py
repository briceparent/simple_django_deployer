# Repository URL
REPO_URL = 'git@repo-url.git'
# Name of the main application (the settings should be accessed with [MAIN_APP].settings)
MAIN_APP = 'project'
# Folder name of the virtual environment
VIRTUALENV_FOLDER_NAME = 'env'
# Host used on local development machine
DEV_DOMAIN = 'localhost'
# Tuples of the manage.py commands you want executed everytime new source code is deployed
EXTRA_MANAGE_COMMANDS_START = (
    'backup',)  # We always create a backup right before an update of the source code
EXTRA_MANAGE_COMMANDS_END = (
    'collectstatic --noinput',  # We collect the static files
    'migrate --noinput',  # We migrate the database
    'clear_cache',)  # We empty the cache, as it's a good idea to recalculate everything now

