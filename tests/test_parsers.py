from datetime import datetime

from apscheduler.triggers.base import BaseTrigger  # type: ignore
from pytest import mark
from pytz import utc

from deck_chores import config
from deck_chores.parsers import _parse_labels as parse_labels
from deck_chores.parsers import CronTrigger, DateTrigger, IntervalTrigger, JobConfigValidator

from tests.utils import equal_triggers


config.generate_config()


def assert_expected_job_result(labels, expected_jobs):
    _, _, result = parse_labels(labels)

    assert len(result) == len(expected_jobs)

    for name, definition in result.items():
        definition.pop('service_id')
        assert len(definition) == 5
        expected_job = expected_jobs[name]
        for attr in definition:
            value = definition[attr]
            if isinstance(value, BaseTrigger):
                assert equal_triggers(value, expected_job[attr])
            else:
                assert value == expected_job[attr]


def test_parse_labels():
    labels = {
        'com.docker.compose.project': 'test_project',
        'com.docker.compose.service': 'ham_machine',
        'deck-chores.backup.interval': 'daily',
        'deck-chores.backup.command': '/usr/local/bin/backup.sh',
        'deck-chores.backup.user': 'www-data',
        'deck-chores.pull-data.date': '1945-05-08 00:01:00',
        'deck-chores.pull-data.command': '/usr/local/bin/pull.sh',
        'deck-chores.gen-thumbs.cron': '*/10 * * * *',
        'deck-chores.gen-thumbs.command': 'python /scripts/gen_thumbs.py',
        'deck-chores.gen-thumbs.max': '3'
    }
    expected_jobs = \
        {'backup': {'trigger': IntervalTrigger(days=1), 'command': '/usr/local/bin/backup.sh',
                    'name': 'backup', 'user': 'www-data', 'max': 1},
         'pull-data': {'trigger': DateTrigger(datetime(1945, 5, 8, 0, 1,tzinfo=utc)), 'name': 'pull-data',
                       'command': '/usr/local/bin/pull.sh', 'user': 'root', 'max': 1},
         'gen-thumbs': {'trigger': CronTrigger('*', '*', '*', '*/10', '*', '*', '*', '*'),
                        'name': 'gen-thumbs', 'command': 'python /scripts/gen_thumbs.py',
                        'user': 'root', 'max': 3}}
    assert_expected_job_result(labels, expected_jobs)


def test_interval_trigger():
    validator = JobConfigValidator({'trigger': {'coerce': 'interval'}})
    assert validator({'trigger': '15'})
    assert equal_triggers(validator.document['trigger'], IntervalTrigger(seconds=15))


@mark.parametrize('default,value,result',
                  ((('image', 'service'), '', 'image,service'),
                   (('image', 'service'), 'noservice', 'image'),
                   (('service',), 'image', 'image,service')))
def test_options(default, value, result):
    config.cfg.default_options = default
    labels = {'deck-chores.options': value}
    assert parse_labels(labels) == ('', result, {})
