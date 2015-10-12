import os
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app.app import app
from lib.git_parse import GitHub
from lib.fetch import Fetch
# from blog.issues import Drafts
# from blog.authors import Authors
from datetime import date
from os import path, stat, environ
from waitress import serve
from config import config
from app import db

config_name = os.getenv('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])
db.init_app(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

port = int(environ["VCAP_APP_PORT"])

if environ['ENV'] == 'local':
    app.logger.debug('A value for debugging')
    app.logger.warning('A warning occurred (%d apples)', 42)
    app.logger.error('An error occurred')
    app.debug = True
else:
    app.debug = False

@manager.command
def updatedata():
    fetch    = Fetch('')
    authors  = Authors()
    drafts   = Drafts()
    today = date.today().strftime("%Y-%m")
    print "Fetching authors"
    authors.fetch_all(today)
    print "Fetching drafts"
    drafts.fetch_all()

    if path.exists('_data/issues.json'):
        issues = fetch.get_data_from_file("_data/issues.json")

        # Fetch the milestone for each issue as json
        for i in issues:
            number = i['number']
            milestones = "_data/issue-%s-milestones.json" % number
            print "Fetching milestones for %s" % number
            drafts.fetch_milestone(number)

@manager.command
def deploy():
    serve(app, port=port)

@manager.command
def clean_db():
    for tbl in reversed(db.metadata.sorted_tables):
        db.engine.execute(db.metadata.sorted_tables[0].delete())

if __name__ == "__main__":
    manager.run()
