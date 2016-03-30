import os
from datetime import date, timedelta
from flask import Flask, request, render_template, make_response, Response
from lib.git_parse import GitHub
import lib.ga as ga
from functools import wraps
from waitress import serve
import calendar
import json
import requests
import yaml
from sassutils.wsgi import SassMiddleware
from .models import GithubQueryLog, Author, Issue, Milestone, Month, Event, db
from .models import update_db_from_github

app = Flask(__name__)
scss_manifest = {app.name: ('static/_scss', 'static/css')}
# Middleware
app.wsgi_app = SassMiddleware(app.wsgi_app, scss_manifest)

servers = {"production": os.environ.get('PROD'), "staging": os.environ.get('STAGING')}


# htpasswd configuration c/o http://flask.pocoo.org/snippets/8/
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == os.environ['HTUSER'] and password == os.environ[
        'HTAUTH']



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


def load_issue_data():
    update_db_from_github(refresh_timedelta=app.config['REFRESH_TIMEDELTA'])
    data = {
        'months': Month.query.filter(Month.authors),
        'current': Author.query.all(),
        'issues': Issue.query.all(),
        'formatted': date.today().strftime('%Y-%-m-%d'),
    }
    for i in Issue.query:
        data['issue-{0}-milestones'.format(i.number)] = i.milestones
    return dict(data=data)


def analytics_data(start_date):
    start_date = start_date.strftime("%Y-%m-%d")
    service = ga.main()
    results = ga.get_sessions_by_month(service[0], service[1], start_date, date.today().strftime("%Y-%m-%d"))
    return results

@app.route("/")
@requires_auth
def index():
    return render_template("index.html")

@app.route("/analytics/", methods=['GET'])
@requires_auth
def analytics(start_date=None):
    if request.args != {}:
        day = int(request.args.get('start_date_1'))
        month = int(request.args.get('start_date_2'))
        year = int(request.args.get('start_date_3'))
        start_date = date(year, month, day)
    else:
        start_date = date.today()
    results = {"sessions": analytics_data(start_date), "date": start_date}
    return render_template("analytics.html", data=results)

@app.route("/issues/")
@requires_auth
def issues():
    results = load_issue_data()
    return render_template("issues.html", data=results)

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
