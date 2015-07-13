from flask import Flask, request, render_template, g
from lib.git_parse import GitHub
from lib.fetch import Fetch
from datetime import date, time, timedelta
import json, yaml, os

app = Flask(__name__)

def fetch_data(target):
    fetch = Fetch('https://18f.gsa.gov/api/data/authors.json')
    gh = GitHub('18F', '18f.gsa.gov')

    commits = gh.fetch_commits({"since":"{0}-01".format(target), "until":"{0}-30".format(target)})
    authors_then = yaml.load(gh.file_at_commit(commits[0]['sha'], '_data/authors.yml'))
    authors_now = fetch.get_authors_from_url()
    then = fetch.save_authors(authors_then, '_data/{0}.json'.format(target))
    now = fetch.save_authors(authors_now, '_data/current.json')

@app.context_processor
def load_date():
    current = date.today().strftime("%B")
    prev = date(date.today().year, date.today().month, day=1) - timedelta(days=1)
    report = dict(string = prev.strftime("%B %Y"))
    report['formatted'] = prev.strftime("%Y-%m")
    report['date'] = prev
    return dict(date=report)

@app.context_processor
def load_data():
    fetch = Fetch('')
    data = {}
    today = date.today().strftime("%Y-%m")
    if os.path.isfile("_data/{0}.json".format(today)) is False:
        fetch_data(today)

    for f in os.listdir('_data'):
        data[f.split('.')[0]] = fetch.get_authors_from_file('_data/%s' % f)
    return dict(data=data)

@app.route("/")
def hello():
    return render_template("index.html")

if __name__ == "__main__":
    app.debug = True
    app.run()
