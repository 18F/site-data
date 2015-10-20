import os
from datetime import date, timedelta
from flask import Flask, request, render_template, make_response, Response
from lib.git_parse import GitHub
from lib.fetch import Fetch
from functools import wraps
from waitress import serve
import calendar
import json
import requests
import yaml
from sassutils.wsgi import SassMiddleware

app = Flask(__name__)
scss_manifest = {app.name: ('static/_scss', 'static/css')}
# Middleware
app.wsgi_app = SassMiddleware(app.wsgi_app, scss_manifest)

drafts_api = GitHub('blog-drafts', '18F')
site_api = GitHub('18f.gsa.gov', '18F')
servers = {"production": os.environ['PROD'], "staging": os.environ['STAGING']}


# htpasswd configuration c/o http://flask.pocoo.org/snippets/8/
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == os.environ['HTUSER'] and password == os.environ['HTAUTH']


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response('Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def fetch_authors(target):
    fetch = Fetch('https://18f.gsa.gov/api/data/authors.json')
    year = date.today().year
    month_end = calendar.monthrange(year, int(target.split('-')[1].strip('0')))
    month_begin = "{0}-01".format(target)
    month_end = "{0}-{1}".format(target, month_end[1])
    commit_range = {"since": month_begin, "until": month_end}
    commits = site_api.fetch_commits(commit_range)

    authors_then = yaml.load(site_api.file_at_commit(commits[0]['sha'], '_data/authors.yml'))
    authors_now = fetch.get_data_from_url()

    fetch.save_data(authors_then, '_data/{0}.json'.format(target))
    fetch.save_data(authors_now, '_data/current.json')


def fetch_issues():
    gh = drafts_api
    fetch = Fetch('')
    issues = gh.fetch_issues()
    fetch.save_data(issues, '_data/issues.json')


def fetch_issue_events(number, part=None, name=None):
    gh = drafts_api
    fetch = Fetch('')
    events = gh.fetch_issue_events(number, part)
    if events != []:
        fetch.save_data(events, '_data/events-%s.json' % number)


def fetch_draft_milestone(i):
    gh = GitHub('blog-drafts', '18F')
    fetch = Fetch('')
    milestones = gh.fetch_milestone(i)
    fetch.save_data(milestones, '_data/issue-%s-milestones.json' % i)


@app.context_processor
def load_date():
    curr_year = date.today().year
    curr_month = date.today().month
    prev = date(curr_year, curr_month, day=1) - timedelta(days=1)
    report = dict(string=prev.strftime("%B %Y"))
    report['formatted'] = prev.strftime("%Y-%m")
    report['date'] = prev
    return dict(date=report)


@app.context_processor
def load_data():
    fetch = Fetch('')
    data = {}
    today = date.today().strftime("%Y-%m")

    if os.path.isfile("_data/{0}.json".format(today)) is False:
        fetch_authors(today)

    # if we don't have a data file for the issues, fetch and save the issues
    if os.path.isfile("_data/issues.json") is False:
        fetch_issues()

    # Now the the file exists, get some info about it to determine if it's stale
    issues = fetch.get_data_from_file("_data/issues.json")
    issues_stat = os.stat("_data/issues.json")
    m_time = date.fromtimestamp(issues_stat.st_mtime)
    today = date.today()

    # if the issues json file was last modified before today, refresh the issues
    if m_time < today:
        fetch_issues()

    # Fetch the milestone for each issue as json
    for i in issues:
        number = i['number']
        milestones = "_data/issue-%s-milestones.json" % number
        if os.path.isfile(milestones) is False:
            fetch_draft_milestone(number)

        if date.fromtimestamp(os.stat(milestones).st_mtime) < date.today():
            fetch_draft_milestone(number)

    # add each file in _data to a global `data` dict
    for f in os.listdir('_data'):
        if f[0] != ".":
            data[f.split('.')[0]] = fetch.get_data_from_file('_data/%s' % f)
    return dict(data=data)


@app.route("/")
@requires_auth
def index():
    return render_template("index.html")


@app.route("/manage/")
@requires_auth
def manage():
    error = None
    if request.args.get('rebuild'):
        server = request.args.get('rebuild')
        url = servers[server]
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        payload = {"ref": "refs/heads/%s" % server}
        requests.post(url, data=json.dumps(payload), headers=headers)
    else:
        error = "No server to rebuild"
    return render_template("manage.html", error=error)


@app.route("/_data/<filename>")
def data(filename):
    if os.path.isfile("_data/%s" % filename):
        response = make_response(open("_data/%s" % filename).read(), 200)
        response.headers['Content-Type'] = 'application/json'
    else:
        response = make_response("not found", 404)
    return response

if __name__ == "__main__":
    port = app.port
    if os.path.isdir("_data") is False:
        os.mkdir("_data")
    if os.environ['ENV'] == 'local':
        app.logger.debug('A value for debugging')
        app.logger.warning('A warning occurred (%d apples)', 42)
        app.logger.error('An error occurred')
        app.debug = True
        app.run(host='0.0.0.0', port=port)
    else:
        serve(app, port=port)
        app.debug = False
