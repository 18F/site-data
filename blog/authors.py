from datetime import date
import calendar
import yaml
from lib.git_parse import GitHub
from lib.fetch import Fetch
class Authors():
    def __init__(self):
        self.fetch = Fetch('https://18f.gsa.gov/api/data/authors.json')
        self.github = GitHub('18f.gsa.gov', '18F')

    def fetch_all(self, target):
        fetch = self.fetch
        site_api = self.github

        year=date.today().year
        month_end = calendar.monthrange(year, int(target.split('-')[1].strip('0')))
        month_begin = "{0}-01".format(target)
        month_end = "{0}-{1}".format(target, month_end[1])
        commit_range = {"since":month_begin, "until":month_end}
        commits = site_api.fetch_commits(commit_range)

        authors_then = yaml.load(site_api.file_at_commit(commits[0]['sha'], '_data/authors.yml'))
        authors_now = fetch.get_data_from_url()

        fetch.save_data(authors_then, '_data/{0}.json'.format(target))
        fetch.save_data(authors_now, '_data/current.json')

    def fetch_current(self):
        pass

    def fetch_month(self, month):
        pass
