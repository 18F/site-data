from flask.ext.script import Manager
from app.app import app
from lib.git_parse import GitHub
from lib.fetch import Fetch
# from blog.issues import Drafts
# from blog.authors import Authors
from datetime import date
from os import path, stat, environ
from waitress import serve

manager = Manager(app)

port = port = int(environ["VCAP_APP_PORT"])

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

if __name__ == "__main__":
    manager.run()
