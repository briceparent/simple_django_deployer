import os
import random
import string
import datetime

from fabric.contrib.files import append, exists, sed
from fabric.api import env, local, run, put, sudo

try:
    from settings import MAIN_APP, REPO_URL, VIRTUALENV_FOLDER_NAME, DEV_DOMAIN, EXTRA_MANAGE_COMMANDS
except ImportError as e:
    print("There is no settings.py file. You should create one, based from settings.sample.py.")
    raise ImportError(e)


env.forward_agent = True


def install_server(user="django"):
    env.user = "root"
    # Installation
    run('apt-get update && apt-get install -y nginx git python3 python3-pip libpq-dev postgresql postgresql-contrib')
    # Removing default nginx site
    run('rm /etc/nginx/sites-enabled/default')
    # Virtualenv
    run('pip3 install virtualenv')
    # Create user and get ssh access to it
    run('useradd {} -s /bin/bash -m'.format(user))
    run('cp -R /root/.ssh /home/{user}/.ssh && chown -R {user}: /home/{user}'.format(user=user))
    # Folder structure
    sudo('mkdir -p /home/{user}/sites'.format(user=user), user=user)
    sudo('mkdir -p /home/{user}/proc'.format(user=user), user=user)
    # Nginx custom http config
    put('templates/nginx_long_domain_names.conf', '/etc/nginx/conf.d/long_domain.conf')
    # Adding user to sudoers without password for the reload folder
    run('mkdir -p /root/gunicorn_reloader_scripts/')
    line = '{user} ALL=(root) NOPASSWD: /root/gunicorn_reloader_scripts/'.format(user=user)
    run('echo "{line}" > /etc/sudoers.d/gunicorn_reloader_scripts'.format(line=line))


def _sed_all(file, data):
    for replace, replacement in data:
        sed(file, replace, str(replacement))


def add_site(domain="www.*", port=80, site_name="production", user="django"):
    sed_data = (('\{SITE_PORT\}', port),
                ('\{SERVER_NAME\}', domain),
                ('\{USER\}', user),
                ('\{SITE_NAME\}', site_name),
                ('\{MAIN_APP\}', MAIN_APP))

    env.user = "root"
    repository = REPO_URL

    # Nginx config
    nginx_file = '{}.conf'.format(site_name)
    nginx_settings = '/etc/nginx/sites-available/' + nginx_file
    put('templates/nginx.conf', nginx_settings)
    _sed_all(nginx_settings, sed_data)
    run('ln -s /etc/nginx/sites-available/{file} /etc/nginx/sites-enabled/{file}'.format(file=nginx_file), quiet=True)
    run('service nginx restart')

    # Gunicorn
    gunicorn_file = 'gunicorn_{}'.format(site_name)
    gunicorn_settings = '/etc/systemd/system/{}.service'.format(gunicorn_file)
    put('templates/gunicorn-systemd.conf', gunicorn_settings)
    _sed_all(gunicorn_settings, sed_data)

    # Gunicorn reloader script
    gunicorn_reloader_settings = '/root/gunicorn_reloader_scripts/' + site_name + ".sh"
    put('templates/gunicorn_reloader.sh', gunicorn_reloader_settings)
    sed_data = sed_data + (('\{GUNICORN_FILE\}', gunicorn_file),)
    _sed_all(gunicorn_reloader_settings, sed_data)
    run('chmod +x ' + gunicorn_reloader_settings)

    # Creating the user and the database
    env.user = "root"
    db_password = _random_string(12)
    db_user = "django" + _random_string(6)
    db_name = site_name
    queries = (
        'sudo -u postgres psql -c "CREATE USER {DB_USER} WITH PASSWORD \'{DB_PASSWORD}\';"',
        'sudo -u postgres psql -c "CREATE DATABASE {DATABASE};"',
        'sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE {DATABASE} TO {DB_USER};"')
    for query in queries:
        run(query.format(DB_PASSWORD=db_password, DB_USER=db_user, DATABASE=db_name))

    # Folders
    env.user = user
    project_folder = '~/sites/' + site_name
    run('mkdir -p {folder}/source {folder}/database {folder}/static'.format(folder=project_folder))  # Database

    # Repository initialisation
    run('git clone {repo} {folder}/source'.format(repo=repository, folder=project_folder))  # local db

    # db conf
    db_settings_file = '{folder}/source/{app}/db.py'.format(folder=project_folder, app=MAIN_APP)
    put('templates/db.template.py', db_settings_file)
    db_sed_data = (('\{DB_PASSWORD\}', db_password),
                   ('\{DB_USER\}', db_user),
                   ('\{DATABASE\}', db_name)) + sed_data
    _sed_all(db_settings_file, db_sed_data)

    # Virtualenv
    run('virtualenv --python=python3 {folder}/{env}'.format(folder=project_folder, env=VIRTUALENV_FOLDER_NAME))

    # Copying the local mail_settings file if there is one
    local_mail_settings_file = '../{}/mail_settings.py'.format(MAIN_APP)
    if os.path.exists(local_mail_settings_file):
        put(local_mail_settings_file, '{folder}/source/{app}/mail_settings.py'.format(
            folder=project_folder, app=MAIN_APP))


