from lib.git_parse import GitHub
from lib.fetch import Fetch
class Drafts():
    def __init__(self):
        self.fetch = Fetch('')
        self.drafts_api = GitHub('blog_drafts', '18F')

    def fetch_all(self, ):
        gh = self.drafts_api
        issues = gh.fetch_issues()
        if issues:
            self.fetch.save_data(issues, '_data/issues.json')
        else:
            import pdb; pdb.set_trace()

    def fetch_events(self, number, part=None, name=None):
        gh = self.drafts_api
        fetch = Fetch('')
        events = gh.fetch_issue_events(number, part)
        if events:
            fetch.save_data(events, '_data/events-%s.json' % number )

    def fetch_milestone(self, i):
        gh = self.drafts_api
        fetch = Fetch('')
        milestones = gh.fetch_milestone(i)
        if milestones:
            fetch.save_data(milestones, '_data/issue-%s-milestones.json' % i)
