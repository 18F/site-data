from datetime import date, time, timedelta
from flask import Flask, request, render_template, make_response, Response
from lib.git_parse import GitHub
from lib.fetch import Fetch
from functools import wraps
from sassutils.wsgi import SassMiddleware
from waitress import serve
import requests, json
import yaml, os, calendar

app = Flask(__name__)

app.config.from_pyfile('../config.py')
config = app.config
port = config["PORT"]
drafts_api = GitHub('blog-drafts', '18F')
site_api = GitHub('18f.gsa.gov', '18F')
servers = config['SERVERS']

scss_manifest = {app.name: ('static/sass', 'static/css', '/static/css')}
# Middleware
app.wsgi_app = SassMiddleware(app.wsgi_app, scss_manifest)

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

# Load _data files into memory
@app.context_processor
def load_data():
    # add each file in _data to a global `data` dict
    data = {}
    fetch = Fetch('')
    for f in os.listdir('_data'):
        if f[0] != ".":
            data[f.split('.')[0]] = fetch.get_data_from_file('_data/%s' % f)
    return dict(data=data)

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
        serve(app, port=app.config['PORT'])
        app.debug = False
