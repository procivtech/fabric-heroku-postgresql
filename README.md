fabric_heroku_postgresql
========================

Fabric helpers for Heroku PostgreSQL database management.

Usage:
------

To start using fabric_heroku_postgresql, add a wildcard import to your
fabfile.py:

    from fabric_heroku_postgresql.core import *

First, we need to specify which Heroku app we'll be dealing with. This can be
specified via an environment variable `HEROKU_APP` or via an `app` keyword
argument to any command:

    # Export HEROKU_APP environment variable
    export HEROKU_APP=my-heroku-app

    # Alternately, pass app=my-heroku-app
    fab heroku_pg_list:app=my-heroku-app

Create new DB:

    # Create new DB with default plan & version (ronin, 9.1)
    fab heroku_pg_create

    # Create new DB with ronin plan and version 9.0
    fab heroku_pg_create:plan=ronin,version=9.0

    # Create new PostGIS DB
    fab heroku_pg_create:postgis=true

Fork/Follow:

    # Forks HEROKU_POSTGRESQL_AMBER db
    fab heroku_pg_fork:amber

    # Forks HEROKU_POSTGRESQL_AMBER db using 'crane' plan and PostGIS
    fab heroku_pg_fork:amber,plan=crane,postgis=true

Create from snapshot:

    # Creates new DB, then creates snapshot of HEROKU_POSTGRESQL_AMBER DB, and
    # finally restores snapshot to new DB

    fab heroku_pg_create_using_snapshot:amber

    # Creates new DB with 'crane' plan and PostGIS
    fab heroku_pg_create_using_snapshot:amber,plan=crane,postgis=true
