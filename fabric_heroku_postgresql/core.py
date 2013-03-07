import os
import re
import StringIO
import pipes
import logging

from fabric.api import local

__all__ = [
        'heroku_pg_create',
        'heroku_fork',
        'heroku_follow',
        'heroku_pg_create_using_snapshot',
        'heroku_pg_drop',
        'heroku_pg_list',
        'heroku_pg_psql',
        'heroku_pgbackups_capture',
        'heroku_pgbackups_restore',
        'heroku_pgbackups_list',
        ]


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

def heroku_pg_psql(db, sql, app=None):
    """
    Run provided query through pgsql
    """
    stdin = sql
    db = format_db_name(db)
    return heroku("pg:psql %s" % db, app=app, stdin=stdin)

def heroku_pg_get_postgis_version(db, app=None):
    """
    Retrieve PostGIS version of specified DB
    """
    sql = "SELECT postgis_version();"
    out = heroku_pg_psql(db, sql, app=app)
    lines = out.split("\n")
    if len(lines) > 3:
        version_info = lines[2]
        parts = version_info.strip().split()
        version = parts[0]
    else:
        version = None
    return version

def heroku_pg_create(
        app=None,
        plan='ronin',
        version='9.1',
        fork=None,
        follow=None,
        postgis=True,
        ):
    """
    Create a new heroku-postgres database with the specified plan
    """

    cmd = "addons:add heroku-postgresql:%s" % plan
    if version:
        cmd += " --version=%s" % version
    if fork:
        cmd += " --fork=%s" % format_db_name(fork)
    elif follow:
        cmd += " --follow=%s" % format_db_name(follow)
    out = heroku(cmd, app=app)
    match = re.search('(HEROKU_POSTGRESQL_\w+)_URL', out, re.M)
    if not match:
        logger.error("Error creating DB; output: %s" % out)
        return None

    newdb = match.group(1)
    logger.info("Started creating DB: %s (this takes several minutes)" % newdb)
    heroku("pg:wait", app=app, capture=False)
    if postgis:
        heroku_pg_add_postgis(newdb, app=app)
    logger.info("Finished creating DB: %s" % newdb)
    return newdb

def heroku_pg_add_postgis(db, app=None):
    """
    Add PostGIS support to the specified DB
    """
    sql = "create extension postgis"
    return heroku_pg_psql(db, sql, app=app)

def heroku_pg_drop(db, app=None):
    """
    Drop specified DB
    """
    db = format_db_name(db)
    info = heroku_pg_info(db, app=app)
    app = app_name(app)
    confirm = " --confirm %s" % app if app else ""
    heroku("addons:remove %s %s" % (db, confirm), app=app, capture=False)

def heroku_fork_follow(db, action='fork', app=None, plan=None, **kwargs):
    """
    Fork or follow database and return new DB name. Unless specified, plan and
    version will match existing DB.
    """
    info = heroku_pg_info(db, app=app)
    if info['Fork/Follow'] != 'Available':
        raise Exception("Fork/Follow not available for selected DB")
    if plan is None:
        plan = info['Plan'].lower()
    if action is 'fork':
        kwargs['fork'] = db
    elif action is 'follow':
        kwargs['follow'] = db
    else:
        raise Exception("Unknown action for fork/follow")

    return heroku_pg_create(plan=plan, app=app, **kwargs)

def heroku_fork(db, **kwargs):
    """
    Fork specified DB. Keyword args passed to heroku_pg_create(). If not
    specified, plan and version will match existing DB.
    """
    return heroku_fork_follow(db, action='fork', **kwargs)

def heroku_follow(db, app=None, plan=None, **kwargs):
    """
    Follow specified DB. Keyword args passed to heroku_pg_create(). If not
    specified, plan and version will match existing DB.
    """
    return heroku_fork_follow(db, action='follow', **kwargs)

def heroku_pgbackups_capture(db, app=None):
    """
    Capture backup of specified DB, and return backup ID
    """
    db = format_db_name(db)
    logger.info("Capturing pgbackup of %s" % db)
    out = heroku("pgbackups:capture %s" % db, app=app)
    pat = '(HEROKU_POSTGRESQL_[A-Z]+)_URL\s*[->]*backup[->]*\s*([a-z0-9]+)'
    match = re.search(pat, out)
    if not match:
        raise Exception("Error extracting backup ID from output %s" % out)

    backup = match.group(2)
    logger.info("Captured backup %s of db %s" % (backup, db))
    return backup

def heroku_pgbackups_restore(db, backup, app=None):
    """
    Restore backup. Specify DB and backup ID.
    """
    db = format_db_name(db)
    app = app_name(app)
    confirm = " --confirm %s" % app if app else ""
    out = heroku("pgbackups:restore %s %s%s" % (db, backup, confirm), app=app)

def heroku_pgbackups_list(app=None):
    heroku("pgbackups", app=app, capture=False)

def heroku_pg_create_using_snapshot(db, app=None, **kwargs):
    """
    Create new database using specified snapshot. Similar to heroku_fork() but
    works on non-production-tier databases.
    """
    logger.info("Creating DB using snapshot from %s" % db)

    # Step 0: Get DB info and PostGIS info for existing DB
    pg_info = heroku_pg_info(db)
    postgis_version = heroku_pg_get_postgis_version(db)

    # Step 1: Create new DB
    logger.info("Step 1 of 3: Create new DB")
    if postgis_version:
        # Force PostGIS if enabled on source DB
        kwargs['postgis'] = True
    newdb = heroku_pg_create(app=app, **kwargs)

    # Step 2: Snapshot old DB
    logger.info("Step 2 of 3: Creating snapshot of s" % db)
    backup = heroku_pgbackups_capture(db, app=app)

    # Step 3: Restore snapshot to new DB
    logger.info("Step 3 of 3: Restoring snapshot %s to new DB %s" % (
        backup, newdb))
    heroku_pgbackups_restore(newdb, backup, app=app)

def heroku_pg_info(db, app=None):
    """
    Retrieve info for specified DB
    """
    db = format_db_name(db)
    out = heroku("pg:info %s" % db, app=app)
    info = {}
    for line in out.split("\n"):
        parts = line.split(':', 2)
        if len(parts) is 2:
            k = parts[0].rstrip(':')
            v = parts[1].strip()
            info[k] = v
    return info

def heroku_pg_list(app=None):
    heroku("pg", app=app, capture=False)

def format_db_name(db):
    """
    Format DB name.
    Examples:
      blue => HEROKU_POSTGRESQL_BLUE
      HEROKU_POSTGRESQL_AMBER_URL => HEROKU_POSTGRESQL_AMBER
    """
    if not db.startswith('HEROKU'):
        color = db.upper()
        db = 'HEROKU_POSTGRESQL_%s' % color
    if db.endswith('_URL'):
        db = db[0:-4]
    return db

def app_name(app=None):
    if not app:
        app = os.environ.get('HEROKU_APP', None)
    # TODO: Attempt to get app name if current directory has a single heroku
    # app? (useful for --confirm when no app specified)
    return app
