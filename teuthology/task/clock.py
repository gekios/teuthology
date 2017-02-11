"""
Clock synchronizer
"""
import logging
import contextlib
import os

from ..orchestra import run

log = logging.getLogger(__name__)

@contextlib.contextmanager
def task(ctx, config):
    """
    Sync or skew clock

    This will initially sync the clocks.  Eventually it should let us also
    skew by some number of seconds.

    example:

    tasks:
    - clock:
    - ceph:
    - interactive:

    to sync.

    :param ctx: Context
    :param config: Configuration
    """

    log.info('Syncing clocks and checking initial clock skew...')
    for rem in ctx.cluster.remotes.iterkeys():
        rem.run(
            args = [
                'sudo', 'service', 'ntp', 'stop', run.Raw('||'),
                'sudo', 'systemctl', 'stop', 'ntp.service'
            ]
        )
        rem.run(
            args = [
                'sudo', 'ntpd', '-gq',
            ]
        )
        rem.run(
            args = [
                'sudo', 'service', 'ntp', 'start', run.Raw('||'),
                'sudo', 'systemctl', 'start', 'ntp.service'
            ]
        )
        rem.run(
            args = [
                'PATH=/usr/bin:/usr/sbin', 'ntpq', '-p',
            ],
        )

    try:
        yield

    finally:
        log.info('Checking final clock skew...')
        for rem in ctx.cluster.remotes.iterkeys():
            rem.run(
                args=[
                    'PATH=/usr/bin:/usr/sbin', 'ntpq', '-p',
                    ],
                )


@contextlib.contextmanager
def check(ctx, config):
    """
    Run ntpq at the start and the end of the task.

    :param ctx: Context
    :param config: Configuration
    """
    log.info('Checking initial clock skew...')
    for rem in ctx.cluster.remotes.iterkeys():
        rem.run(
            args=[
                'PATH=/usr/bin:/usr/sbin',
                'ntpq', '-p',
                ],
            )

    try:
        yield

    finally:
        log.info('Checking final clock skew...')
        for rem in ctx.cluster.remotes.iterkeys():
            rem.run(
                args=[
                    'PATH=/usr/bin:/usr/sbin',
                    'ntpq', '-p',
                    ],
                )