# Here, we deploy the given tag on the given server_type
def deploy_tag(tag="tag", user="Django", site_name="", domain="", server_type=True, is_production=True):
    env.user = user
    print("Deploying tag {} to {} (production? {})".format(tag, env.host, is_production))
    site_folder = '/home/%s/sites/%s' % (user, site_name)
    source_folder = site_folder + '/source'
    _update_source_code(source_folder, tag, is_production)
    _update_settings(source_folder, domain, is_production)
    _update_virtualenv_requirements(source_folder)
    _collect_static_files(source_folder)
    _migrate_database(source_folder)
    _restart_gunicorn(site_name)
    _launch_extra_manage_commands(source_folder)


# Here, we create a superuser on the given server_type
def create_super_user(django_user="Django", username="admin", email=None, site_name=""):
    env.user = django_user
    site_folder = '/home/%s/sites/%s' % (django_user, site_name)
    source_folder = site_folder + '/source'
    password = _random_string(16)
    script = "from django.contrib.auth.models import User; " \
             "User.objects.create_superuser('{username}', '{email}', '{password}')".format(
                 username=username, email=email, password=password)
    run("cd {folder} && echo \"{script}\" | ../{env}/bin/python3 manage.py shell".format(
        folder=source_folder, script=script, env=VIRTUALENV_FOLDER_NAME))
    print("Password for the new user : " + password)


def _update_source_code(source_folder, deploy_tag, is_production_server):
    local("git push && git push --tags")
    run('cd %s && git fetch' % (source_folder,))
    run('cd %s && git reset --hard %s' % (source_folder, deploy_tag))

    if is_production_server:
        # We add a tag to mark the deployment
        new_tag = 'deployed-{}'.format(datetime.datetime.today().strftime('%Y-%m-%d_%H-%M'))
        deploy_message = 'Deployed automatically using Fabric, created tag {}'.format(new_tag)
        local("cd .. && git tag -a '{}' -m '{}'".format(new_tag, deploy_message))
        local("cd .. && git push --tags")


def _update_settings(source_folder, domain, is_production_server):
    # We get the domain's IP for the ALLOWED_HOSTS setting (last line of dig +short)
    ip = local('dig +short {} | tail -n1;'.format(domain), capture=True)

    settings_path = '{}/{}/settings.py'.format(source_folder, MAIN_APP)
    sed(settings_path, "DEBUG = True", "DEBUG = False")
    sed(settings_path, 'ALLOWED_HOSTS = [DOMAIN, "127.0.0.1"]', 'ALLOWED_HOSTS = [DOMAIN, "{}"]'.format(ip))
    sed(settings_path, 'DOMAIN = "{}"'.format(DEV_DOMAIN), 'DOMAIN = "%s"' % (domain,))
    if not is_production_server:
        sed(settings_path, 'SERVER_TYPE = SERVER_TYPE_DEVELOPMENT', 'SERVER_TYPE = SERVER_TYPE_STAGING')
    else:
        sed(settings_path, 'SERVER_TYPE = SERVER_TYPE_DEVELOPMENT', 'SERVER_TYPE = SERVER_TYPE_PRODUCTION')

    secret_key_file = '{}/{}/secret_key.py'.format(source_folder, MAIN_APP)
    if not exists(secret_key_file):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        key = ''.join(random.SystemRandom().choice(chars) for _ in range(50))
        append(secret_key_file, "SECRET_KEY = '%s'" % (key,))

    append(settings_path, '\nfrom .secret_key import SECRET_KEY')


def _update_virtualenv_requirements(source_folder):
    virtualenv_folder = '{}/../{}'.format(source_folder, VIRTUALENV_FOLDER_NAME)
    run('%s/bin/pip install -r %s/requirements.txt' % (
            virtualenv_folder, source_folder
    ))


def _get_manage_dot_py_command(source_folder):
    return 'cd {} && ../{}/bin/python3 manage.py'.format(source_folder, VIRTUALENV_FOLDER_NAME)


def _collect_static_files(source_folder):
    run(_get_manage_dot_py_command(source_folder) + ' collectstatic --noinput')


def _migrate_database(source_folder):
    run(_get_manage_dot_py_command(source_folder) + ' migrate --noinput')


def _launch_extra_manage_commands(source_folder):
    for command in EXTRA_MANAGE_COMMANDS:
        run(_get_manage_dot_py_command(source_folder) + ' ' + command)


def _restart_gunicorn(server_type_name):
    # The create-site command should have created a no-password executing right for this action
    gunicorn_reloader_settings = '/root/gunicorn_reloader_scripts/' + server_type_name + ".sh"
    run("sudo {}".format(gunicorn_reloader_settings))


def _random_string(size=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))
