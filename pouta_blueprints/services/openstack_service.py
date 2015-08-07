import novaclient
from novaclient.v2 import client

import taskflow.engines
from taskflow.patterns import linear_flow as lf
from taskflow.patterns import graph_flow as gf
from taskflow import task

import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_openstack_nova_client():
    os_username = os.environ['OS_USERNAME']
    os_password = os.environ['OS_PASSWORD']
    os_tenant_name = os.environ['OS_TENANT_NAME']
    os_auth_url = os.environ['OS_AUTH_URL']

    return client.Client(os_username, os_password, os_tenant_name, os_auth_url, service_type="compute")


class GetImage(task.Task):
    def execute(self, image_name):
        logger.debug("getting image %s" % image_name)
        nc = get_openstack_nova_client()
        return nc.images.find(name=image_name).id


class GetFlavor(task.Task):
    def execute(self, flavor_name):
        logger.debug("getting flavor %s" % flavor_name)
        nc = get_openstack_nova_client()
        return nc.flavors.find(name=flavor_name).id


class CreateSecurityGroup(task.Task):
    def execute(self, display_name):
        logger.debug("create security group %s" % display_name)
        security_group_name = display_name
        nc = get_openstack_nova_client()
        try:
            self.secgroup = nc.security_groups.create(
                security_group_name,
                "Security group generated by Pouta Blueprints")
        except Exception as e:
            logger.error(e)
        return self.secgroup.id

    def revert(self, **kwargs):
        logger.debug("revert: delete security group")
        nc = get_openstack_nova_client()
        nc.security_groups.delete(self.secgroup.id)


class ProvisionInstance(task.Task):
    def execute(self, display_name, image, flavor, key_name, security_group):
        logger.debug("provisioning instance %s" % display_name)
        logger.debug("image=%s flavor=%s, key=%s, secgroup=%s" % (image, flavor, key_name, security_group))
        nc = get_openstack_nova_client()

        instance = nc.servers.create(
            display_name,
            image,
            flavor,
            key_name=key_name,
            security_groups=[security_group])

        self.instance_id = instance.id
        logger.debug("instance provisioning ok")
        return instance.id

    def revert(self, **kwargs):
        logger.debug("revert: deleting instance %s", kwargs)
        nc = get_openstack_nova_client()
        nc.servers.delete(self.instance_id)


class AllocateIPForInstance(task.Task):
    def execute(self, server_id):
        logger.debug("Allocate IP for server %s" % server_id)
        # Arbitrary time out due to
        # https://bugs.launchpad.net/nova/+bug/1249065
        import time
        time.sleep(5)
        nc = get_openstack_nova_client()
        ips = nc.floating_ips.findall(instance_id=None)
        server = nc.servers.get(server_id)
        allocated_from_pool = False
        if not ips:
            logger.debug("No allocated free IPs left, trying to allocate one\n")
            try:
                ip = nc.floating_ips.create(pool="public")
                allocated_from_pool = True
            except novaclient.exceptions.ClientException as e:
                logger.debug("Cannot allocate IP, quota exceeded?\n")
        else:
            ip = ips[0]
        try:
            server.add_floating_ip(ip)
        except Exception as e:
            logger.error(e)
        instance_data = {
            'ip': ip,
            'server_id': server.id,
            'allocated_from_pool': allocated_from_pool,
        }
        return instance_data


flow = lf.Flow('ProvisionInstance').add(
    gf.Flow('BootInstance').add(
        GetImage('get_image', provides='image'),
        GetFlavor('get_flavor', provides='flavor'),
        CreateSecurityGroup('create_security_group', provides='security_group'),
        ProvisionInstance('provision_instance', provides='server_id')
    ),
    AllocateIPForInstance('allocate_ip_for_instance', provides='ip'),
)


class OpenStackService(object):
    def provision_instance(self, display_name, image_name, flavor_name, key_name):
        try:
            return taskflow.engines.run(flow, engine='parallel', store=dict(
                image_name=image_name,
                flavor_name=flavor_name,
                display_name=display_name,
                key_name=key_name,
                ))
        except Exception as e:
            logger.error("Flow failed")
            logger.error(e)
            return {'error': 'flow failed'}

