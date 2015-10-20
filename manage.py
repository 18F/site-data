import os
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app.app import app
from lib.git_parse import GitHub
from datetime import date, timedelta
from os import path, stat, environ
from waitress import serve
from config import config
from app import db, models

config_name = os.getenv('FLASK_CONFIG') or 'default'
app.logger.info('Using FLASK_CONFIG {0} from environment'.format(config_name))
app.config.from_object(config[config_name])
db.init_app(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if environ['ENV'] == 'local':
    app.logger.debug('A value for debugging')
    app.logger.warning('A warning occurred (%d apples)', 42)
    app.logger.error('An error occurred')
    app.debug = True
else:
    app.debug = False

@manager.command
def updatedata(days=0):
    """Refresh stored data from upstream sources.

    Args:
        days: Pull from each data source only if the last pull was at least
            this many days ago (default 0)
    """
    models.update_db_from_github(timedelta(days=days))


@manager.command
def deploy():
    port = int(environ["VCAP_APP_PORT"])
    serve(app, port=port)

@manager.command
def cleandata():
    "Deletes *all* stored data"
    for tbl in reversed(db.metadata.sorted_tables):
        db.engine.execute(tbl.delete())

if __name__ == "__main__":
    manager.run()
