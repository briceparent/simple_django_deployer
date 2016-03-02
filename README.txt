#################################################################################
Simple script to
- install all that's needed for Django to be deployed
- create a site to deploy some code on
- deploy code on it
- create superuser accounts

It saves all the configurations in json files in a data/ folder.
#################################################################################

Requirements :
* on local machine :
    - fabric and python 2.7
* on server :
    - Debian-based system (uses apt-get to install the packages)
    - Systemd (uses systemd to restart services) : Ubuntu 15.04+ work like a charm
    - Not sure if it works to deploy Python2.x Django projects
* inside the source code :
    - Django, gunicorn and psycopg2 should be in a requirements.txt file at the root of the project
    - The settings file should be as described in django_settings_contents.py
    - A settings.py file should be created. A pre-filled model can be found in settings.sample.py.

Caution :
- The settings found in deployer/settings.py are shared between all servers and sites, which means
 if you modify them while there already are some created servers or sites, they may not work anymore.

Todo :
- Check user's entries with regex for already registered domains or site_names
- Check that the requirements are fulfilled
- Write a summary to allow the user to validate before the "install" and the "create-site" commands.
- Check that the user doesn't already exist

Usage :
The project to deploy has some requirements (at least for now) :
- The source code should be a git repo.
- You should have a domain pointing to the server.
- The account used to deploy ("django" by default) the code should not exist
- You should have a root access to the server using an ssh key for both the "install" and "create-site"
commands. Once those actions have been processed, you may, for security, disallow root login as the
deployment connects through the created user's account.

Type the following for documentation :
* "python2 deploy.py --help" for general help
* "python2 deploy.py install --help" for help on installing a server
* "python2 deploy.py create-site --help" for help on creating a site to deploy to to
* "python2 deploy.py deploy --help" for help on deploying a tag to a site
* "python2 deploy.py createsuperuser --help" for help on creating a superuser on a site

What it does :
* install
    - installs the packages nginx git python3 python3-pip
    - creates the user and prepares the folders in his home
    - allows this user to launch passwordlessly the commands to relaunch gunicorn
* add-site
    - creates subfolders to install the project in
    - creates a virtual environment
    - prepares the site (nginx and gunicorn conf files)
    - clones the repository
    - copies the mail_settings.py file if it exists locally in the same folder as Django's settings.py file
* deploy
    - checks that the server type (production or staging) may accept the given tag
    - updates the source code from the repository
    - updates the project's settings (and creates random SECRET_KEY if there is none)
    - installs the pip packages
    - collects the static files, migrates the db and launches the extra manage.py commands (if any)
    - restarts gunicorn for these changes to be available
* createsuperuser
    - generates a random password
    - creates the superuser using Django's createsuperuser management command
    - displays the generated password
