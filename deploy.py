import argparse
import json
import os
import sys

if sys.version_info[0] > 2:
    raise Exception("Fabric may only be used with Python 2, sorry !")

from fabric.tasks import execute

from fabfile import install_server, add_site, create_super_user, deploy_tag


base_dir = os.path.dirname(os.path.abspath(__file__)) + "/"
data_folder = base_dir + "data/"
if not os.path.isdir(data_folder):
    os.mkdir(data_folder)


def server_exists(file):
    return os.path.exists(base_dir + 'data/server_{}.json'.format(file))


def site_exists(file):
    return os.path.exists(base_dir + 'data/site_{}.json'.format(file))


def read_json(file):
    with open(base_dir + 'data/{}.json'.format(file)) as data_file:
        return json.load(data_file)


def write_json(file, data):
    with open(base_dir + 'data/{}.json'.format(file), 'w') as outfile:
        json.dump(data, outfile)


def install(parser):
    print("We install a server")

    # data to store
    data = {
        'id': len(get_available_servers_list()) + 1,
        'host': parser.host,
        'user': parser.user}

    execute(install_server, user=parser.user, hosts=[parser.host])

    write_json('server_' + str(data['id']), data)
    print("Server installation ended")


def get_available_servers_list():
    servers = []
    for file in os.listdir(data_folder):
        if file.startswith("server_") and file.endswith(".json"):
            servers.append(get_server_data(server_file=data_folder+str(file)))

    return servers


def get_server_data(server_number=None, server_file=None):
    if server_number:
        server_file = data_folder + "server_" + str(server_number) + ".json"

    with open(server_file, 'r') as file:
        return json.load(file)


def get_site_data(site_number=None, site_file=None):
    if site_number:
        site_file = data_folder + "site_" + str(site_number) + ".json"

    with open(site_file, 'r') as file:
        return json.load(file)


def get_all_sites_list():
    sites = []
    for file_name in os.listdir(data_folder):
        if file_name.startswith("site_") and file_name.endswith(".json"):
            sites.append(str(file_name))

    return sites


def get_available_sites_list(server):
    sites = []
    for file_name in get_all_sites_list():
        if file_name.startswith("site_") and file_name.endswith(".json"):
            data = get_site_data(site_file=data_folder+file_name)
            if data['server'] == server:
                sites.append(data_folder + str(file_name))

    return sites


def print_available_servers_list():
    servers = get_available_servers_list()
    if not servers:
        print("There are no servers configured. You can configure one using the 'install' subcommand.")

    for server in servers:
        print(str(server['id']) + ': ' + server['user'] + "@" + server['host'])


def print_available_sites_list():
    servers = get_available_servers_list()
    if not servers:
        print("There are no servers configured. You can configure one using the 'install' subcommand.")

    sites_found = 0
    for server in servers:
        sites = get_available_sites_list(server=server['id'])
        for site in sites:
            sites_found += 1
            site_data = get_site_data(site_file=site)
            catching = "(catching " + site_data['domain'] + ":" + str(site_data['port']) + ")"
            server_data = server['user'] + "@" + server['host']
            print(str(site_data['id']) + " : " + site_data['site_name'] + " on " + server_data + " " + catching)

    if not sites_found:
        print("There are no sites configured. You can configure one using the 'create_site' subcommand.")


def create_site(parser):
    print("We create a site")
    server = parser.server

    if not server:
        print('You should select a site (ex " --server 3") to deploy to. Here are the available sites :')
        print_available_servers_list()
        return

    server_data = get_server_data(server)
    print("On server {}".format(str(server_data['id']) + ': ' + server_data['user'] + "@" + server_data['host']))
    try:
        server_data = get_server_data(server_number=server)
    except IOError:
        print("The server does not exist ! Select a server from the list.")
        print_available_servers_list()
        return

    if not parser.domain:
        print("You should give the domain name to deploy (ex : '--domain www.mydomain.com').")
        return

    if not parser.sitename:
        print("You should give a unique name for this site (ex : '--sitename production').")
        return

    if '_' in parser.domain:
        print("The domain can't contain underscores.")
        return

    # Data to store
    data = {
        'id': len(get_all_sites_list()) + 1,
        'server': server_data['id'],
        'is_production': parser.production,
        'site_name': parser.sitename,
        'domain': parser.domain,
        'port': parser.port}

    execute(
        add_site, hosts=[server_data['host']],
        user=server_data['user'], site_name=data['site_name'], domain=data['domain'], port=data['port'])

    write_json('site_' + str(data['id']), data)
    print("Site installation ended")


def print_tags_list():
    command = "git for-each-ref --format='%(*committerdate:raw)%(committerdate:raw) %(refname) %(*objectname) %(objectname)' refs/tags | sort -n | awk '{ print $3; }'"
    p = os.popen(command, "r")
    tags = []
    while 1:
        line = p.readline()
        if not line:
            break

        on_branch = 'git branch --contains "{}" | grep "*"'.format(line[10:-1])
        p2 = os.popen(on_branch, "r")
        line2 = p2.readline()
        if line2:
            tags.append(line[10:-1])

    for i in range(len(tags) - 10, len(tags)):
        try:
            print(tags[i])
        except IndexError:
            pass


