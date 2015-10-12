from datetime import date, time, timedelta
from flask import Flask, request, render_template, make_response, Response
from lib.git_parse import GitHub
from lib.fetch import Fetch
from functools import wraps
from waitress import serve
import requests, json
import yaml, os
from sassutils.wsgi import SassMiddleware
from .models import GithubQueryLog, Author, Issue, Milestone, Month, db

app = Flask(__name__)
scss_manifest = {app.name: ('static/sass', 'static/css', 'static/css')}
# Middleware
app.wsgi_app = SassMiddleware(app.wsgi_app, scss_manifest)

drafts_api = GitHub('blog-drafts', '18F')
site_api = GitHub('18f.gsa.gov', '18F')
servers = {"production":os.environ['PROD'], "staging":os.environ['STAGING']}
# htpasswd configuration c/o http://flask.pocoo.org/snippets/8/
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == os.environ['HTUSER'] and password == os.environ['HTAUTH']

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
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

def fetch_authors_as_of_month(month):
    "Fetches from github blog authors as of ``month`` instance"
    month_begin = "{0}-01".format(month)
    month_end = "{0}-{1}".format(month, month.end().day)
    commit_range = {"since":month_begin, "until":month_end}
    commits = site_api.fetch_commits(commit_range)
    if commits:
        authors = yaml.load(site_api.file_at_commit(commits[0]['sha'], '_data/authors.yml'))
    return authors or {}

def add_authors_to_month(authors, month):
    for (username, author_data) in authors.items():
        author = Author.from_gh_data(username, author_data)
        db.session.add(author)
        if month not in author.months:
            author.months.append(month)

def create_months():
    FIRST_MONTH_OF_BLOG = date(2014, 3, 1)
    month = Month.get_or_create(FIRST_MONTH_OF_BLOG)
    while month.begin <= date.today():
        db.session.add(month)
        if (not month.authors) or (not month.author_list_is_complete()):
            authors = fetch_authors_as_of_month(month)
            add_authors_to_month(authors, month)
        month = month.next()
    db.session.commit()

def fetch_authors():
    create_months()
    fetch = Fetch('https://18f.gsa.gov/api/data/authors.json')
    authors_now = fetch.get_data_from_url()
    for (username, author_data) in authors_now.items():
        author = Author.from_gh_data(username, author_data)
        db.session.add(author)
    GithubQueryLog.log('authors')
    db.session.commit()

def fetch_issues():
    gh = drafts_api
    fetch = Fetch('')
    issues = drafts_api.fetch_issues()

    gh = GitHub('blog-drafts', '18F')
    fetch = Fetch('')

    # clear all issues - what about milestones?
    Milestone.query.delete()
    Issue.query.delete()
    for issue_data in issues:
        issue = Issue.from_dict(issue_data)
        db.session.add(issue)
        milestones = gh.fetch_milestone(issue.number)
        for milestone_data in milestones:
            issue.milestones.append(Milestone.from_dict(milestone_data))
    GithubQueryLog.log('issues')
    db.session.commit()

def fetch_issue_events(number, part=None, name=None):
    gh = drafts_api
    fetch = Fetch('')
    events = gh.fetch_issue_events(number, part)
    if events != []:
        fetch.save_data(events, '_data/events-%s.json' % number )

def fetch_draft_milestone(i):
    gh = GitHub('blog-drafts', '18F')
    fetch = Fetch('')
    milestones = gh.fetch_milestone(i)
    fetch.save_data(milestones, '_data/issue-%s-milestones.json' % i)

@app.context_processor
def load_date():
    current = date.today().strftime("%B")
    curr_year = date.today().year
    curr_month = date.today().month
    prev = date(curr_year, curr_month, day=1) - timedelta(days=1)
    report = dict(string = prev.strftime("%B %Y"))
    report['formatted'] = prev.strftime("%Y-%m")
    report['date'] = prev
    return dict(date=report)

@app.context_processor
def load_data():
    fetch = Fetch('')
    data = {}
    today = date.today().strftime("%Y-%m")

    if not GithubQueryLog.was_fetched_today('authors'):
        fetch_authors()
    if not GithubQueryLog.was_fetched_today('issues'):
        fetch_issues()

    data['months'] = Month.query.filter(Month.authors)
    # {str(m): m.authors for m in Month.query}
    data['current'] = Author.query.all()
    data['issues'] = Issue.query.all()
    for issue in Issue.query:
        data['issue-{0}-milestones'.format(issue.number)] = issue.milestones
    data['formatted'] = date.today().strftime('%Y-%-m-%d')

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
    app.port=port
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
