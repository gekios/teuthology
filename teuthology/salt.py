import logging
import re
import time

from os.path import isfile
from netifaces import ifaddresses

import teuthology
from .contextutil import safe_while
from .misc import sh
from .orchestra import run

log = logging.getLogger(__name__)


class UseSalt(object):

    def __init__(self, machine_type, os_type):
        self.machine_type = machine_type
        self.os_type = os_type

    def openstack(self):
        if self.machine_type == 'openstack':
            return True
        return False

    def suse(self):
        if self.os_type in ['opensuse', 'sle']:
            return True
        return False

    def use_salt(self):
        #if self.openstack() and self.suse():
        #    return True
        return False


class Salt(object):

    def __init__(self, ctx, config, **kwargs):
        self.ctx = ctx
        self.job_id = ctx.config.get('job_id')
        self.cluster = ctx.cluster
        self.remotes = ctx.cluster.remotes
        # FIXME: this seems fragile (ens3 hardcoded)
        self.teuthology_ip_address = ifaddresses('ens3')[2][0]['addr']
        self.minions = []
        ip_addr = self.teuthology_ip_address.split('.')
        self.teuthology_fqdn = "target{:03d}{:03d}{:03d}{:03d}.teuthology".format(
            int(ip_addr[0]),
            int(ip_addr[1]),
            int(ip_addr[2]),
            int(ip_addr[3]),
        )
        self.master_fqdn = kwargs.get('master_fqdn', self.teuthology_fqdn)

    def generate_minion_keys(self):
        for rem in self.remotes.iterkeys():
            minion_id=rem.shortname
            self.minions.append(minion_id)
            log.debug("minion: ID {sn}".format(
                sn=minion_id,
            ))
            # mode 777 is necessary to be able to generate keys reliably
            # we hit this before: https://github.com/saltstack/salt/issues/31565
            self.master_remote.run(args = ['mkdir', 'salt'],
                    check_status = False)
            self.master_remote.run(args = ['mkdir', '-m', '777', 'salt/minion-keys'],
                    check_status = False)
            self.master_remote.run(args = ['sudo', 'salt-key',
                '--gen-keys={sn}'.format(sn=minion_id),
                '--gen-keys-dir=salt/minion-keys/'])

    def cleanup_keys(self):
        for rem in self.remotes.iterkeys():
            minion_fqdn=rem.name.split('@')[1]
            minion_id=rem.shortname
            log.debug("Deleting minion key: FQDN {fqdn}, ID {sn}".format(
                fqdn=minion_fqdn,
                sn=minion_id,
            ))
            sh('sudo salt-key -y -d {sn}'.format(sn=minion_id))

    def preseed_minions(self):
        for rem in self.remotes.iterkeys():
            minion_fqdn=rem.name.split('@')[1]
            minion_id=rem.shortname
            self.master_remote.run(args = ['sudo', 'cp',
                'salt/minion-keys/{sn}.pub'.format(sn=minion_id),
                '/etc/salt/pki/master/minions/{sn}'.format(sn=minion_id)])
            self.master_remote.run(args = ['sudo', 'chown', 'ubuntu',
                "salt/minion-keys/{sn}.pem".format(sn=minion_id),
                "salt/minion-keys/{sn}.pub".format(sn=minion_id)])
            # copy the keys via the teuthology VM. The worker VMs can't ssh to
            # each other. scp -3 does a 3-point copy through the teuhology VM.
            sh('scp -3 {}:salt/minion-keys/{}.* {}:'.format(self.master_remote.name,
                minion_id, rem.name))
            r = rem.run(
                args=[
                    'sudo',
		    'sh',
                    '-c',
                    'echo "grains:" > /etc/salt/minion.d/job_id_grains.conf;\
                    echo "  job_id: {}" >> /etc/salt/minion.d/job_id_grains.conf'.format(self.job_id),
		    'sudo',
                    'chown',
                    'root',
                    '{}.pem'.format(minion_id),
                    '{}.pub'.format(minion_id),
                    run.Raw(';'),
                    'sudo',
                    'chmod',
                    '600',
                    '{}.pem'.format(minion_id),
                    '{}.pub'.format(minion_id),
                    run.Raw(';'),
                    'sudo',
                    'mv',
                    '{}.pem'.format(minion_id),
                    '/etc/salt/pki/minion/minion.pem',
                    run.Raw(';'),
                    'sudo',
                    'mv',
                    '{}.pub'.format(minion_id),
                    '/etc/salt/pki/minion/minion.pub',
                    run.Raw(';'),
                    'sudo',
                    'sh',
                    '-c',
                    'echo {} > /etc/salt/minion_id'.format(minion_id),
                    run.Raw(';'),
                    'sudo',
                    'cat',
                    '/etc/salt/minion_id',
                ],
            )

    def set_minion_master(self):
        """Points all minions to the master"""
        for rem in self.remotes.iterkeys():
            sed_cmd = 'echo master: {} > ' \
                      '/etc/salt/minion.d/master.conf'.format(
                self.master_fqdn
            )
            rem.run(args=[
                'sudo',
                'rm',
                '/etc/salt/pki/minion/minion_master.pub',
                run.Raw(';'),
                'sudo',
                'sh',
                '-c',
                sed_cmd,
            ])

    def init_minions(self):
        self.generate_minion_keys()
        self.preseed_minions()
        self.set_minion_master()

    def start_master(self):
        """Starts salt-master.service on given FQDN via SSH"""
        self.master_remote.run(args = ['sudo', 'systemctl', 'restart',
            'salt-master.service'])

    def stop_minions(self):
        """Stops salt-minion.service on all target VMs"""
        run.wait(
            self.cluster.run(
                args=['sudo', 'systemctl', 'stop', 'salt-minion.service'],
                wait=False,
            )
        )

    def start_minions(self):
        """Starts salt-minion.service on all target VMs"""
        run.wait(
            self.cluster.run(
                args=['sudo', 'systemctl', 'restart', 'salt-minion.service'],
                wait=False,
            )
        )

    def ping_minion(self, mid):
        """Pings a minion, raises exception if it doesn't respond"""
        self.__ping("sudo salt '{}' test.ping".format(mid), 1)

    def ping_minions(self):
        """Pings minions with this cluser's job_id, raises exception if they don't respond"""
        self.__ping("sudo salt -C 'G@job_id:{}' test.ping".format(self.job_id),
                len(self.remotes))

    def __ping(self, ping_cmd, expected):
        with safe_while(sleep=2, tries=10,
                action=ping_cmd) as proceed:
            while proceed():
                if self.master_fqdn == self.teuthology_fqdn:
                    res = sh(ping_cmd)
                    responded = len(re.findall('True', res))
                    log.debug("{} minion(s) responded".format(responded))
                    if(expected == responded):
                        return
                else:
                    # master is a remote
                    pass
