from flask.ext.script import Manager
from app.app import app
from lib.git_parse import GitHub
from lib.fetch import Fetch
from blog.issues import Drafts
from blog.authors import Authors
from datetime import date
from os import path, stat

manager = Manager(app)

@manager.command
def updatedata():
    fetch    = Fetch('')
    authors  = Authors()
    drafts   = Drafts()
    today = date.today().strftime("%Y-%m")
    authors.fetch_all(today)
    drafts.fetch_all()
    if path.exists('_data/issues.json'):
        issues = fetch.get_data_from_file("_data/issues.json")

        # Fetch the milestone for each issue as json
        for i in issues:
            number = i['number']
            milestones = "_data/issue-%s-milestones.json" % number
            drafts.fetch_milestone(number)

@manager.command
def hello():
    print "hello"

if __name__ == "__main__":
    manager.run()