def get_git_branch():
    command = 'git branch | grep "*"'
    p = os.popen(command, "r")
    return p.readline()[:-1][2:]


def deploy(parser):
    print("Deployment of source code")

    if not parser.site:
        print('You should select a site to deploy to (ex: "--site 1"). Here are the available sites :')
        print_available_sites_list()
        return

    site_data = get_site_data(parser.site)
    server = get_server_data(site_data['server'])
    catching = "(catching " + site_data['domain'] + ":" + str(site_data['port']) + ")"
    server_data = server['user'] + "@" + server['host']
    site_description = str(site_data['id']) + " : " + site_data['site_name'] + " on " + server_data + " " + catching
    print("Site to deploy to : {}".format(site_description))
    if not parser.tag:
        print('You should select a tag deploy (ex: "--tag Feature-new-design"). Here are the available tags for active branch :')
        print_tags_list()
        return

    tag = parser.tag
    site = get_site_data(parser.site)
    server = get_server_data(site['server'])
    if site['is_production']:
        if not tag.lower().startswith("release-") and not tag.lower().startswith("hotfix-"):
            print("Production sites may only be deployed with Release-* or Hotfix-* tags")
            return

        branch = get_git_branch()
        if branch != "master":
            print("Production sites may only be deployed with tags on master branch (and not {})".format(branch))
            return

    print("Tag to deploy : {}".format(parser.tag))
    execute(deploy_tag, user=server['user'], site_name=site['site_name'], is_production=site['is_production'],
            domain=site['domain'], tag=tag, hosts=[server['host']])
    print("Tag {} successfully deployed to {}:{}.".format(tag, site_data['domain'], site_data['port']))


def createsuperuser(parser):
    print("Creation of a super user")

    if not parser.site:
        print('You should select a site to create the superuser to (ex: "--site 1"). Here are the available sites :')
        print_available_sites_list()
        return

    site = get_site_data(parser.site)
    server = get_server_data(site['server'])
    execute(create_super_user, django_user=server['user'], site_name=site['site_name'],
            username=parser.username, email=parser.email, hosts=[server['host']])
    print("Superuser creation ended")


# Comand line arguments parsing
parser = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    description="""Installs server, configures sites and deploys source code.
For details on how to use the subcommands, type :
    * install -h (installation of a new server)
    * create_site -h (creation of a new site on an already installed server)
    * deploy -h (deployment of a tag on an already created site)
    * createsuperuser -h (creation of a superuser to access Django's admin)
""")

install_parser = argparse.ArgumentParser(add_help=False)
install_parser.add_argument('--host', required=True, help="""
The server to be installed (ex : www.domain.com).

Pre-requisite : The server should be accessible through SSH using both root@domain.com and
    [user]@domain.com, so the user [user] must exist and be accessible using a local SSH key.

The root account will only be used for the installation and for future site creations on this
server. The other account will be used for every deployment.
""")
install_parser.add_argument('--user', default="django", help="""
The system user for whom to make the installation (doesnt require special privileges, just a home folder).
Defaults to "django".
""")

create_parser = argparse.ArgumentParser(add_help=False)
group = create_parser.add_mutually_exclusive_group()
group.add_argument('--staging', help='Is this a staging/testing server ? (default)', action='store_true')
group.add_argument('--production', help='Is this a production server ?', action='store_true')
create_parser.add_argument('--server', type=int, help='The id of the server on which to create the site')
create_parser.add_argument('--domain', required=True, help='The domain of the site')
create_parser.add_argument('--port', default=80, type=int, help='The port to listen to (defaults to 80)')
create_parser.add_argument('--sitename', required=True, help='The name of the site (will be used for deployments)')

is_default_server = False

deploy_parser = argparse.ArgumentParser(add_help=False)
deploy_parser.add_argument(
    '--site', default=0, type=int,
    help='The id of the site on which to install the code. Leave empty to get a liste of available sites.')
deploy_parser.add_argument(
    '--tag', default=0,
    help='The tag to deploy on the installation. Leave empty to get a list of the last available tags on active branch.')

superuser_parser = argparse.ArgumentParser(add_help=False)
superuser_parser.add_argument(
    '--site', default=0, type=int,
    help='The id of the site on which to create the user the code. Leave empty to get a liste of available sites.')
superuser_parser.add_argument('--username', required=True, help='The username of the super user to create')
superuser_parser.add_argument(
    '--email',
    help='The email of the super user to create. Will be needed if you need to reset your password')

sp = parser.add_subparsers()
sp.required = True
sp_start = sp.add_parser('install', parents=[install_parser], description='Installs the server')
sp_start.set_defaults(func=install)
sp_stop = sp.add_parser('create-site', parents=[create_parser], description='Creates a site on an installed server')
sp_stop.set_defaults(func=create_site)
sp_restart = sp.add_parser('deploy', parents=[deploy_parser], description='Deploys a tag on an site')
sp_restart.set_defaults(func=deploy)
sp_restart = sp.add_parser('createsuperuser', parents=[superuser_parser],
                           description='Creates a superuser account with a randomly generated password')
sp_restart.set_defaults(func=createsuperuser)

args = parser.parse_args()
args.func(args)
