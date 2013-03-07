import os
import pipes
import logging

from fabric.api import local

logger = logging.getLogger(__name__)


def heroku(cmd, app=None, capture=True, stdin=None):
    """
    Execute heroku command
    """
    app = app_name(app)
    if app:
        # Parse command and inject app
        parts = cmd.split(' ', 1)
        first = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        cmd = "%s -a %s %s" % (first, app, rest)
    cmd = "heroku %s" % cmd
    if stdin:
        stdin = pipes.quote(stdin)
        cmd = "echo %s | %s" % (stdin, cmd)
    return local(cmd, capture=capture)

def heroku_config_all(app=None):
    """
    heroku config. Retrieve all configuration variables.
    """
    out = heroku("config", app=app)
    config = {}
    for line in out.split("\n"):
        if line.startswith('='): continue
        parts = line.split(':', 1)
        k = parts[0].strip()
        v = parts[1].strip()
        config[k] = v
    return config

def heroku_config(key=None, app=None):
    """
    heroku config. Optional arg: key (return single value)
    """
    config = heroku_config_all(app=app)
    if key:
        val = config.get(key, None)
        logger.info("%s=%s" % (key, val))
        return val
    return config

def heroku_config_set(key, val, app=None):
    """
    heroku config:set. Args: key, val
    """
    val = pipes.quote(val)
    logger.info("setting %s=%s" % (key, val))
    heroku("config:set %s=%s" % (key, val), app=app)

def app_name(app=None):
    """
    App name; fall back on env var HEROKU_APP
    """
    if not app:
        app = os.environ.get('HEROKU_APP', None)
    # TODO: Attempt to get app name if current directory has a single heroku
    # app? (useful for --confirm when no app specified)
    return app
