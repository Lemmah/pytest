# -*- coding: utf-8 -*-
import os
import pytest


def test_nothing_logged(testdir):
    testdir.makepyfile('''
        import sys

        def test_foo():
            sys.stdout.write('text going to stdout')
            sys.stderr.write('text going to stderr')
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])
    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])


def test_messages_logged(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            sys.stdout.write('text going to stdout')
            sys.stderr.write('text going to stderr')
            logger.info('text going to logger')
            assert False
        ''')
    result = testdir.runpytest('--log-level=INFO')
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*text going to logger*'])
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])


def test_setup_logging(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def setup_function(function):
            logger.info('text going to logger from setup')

        def test_foo():
            logger.info('text going to logger from call')
            assert False
        ''')
    result = testdir.runpytest('--log-level=INFO')
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log setup -*',
                                 '*text going to logger from setup*',
                                 '*- Captured *log call -*',
                                 '*text going to logger from call*'])


def test_teardown_logging(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            logger.info('text going to logger from call')

        def teardown_function(function):
            logger.info('text going to logger from teardown')
            assert False
        ''')
    result = testdir.runpytest('--log-level=INFO')
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*text going to logger from call*',
                                 '*- Captured *log teardown -*',
                                 '*text going to logger from teardown*'])


def test_disable_log_capturing(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            sys.stdout.write('text going to stdout')
            logger.warning('catch me if you can!')
            sys.stderr.write('text going to stderr')
            assert False
        ''')
    result = testdir.runpytest('--no-print-logs')
    print(result.stdout)
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])
    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])


def test_disable_log_capturing_ini(testdir):
    testdir.makeini(
        '''
        [pytest]
        log_print=False
        '''
    )
    testdir.makepyfile('''
        import sys
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            sys.stdout.write('text going to stdout')
            logger.warning('catch me if you can!')
            sys.stderr.write('text going to stderr')
            assert False
        ''')
    result = testdir.runpytest()
    print(result.stdout)
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])
    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])


@pytest.mark.parametrize('enabled', [True, False])
def test_log_cli_enabled_disabled(testdir, enabled):
    msg = 'critical message logged by test'
    testdir.makepyfile('''
        import logging
        def test_log_cli():
            logging.critical("{}")
    '''.format(msg))
    if enabled:
        testdir.makeini('''
            [pytest]
            log_cli=true
        ''')
    result = testdir.runpytest('-s')
    if enabled:
        result.stdout.fnmatch_lines([
            'test_log_cli_enabled_disabled.py::test_log_cli ',
            'test_log_cli_enabled_disabled.py* CRITICAL critical message logged by test',
            'PASSED',
        ])
    else:
        assert msg not in result.stdout.str()


def test_log_cli_default_level(testdir):
    # Default log file level
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_cli(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_cli_handler.level == logging.NOTSET
            logging.getLogger('catchlog').info("INFO message won't be shown")
            logging.getLogger('catchlog').warning("WARNING message will be shown")
    ''')
    testdir.makeini('''
        [pytest]
        log_cli=true
    ''')

    result = testdir.runpytest()

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_cli_default_level.py::test_log_cli ',
        'test_log_cli_default_level.py*WARNING message will be shown*',
    ])
    assert "INFO message won't be shown" not in result.stdout.str()
    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_log_cli_level(testdir):
    # Default log file level
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_cli(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_cli_handler.level == logging.INFO
            logging.getLogger('catchlog').debug("This log message won't be shown")
            logging.getLogger('catchlog').info("This log message will be shown")
            print('PASSED')
    ''')
    testdir.makeini('''
        [pytest]
        log_cli=true
    ''')

    result = testdir.runpytest('-s', '--log-cli-level=INFO')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_cli_level.py*This log message will be shown',
        'PASSED',  # 'PASSED' on its own line because the log message prints a new line
    ])
    assert "This log message won't be shown" not in result.stdout.str()

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0

    result = testdir.runpytest('-s', '--log-level=INFO')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_cli_level.py* This log message will be shown',
        'PASSED',  # 'PASSED' on its own line because the log message prints a new line
    ])
    assert "This log message won't be shown" not in result.stdout.str()

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_log_cli_ini_level(testdir):
    testdir.makeini(
        """
        [pytest]
        log_cli=true
        log_cli_level = INFO
        """)
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_cli(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_cli_handler.level == logging.INFO
            logging.getLogger('catchlog').debug("This log message won't be shown")
            logging.getLogger('catchlog').info("This log message will be shown")
            print('PASSED')
    ''')

    result = testdir.runpytest('-s')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_cli_ini_level.py* This log message will be shown',
        'PASSED',  # 'PASSED' on its own line because the log message prints a new line
    ])
    assert "This log message won't be shown" not in result.stdout.str()

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_log_file_cli(testdir):
    # Default log file level
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_file(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_file_handler.level == logging.WARNING
            logging.getLogger('catchlog').info("This log message won't be shown")
            logging.getLogger('catchlog').warning("This log message will be shown")
            print('PASSED')
    ''')

    log_file = testdir.tmpdir.join('pytest.log').strpath

    result = testdir.runpytest('-s', '--log-file={0}'.format(log_file), '--log-file-level=WARNING')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_file_cli.py PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
    assert os.path.isfile(log_file)
    with open(log_file) as rfh:
        contents = rfh.read()
        assert "This log message will be shown" in contents
        assert "This log message won't be shown" not in contents


def test_log_file_cli_level(testdir):
    # Default log file level
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_file(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_file_handler.level == logging.INFO
            logging.getLogger('catchlog').debug("This log message won't be shown")
            logging.getLogger('catchlog').info("This log message will be shown")
            print('PASSED')
    ''')

    log_file = testdir.tmpdir.join('pytest.log').strpath

    result = testdir.runpytest('-s',
                               '--log-file={0}'.format(log_file),
                               '--log-file-level=INFO')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_file_cli_level.py PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
    assert os.path.isfile(log_file)
    with open(log_file) as rfh:
        contents = rfh.read()
        assert "This log message will be shown" in contents
        assert "This log message won't be shown" not in contents


