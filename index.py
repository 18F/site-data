from flask import Flask, request, render_template, make_response
from lib.git_parse import GitHub
from lib.fetch import Fetch
from datetime import date, time, timedelta
from waitress import serve
import yaml, os, calendar
app = Flask(__name__)
port = port = int(os.getenv("VCAP_APP_PORT"))
drafts_api = GitHub('blog-drafts', '18F')
site_api = GitHub('18f.gsa.gov', '18F')

def fetch_authors(target):
    fetch = Fetch('https://18f.gsa.gov/api/data/authors.json')
    year=date.today().year
    month_end = calendar.monthrange(year, int(target.split('-')[1].strip('0')))
    month_begin = "{0}-01".format(target)
    month_end = "{0}-{1}".format(target, month_end[1])
    commit_range = {"since":month_begin, "until":month_end}
    commits = site_api.fetch_commits(commit_range)

    authors_then = yaml.load(site_api.file_at_commit(commits[0]['sha'], '_data/authors.yml'))
    authors_now = fetch.get_data_from_url()

    then = fetch.save_data(authors_then, '_data/{0}.json'.format(target))
    now = fetch.save_data(authors_now, '_data/current.json')

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

# @app.context_processor
# def load_post_names():
#     gh = GitHub('18f.gsa.gov', '18F')
#     data = json.loads(gh.get_repo_contents('_posts'))
#
#     today = date.today()
#     month = today.month
#     year = today.year
#     posts = dict()
#     match = "{0}-{1}".format(year, month)
#     posts['current'] = gh.parse_by_key(data, 'name', match)
#     return dict(posts=posts)

@app.route("/")
def index():
    return render_template("index.html")

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
    if os.environ['PRODUCTION'] == '0':
        app.debug = True
        app.run(host='0.0.0.0', port=port)
    else:
        serve(app, port=port)
        app.debug = False
