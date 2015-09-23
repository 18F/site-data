from lib.git_parse import GitHub
from lib.fetch import Fetch
class Drafts():
    def fetch_all(self, ):
        drafts_api = GitHub('blog-drafts', '18F')
        fetch = Fetch('')
        issues = drafts_api.fetch_issues()
        if issues:
            fetch.save_data(issues, '_data/issues.json')
        else:
            print "GitHub could not be reached for comment"

    def fetch_events(self, number, part=None, name=None):
        gh = GitHub('blog-drafts', '18F')
        fetch = Fetch('')
        events = gh.fetch_issue_events(number, part)
        if events:
            fetch.save_data(events, '_data/events-%s.json' % number )

    def fetch_milestone(self, i):
        gh = GitHub('blog-drafts', '18F')
        fetch = Fetch('')
        milestones = gh.fetch_milestone(i)
        if milestones:
            fetch.save_data(milestones, '_data/issue-%s-milestones.json' % i)
        else:
            print "GitHub could not be reached for comment. %s" % milestones