def test_log_level_not_changed_by_default(testdir):
    testdir.makepyfile('''
        import logging
        def test_log_file():
            assert logging.getLogger().level == logging.WARNING
    ''')
    result = testdir.runpytest('-s')
    result.stdout.fnmatch_lines('* 1 passed in *')


def test_log_file_ini(testdir):
    log_file = testdir.tmpdir.join('pytest.log').strpath

    testdir.makeini(
        """
        [pytest]
        log_file={0}
        log_file_level=WARNING
        """.format(log_file))
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_file(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_file_handler.level == logging.WARNING
            logging.getLogger('catchlog').info("This log message won't be shown")
            logging.getLogger('catchlog').warning("This log message will be shown")
            print('PASSED')
    ''')

    result = testdir.runpytest('-s')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_file_ini.py PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
    assert os.path.isfile(log_file)
    with open(log_file) as rfh:
        contents = rfh.read()
        assert "This log message will be shown" in contents
        assert "This log message won't be shown" not in contents


def test_log_file_ini_level(testdir):
    log_file = testdir.tmpdir.join('pytest.log').strpath

    testdir.makeini(
        """
        [pytest]
        log_file={0}
        log_file_level = INFO
        """.format(log_file))
    testdir.makepyfile('''
        import pytest
        import logging
        def test_log_file(request):
            plugin = request.config.pluginmanager.getplugin('logging-plugin')
            assert plugin.log_file_handler.level == logging.INFO
            logging.getLogger('catchlog').debug("This log message won't be shown")
            logging.getLogger('catchlog').info("This log message will be shown")
            print('PASSED')
    ''')

    result = testdir.runpytest('-s')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_log_file_ini_level.py PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
    assert os.path.isfile(log_file)
    with open(log_file) as rfh:
        contents = rfh.read()
        assert "This log message will be shown" in contents
        assert "This log message won't be shown" not in contents
