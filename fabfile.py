from fabric.api import local, task, env, run, sudo
from fabric.operations import open_shell
from fabric.utils import puts, indent
from fabric.context_managers import prefix, settings, cd
from fabric.contrib.console import confirm
from fabric import colors
from boto import ec2
from os import path
import time
import ConfigParser
import yaml

ec2_connection = ec2.get_region('us-west-2').connect()

env.security_group = 'wsgi_test' # wsgi_test
env.instance_type = 't1.micro'
env.keypair = 'wsgi_test'
env.user = 'app'
env.key_filename = path.join('keypairs', 'wsgi_test.pem')

@task
def app(name):
  env.name = name
  env.hosts = get_instance_hostnames(name)

@task
def launch(repo = 'https://github.com/mattupstate/ansible-tutorial.git', tags = 'setup,deploy'):
  with settings(warn_only = True):
    sync_repo(repo)
  components = parse_components(path.join('app', env.name))

  server_count = int(components['app']['servers'])
  instances = get_instances(env.name)
  if len(instances) < server_count:
    launch_instances(server_count - len(instances))

  time.sleep(5)
  puts('Waiting for instance to boot...')
  wait_for_instances(instances)
  update_hosts()
  archive()
  setup_instances(tags)

@task
def archive():
  commit = get_app_commit(env.name)
  with prefix('cd ./app/'):
    local('tar czf {0}_{1}.tar.gz {0}'.format(env.name, commit))

@task
def sync_repo(repo):
  repo_dir = 'app/%s' % env.name
  if path.exists(repo_dir):
    with prefix('cd ' + repo_dir):
      local('git pull')
  else:
    local('git clone %s %s' % (repo, repo_dir))

@task
def launch_instances(num = 1):
  puts('Launching %s new instance(s) (%s)' % (num, env.name))

  image = ec2_connection.get_image(env.ami_id)
  reservation = image.run(
    instance_type = env.instance_type,
    security_groups = [env.security_group],
    key_name = env.keypair,
    min_count = num,
    max_count = num
  )
  instances = reservation.instances
  ec2_connection.create_tags([i.id for i in instances], {'Name': env.name})

  for instance in instances:
    print instance.id
    print instance.dns_name

  return instances

@task
def update_hosts():
  puts('Updating hosts')

  hostnames = get_instance_hostnames(env.name)
  hosts = '[webservers]\n%s' % '\n'.join(hostnames)
  with open('app/%s/hosts' % env.name, 'w') as hosts_file:
    hosts_file.write(hosts)

@task
def setup_instances(tags = 'setup,deploy'):
  puts('Preparing instances')

  app_commit = get_app_commit(env.name)
  app_archive = '%s_%s.tar.gz' % (env.name, app_commit)
  app_components = path.join('../app', env.name, 'components.yaml')

  with prefix('. env/bin/activate'):
    local('ansible-playbook server/setup.yml -i {hosts} --private-key {key} --extra-vars "{vars}" --tags "{tags}"'.format(
      hosts = path.join('app', env.name, 'hosts'),
      key = 'keypairs/%s.pem' % env.keypair,
      vars = 'app_name=%s app_archive=%s app_components=%s app_commit=%s' % (env.name, app_archive, app_components, app_commit),
      tags = tags,
    ))

@task
def destroy_app():
  puts('Instances:')
  puts('- ' + '\n- '.join(get_instance_hostnames(env.name)))
  if not confirm('Are you sure you want to destroy all the above instances?'):
    return

  instance_ids = [i.id for i in get_instances(env.name)]
  ec2_connection.terminate_instances(instance_ids)

@task
def status():
  print '-----'
  for instance in get_instances(env.name):
    print('%s (%s) - %s' % (instance.id, instance.dns_name, instance.state))

@task
def shell():
  open_shell()

@task
def log(log = 'application.log'):
  run('tail -f log/%s' % log)

@task
def reboot():
  sudo('reboot')

def parse_components(project_folder):
  return yaml.load(open(path.join(project_folder, 'components.yaml')))

def get_app_commit(name):
  with prefix('cd app/%s/' % name):
    return local('git rev-parse HEAD', capture = True)

def get_instances(name):
  reservations = ec2_connection.get_all_instances(filters = {'tag-key': 'Name', 'tag-value': name})
  instances = [r.instances[0] for r in reservations if r.instances[0].state != 'terminated']
  return instances

def get_instance_hostnames(name):
  hostnames = [str(i.dns_name) for i in get_instances(name)]

  return hostnames

def wait_for_instances(instances):
  for instance in instances:
    while instance.update() != 'running':
      time.sleep(10)

  # wait another 10 seconds for good luck
  #time.sleep(60)
