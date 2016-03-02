# Repository URL
REPO_URL = 'git@repo-url.git'
# Name of the main application (the settings should be accessed with [MAIN_APP].settings)
MAIN_APP = 'project'
# Folder name of the virtual environment
VIRTUALENV_FOLDER_NAME = 'env'
# Host used on local development machine
DEV_DOMAIN = 'localhost'
# Tuple of the manage.py commands you want executed everytime new source code is deployed
EXTRA_MANAGE_COMMANDS = (
    'collectstatic --noinput',  # collect the static files
    'migrate --noinput',        # migrate the database
)
