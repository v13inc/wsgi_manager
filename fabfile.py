from fabric.api import local, task, env
from fabric.context_managers import prefix
from boto import ec2

ec2_connection = ec2.get_region('us-west-2').connect()

env.ami_id = 'ami-d8a633e8' # debian testing
env.security_group = 'wsgi_test' # wsgi_test
env.instance_type = 'm1.small'
env.keypair = 'wsgi_test'

@task
def new_app(name = 'test'):
  image = ec2_connection.get_image(env.ami_id)
  reservation = image.run(
    instance_type = env.instance_type,
    security_groups = [env.security_group],
    key_name = env.keypair
  )
  instance = reservation.instances[0]
  ec2_connection.create_tags([instance.id], {'Name': name})

@task
def setup_servers():
  with prefix('. env/bin/activate'):
    local('ansible-playbook setup.yml -i hosts --private-key=keypairs/%s.pem' % env.keypair)
