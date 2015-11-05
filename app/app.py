import os
from datetime import date, timedelta
from flask import Flask, request, render_template, make_response, Response
from lib.git_parse import GitHub
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
app.debug = True
scss_manifest = {app.name: ('static/_scss', 'static/css')}
# Middleware
app.wsgi_app = SassMiddleware(app.wsgi_app, scss_manifest)

servers = {
    "production-site": [os.environ.get('PROD'), 'production'],
    "staging-site": [os.environ.get('STAGING'), 'staging'],
    "production-dashboard": ['https://18f.gsa.gov/dashboard/deploy', 'production']}


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


@app.context_processor
def load_data():
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
        url = servers[server][0]
        branch = servers[server][1]
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        payload = {"ref": "refs/heads/%s" % branch}
        requests.post(url, data=json.dumps(payload), headers=headers)
    else:
        error = "No server to rebuild"
    return render_template("manage.html", error=error)
