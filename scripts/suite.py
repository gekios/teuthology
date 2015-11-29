import docopt
import sys

import teuthology.suite
from teuthology.config import config

doc = """
usage: teuthology-suite --help
       teuthology-suite [-v | -vv ] --suite <suite> [options] [<config_yaml>...]

Run a suite of ceph integration tests. A suite is a directory containing
facets. A facet is a directory containing config snippets. Running a suite
means running teuthology for every configuration combination generated by
taking one config snippet from each facet. Any config files passed on the
command line will be used for every combination, and will override anything in
the suite. By specifying a subdirectory in the suite argument, it is possible
to limit the run to a specific facet. For instance -s upgrade/dumpling-x only
runs the dumpling-x facet of the upgrade suite.

Miscellaneous arguments:
  -h, --help                  Show this help message and exit
  -v, --verbose               Be more verbose
  --dry-run                   Do a dry run; do not schedule anything. In
                              combination with -vv, also call
                              teuthology-schedule with --dry-run.

Standard arguments:
  <config_yaml>               Optional extra job yaml to include
  -s <suite>, --suite <suite>
                              The suite to schedule
  --wait                      Block until the suite is finished
  -c <ceph>, --ceph <ceph>    The ceph branch to run against
                              [default: master]
  -k <kernel>, --kernel <kernel>
                              The kernel branch to run against; if not
                              supplied, the installed kernel is unchanged
  -f <flavor>, --flavor <flavor>
                              The kernel flavor to run against: ('basic',
                              'gcov', 'notcmalloc')
                              [default: basic]
  -t <branch>, --teuthology-branch <branch>
                              The teuthology branch to run against.
                              [default: master]
  -m <type>, --machine-type <type>
                              Machine type [default: {default_machine_type}]
  -d <distro>, --distro <distro>
                              Distribution to run against
  --suite-branch <suite_branch>
                              Use this suite branch instead of the ceph branch
  --suite-dir <suite_dir>     Use this alternative directory as-is when
                              assembling jobs from yaml fragments. This causes
                              <suite_branch> to be ignored for scheduling
                              purposes, but it will still be used for test
                              running.

Scheduler arguments:
  --owner <owner>             Job owner
  -e <email>, --email <email>
                              When tests finish or time out, send an email
                              here. May also be specified in ~/.teuthology.yaml
                              as 'results_email'
  -N <num>, --num <num>       Number of times to run/queue the job
                              [default: 1]
  -l <jobs>, --limit <jobs>   Queue at most this many jobs
                              [default: 0]
  --subset <index/outof>      Instead of scheduling the entire suite, break the
                              set of jobs into <outof> pieces (each of which will
                              contain each facet at least once) and schedule
                              piece <index>.  Scheduling 0/<outof>, 1/<outof>,
                              2/<outof> ... <outof>-1/<outof> will schedule all
                              jobs in the suite (many more than once).
  -p <priority>, --priority <priority>
                              Job priority (lower is sooner)
                              [default: 1000]
  --timeout <timeout>         How long, in seconds, to wait for jobs to finish
                              before sending email. This does not kill jobs.
                              [default: {default_results_timeout}]
  --filter KEYWORDS           Only run jobs whose description contains at least one
                              of the keywords in the comma separated keyword
                              string specified.
  --filter-out KEYWORDS       Do not run jobs whose description contains any of
                              the keywords in the comma separated keyword
                              string specified.
  --archive-upload RSYNC_DEST Rsync destination to upload archives.
  --throttle SLEEP            When scheduling, wait SLEEP seconds between jobs.
                              Useful to avoid bursts that may be too hard on
                              the underlying infrastructure or exceed OpenStack API
                              limits (server creation per minute for instance).
""".format(default_machine_type=config.default_machine_type,
           default_results_timeout=config.results_timeout)


def main(argv=sys.argv[1:]):
    args = docopt.docopt(doc, argv=argv)
    teuthology.suite.main(args)
