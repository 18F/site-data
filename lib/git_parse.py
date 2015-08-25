import requests, yaml
from requests.auth import HTTPBasicAuth
import os
"""
parses the first commit from:
git log --before={YYY-MM-DD} --after={YYYY-MM-DD} --pretty=format:"%H"
"""
class GitHub():
    def __init__(self, repo, owner):
        self.repo = repo.strip()
        self.owner = owner.strip()
        self.api = "https://api.github.com"
        self.raw = "https://raw.githubusercontent.com"
        self.user = os.environ['GITHUB_USER']
        self.auth = os.environ['GITHUB_AUTH']

    def fetch_raw(self, request_string):
        url = "%s/%s" % (self.raw, request_string)
        content = requests.get(url)
        if content.ok:
            return content
        else:
            return False

    def fetch_endpoint(self, endpoint):
        git_url = "%s/repos/%s/%s/%s" % (self.api, self.owner, self.repo, endpoint)
        content = requests.get(git_url, auth=HTTPBasicAuth(self.user, self.auth))
        if (content.ok):
            return content
        else:
            return False

    def search(self, endpoint, query, sort=None, order=None):
        git_url = "%s/search/%s?%s&%s&%s," % (endpoint, query, sort, order)
        print "Fetching search query %s from GitHub" % query
        content = requests.get(git_url, auth=HTTPBasicAuth(self.user, self.auth))
        if (content.ok):
            return content
        else:
            return False

    def fetch_commits(self, params):
        commits = self.fetch_endpoint('commits')
        if commits:
            return commits.json()
        else:
            return False

    def fetch_issues(self, params=None):
        issues = self.fetch_endpoint('issues?per_page=100')
        if issues:
            return issues.json()
        else:
            return False

    def split_by_event(self, events, part):
        reduced = list()
        for e in events:
            if e['event'] == part:
                reduced.append(e)
        return reduced

    def fetch_issue_events(self, issue, part=None, name=None):
        events = self.fetch_endpoint('issues/%s/events?per_page=100' % issue)
        if events:
            if part != None:
                requested = self.split_by_event(events.json(), part)
            else:
                requested = events.json()
            return requested
        else:
            return False

    def fetch_milestone(self, issue):
        return self.fetch_issue_events(issue, 'milestoned')

    def file_at_commit(self, sha, filename):
        url = "%s/%s/%s/%s" % (self.owner, self.repo, sha, filename)
        contents = self.fetch_raw(url)
        return contents.content

    def get_repo_contents(self, path):
        contents = self.fetch_endpoint('contents/{0}'.format(path))
        return contents.content

    def parse_by_key(self, data, key, match):
        i = 0
        matches = list()
        while i < len(data):
            if data[i].get(key).startswith(match):
                matches.append(data[i].get(key))
            i = i+1
        return matches
