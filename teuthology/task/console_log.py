import logging
import os

from teuthology.orchestra.cluster import Cluster

from . import Task

log = logging.getLogger(__name__)


class ConsoleLog(Task):
    enabled = True
    name = 'console_log'

    def __init__(self, ctx=None, config=None):
        super(ConsoleLog, self).__init__(ctx, config)
        if self.config.get('enabled') is False:
            self.enabled = False
        if not getattr(self.ctx, 'archive', None):
            self.enabled = False

    def filter_hosts(self):
        super(ConsoleLog, self).filter_hosts()
        if not hasattr(self.ctx, 'cluster'):
            return
        new_cluster = Cluster()
        for (remote, roles) in self.cluster.remotes.iteritems():
            if not hasattr(remote.console, 'spawn_sol_log'):
                log.debug("%s does not support IPMI; excluding",
                          remote.shortname)
            elif not remote.console.has_ipmi_credentials:
                log.debug("IPMI credentials not found for %s; excluding",
                          remote.shortname)
            else:
                new_cluster.add(remote, roles)
        self.cluster = new_cluster
        return self.cluster

    def setup(self):
        if not self.enabled:
            return
        super(ConsoleLog, self).setup()
        self.processes = list()
        self.setup_archive()

    def setup_archive(self):
        self.archive_dir = os.path.join(
            self.ctx.archive,
            'console_logs',
        )
        os.makedirs(self.archive_dir)

    def begin(self):
        if not self.enabled:
            return
        super(ConsoleLog, self).begin()
        self.start_logging()

    def start_logging(self):
        for remote in self.cluster.remotes.keys():
            log_path = os.path.join(
                self.archive_dir,
                "%s.log" % remote.shortname,
            )
            proc = remote.console.spawn_sol_log(log_path)
            self.processes.append(proc)

    def end(self):
        if not self.enabled:
            return
        super(ConsoleLog, self).end()
        self.stop_logging()

    def stop_logging(self, force=False):
        for proc in self.processes:
            if proc.poll() is not None:
                continue
            if force:
                proc.kill()
            else:
                proc.terminate()

    def teardown(self):
        if not self.enabled:
            return
        self.stop_logging(force=True)
        super(ConsoleLog, self).teardown()


task = ConsoleLog
