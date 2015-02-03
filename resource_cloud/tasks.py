import base64
import os
import random
import time
import subprocess
import requests
from celery import Celery
from celery.utils.log import get_task_logger
import jinja2
from flask import render_template
from flask.ext.mail import Message
import stat
from resource_cloud.app import get_app
# from resource_cloud.config import BaseConfig as config
from resource_cloud.config import DevConfig as config

logger = get_task_logger(__name__)
app = Celery('tasks', broker=config.MESSAGE_QUEUE_URI, backend=config.MESSAGE_QUEUE_URI)
app.conf.CELERY_TASK_SERIALIZER = 'json'

flask_app = get_app()


@app.task(name="resource_cloud.tasks.send_mails")
def send_mails(users):
    with flask_app.test_request_context():
        for email, token in users:
            msg = Message('Resource-cloud activation')
            msg.recipients = [email]
            msg.sender = 'resource-cloud@csc.fi'
            activation_url = '%s/#/activate/%s' % (flask_app.config['BASE_URL'],
                                                   token)
            msg.html = render_template('invitation.html',
                                       activation_link=activation_url)
            msg.body = render_template('invitation.txt',
                                       activation_link=activation_url)
            mail = flask_app.extensions.get('mail')
            if not mail:
                raise RuntimeError("mail extension is not configured")
            if flask_app.config.get('MAIL_SUPPRESS_SEND'):
                logger.info(msg.body)
            mail.send(msg)


@app.task(name="resource_cloud.tasks.run_provisioning")
def run_provisioning(token, resource_id):
    logger.info('provisioning triggered for %s' % resource_id)

    run_pvc_provisioning(token, resource_id)

    logger.info('provisioning done, notifying server')
    resp = update_resource_state(token, resource_id, 'running')

    if resp.status_code == 200:
        return 'ok'

    return 'error: %s %s' % (resp.status_code, resp.reason)


@app.task(name="resource_cloud.tasks.run_deprovisioning")
def run_deprovisioning(token, resource_id):
    logger.info('deprovisioning triggered for %s' % resource_id)

    run_pvc_deprovisioning(token, resource_id)

    logger.info('deprovisioning done, notifying server')
    resp = update_resource_state(token, resource_id, 'deleted')

    if resp.status_code == 200:
        return 'ok'

    return 'error: %s %s' % (resp.status_code, resp.reason)


def update_resource_state(token, resource_id, state):
    payload = {'state': state}
    auth = base64.encodestring('%s:%s' % (token, '')).replace('\n', '')
    headers = {'Content-type': 'application/x-www-form-urlencoded',
               'Accept': 'text/plain',
               'Authorization': 'Basic %s' % auth}
    url = 'https://localhost/api/v1/provisioned_resources/%s' % resource_id
    resp = requests.patch(url, data=payload, headers=headers,
                          verify=config.SSL_VERIFY)
    logger.info('got response %s %s' % (resp.status_code, resp.reason))
    return resp


def get_resource_data(token, resource_id):
    auth = base64.encodestring('%s:%s' % (token, '')).replace('\n', '')
    headers = {'Accept': 'text/plain',
               'Authorization': 'Basic %s' % auth}
    url = 'https://localhost/api/v1/provisioned_resources/%s' % resource_id
    resp = requests.get(url, headers=headers, verify=config.SSL_VERIFY)
    logger.info('got response %s %s' % (resp.status_code, resp.reason))
    return resp


def run_pvc_provisioning(token, resource_id):
    resp = get_resource_data(token, resource_id)
    if resp.status_code != 200:
        raise RuntimeError('Cannot fetch data for resource %s, %s' % (resource_id, resp.reason))
    r_data = resp.json()
    c_name = r_data['name']

    res_dir = '%s/%s' % (config.PVC_CLUSTER_DATA_DIR, c_name)

    # will fail if there is already a directory for this resource
    os.makedirs(res_dir)

    # generate pvc config for this cluster
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    j2env = jinja2.Environment(loader=jinja2.FileSystemLoader(THIS_DIR))
    tc = j2env.get_template('templates/pvc-cluster.yml.jinja2')

    conf = tc.render(cluster_name='rc-%s' % c_name, security_key='rc-%s' % c_name, frontend_flavor='mini',
                     public_ip='86.50.169.98',
                     node_flavor='mini', )

    with open('%s/cluster.yml' % res_dir, 'w') as cf:
        cf.write(conf)
        cf.write('\n')

    if not config.FAKE_PROVISIONING:
        # generate keypair for this cluster
        key_file = '%s/key.priv' % res_dir
        if not os.path.isfile(key_file):
            with open(key_file, 'w') as keyfile:
                args = ['nova', 'keypair-add', 'rc-%s' % c_name]
                p = subprocess.Popen(args, cwd=res_dir, stdout=keyfile)
            os.chmod(key_file, stat.S_IRUSR)

        # run provisioning
        args = ['/webapps/resource_cloud/venv/bin/python', '/opt/pvc/python/poutacluster.py', 'up', '2']
        with open('%s/pvc_stdout.log' % res_dir, 'a') as stdout, open('%s/pvc_stderr.log' % res_dir, 'a') as stderr:
            logger.info('spawning "%s"' % ' '.join(args))
            p = subprocess.Popen(args, cwd=res_dir, stdout=stdout, stderr=stderr)
            logger.info('spawning done, waiting')
            p.wait()
    else:
        logger.info('faking provisioning, sleeping for a while')
        time.sleep(random.randint(5, 15))


def run_pvc_deprovisioning(token, resource_id):
    resp = get_resource_data(token, resource_id)
    if resp.status_code != 200:
        raise RuntimeError('Cannot fetch data for resource %s, %s' % (resource_id, resp.reason))
    r_data = resp.json()
    c_name = r_data['name']

    res_dir = '%s/%s' % (config.PVC_CLUSTER_DATA_DIR, c_name)

    if not config.FAKE_PROVISIONING:
        # run deprovisioning
        args = ['/webapps/resource_cloud/venv/bin/python', '/opt/pvc/python/poutacluster.py', 'down']
        with open('%s/pvc_stdout.log' % res_dir, 'a') as stdout, open('%s/pvc_stderr.log' % res_dir, 'a') as stderr:
            logger.info('spawning "%s"' % ' '.join(args))
            p = subprocess.Popen(args, cwd=res_dir, stdout=stdout, stderr=stderr)
            logger.info('spawning done, waiting')
            p.wait()
    else:
        logger.info('faking provisioning, sleeping for a while')
        time.sleep(random.randint(5, 15))

    # use resource id as a part of the name to make tombstones always unique
    os.rename(res_dir, '%s.deleted.%s' % (res_dir, resource_id))

