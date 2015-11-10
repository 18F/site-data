import calendar
import requests
from functools import total_ordering
from datetime import date, datetime
import yaml
from . import db
from lib.utils import to_py_date
from lib.git_parse import drafts_api, site_api, hub_api

author_months = db.Table(
    'author_months',
    db.Column('month_begin', db.Date(), db.ForeignKey('month.begin')),
    db.Column('author_id', db.Integer, db.ForeignKey('author.id')))


@total_ordering
class Month(db.Model):
    begin = db.Column(db.Date(), primary_key=True)
    authors = db.relationship('Author',
                              secondary=author_months,
                              backref=db.backref('months',
                                                 lazy='dynamic'),
                              collection_class=set)

    def __str__(self):
        return '{0}-{1}'.format(self.begin.year, self.begin.month)

    @classmethod
    def non_empty(cls):
        return cls.query.filter(cls.authors)

    @classmethod
    def author_count_by_location(cls, location):
        return [(str(m),
                 len([a
                      for a in m.authors
                      if a.duty_station and a.duty_station.group == location]))
                for m in cls.non_empty()]

    @classmethod
    def get_or_create(cls, first_day):
        return cls.query.get(first_day) or cls(begin=first_day)

    def next(self):
        if self.begin.month == 12:
            next_begin = date(self.begin.year + 1, 1, 1)
        else:
            next_begin = date(self.begin.year, self.begin.month + 1, 1)
        return self.get_or_create(next_begin)

    def end(self):
        last_day = calendar.monthrange(self.begin.year, self.begin.month)[1]
        return date(self.begin.year, self.begin.month, last_day)

    def author_list_is_complete(self):
        GithubQueryLog.last_query_datetime('authors').date() > self.end()

    def __eq__(self, other):
        return self.begin == other.begin

    def __gt__(self, other):
        return self.begin > other.begin

    def _date_range(self):
        month_begin = "{0}-01".format(self)
        month_end = "{0}-{1}".format(self, self.end().day)
        return {"since": month_begin, "until": month_end}

    def fetch_authors(self):
        "Fetches from github blog authors as of this month"
        commits = site_api.fetch_commits(self._date_range())
        if commits:
            authors = yaml.load(site_api.file_at_commit(commits[0]['sha'],
                                                        '_data/authors.yml'))
        return authors or {}

    @classmethod
    def create_missing(cls):
        "Populate DB with all months up to today, including their authors."
        FIRST_MONTH_OF_BLOG = date(2014, 3, 1)
        month = cls.get_or_create(FIRST_MONTH_OF_BLOG)
        while month.begin <= date.today():
            db.session.add(month)
            if (not month.authors) or (not month.author_list_is_complete()):
                for (username, author_data) in month.fetch_authors().items():
                    month.authors.add(Author.from_api_data(username,
                                                           author_data))
            month = month.next()
        db.session.commit()

    def __eq__(self, other):
        return self.begin == other.begin

    def __gt__(self, other):
        return self.begin > other.begin

    # other comparison operators automagically inferred by `total_ordering`

    def _date_range(self):
        month_begin = "{0}-01".format(self)
        month_end = "{0}-{1}".format(self, self.end().day)
        return {"since": month_begin, "until": month_end}


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    authors = db.relationship('Author',
                              cascade='all, delete-orphan',
                              backref='team')


class DutyStation(db.Model):
    airport_code = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timezone = db.Column(db.Text, nullable=False)
    authors = db.relationship('Author',
                              collection_class=set,
                              backref='duty_station')

    @classmethod
    def fill(cls):
        data = hub_api.yaml('_data/locations.yml', 1)
        for d in data:
            if not cls.query.get(d['code']):
                d['airport_code'] = d.pop('code')
                d['name'] = d.pop('label')
                db.session.add(cls(**d))
        db.session.commit()

    def __str__(self):
        return self.airport_code

    _groups = {'DCA': 'DC', 'SFO': 'SF'}

    @property
    def group(self):
        return self._groups.get(self.airport_code, 'OTHER')


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String())  # in github
    first_name = db.Column(db.String())
    last_name = db.Column(db.String())
    full_name = db.Column(db.String())
    url = db.Column(db.String(), nullable=True)
    pronouns = db.Column(db.String(), nullable=True)
    airport_code = db.Column(db.String(),
                             db.ForeignKey('duty_station.airport_code'))
    team_id = db.Column(db.Integer(), db.ForeignKey('team.id'))

    def __init__(self, *arg, **kwarg):
        super(Author, self).__init__(*arg, **kwarg)
        self.lookup_duty_station()
        self.lookup_team()

    def lookup_duty_station(self):
        "Query Hub for an author's airport code"
        data = hub_api.yaml('_data/team/{0}.yml'.format(self.username), 1)
        self.airport_code = data.get('location')

    def lookup_team(self):
        "Query 18F website for an author's team in 18F"
        data = site_api.yaml('_team/{0}.md'.format(self.username), 1)
        team_name = data.get('team')
        if team_name:
            team = Team.query.filter_by(name=team_name).first() or Team(
                name=team_name)
            db.session.add(team)
            self.team = team

    @classmethod
    def from_api_data(cls, username, dct):
        "Finds and updates, or creates, instance based on API result."
        author = cls.query.filter_by(username=username).first()
        if author:
            for field in ('first_name', 'last_name', 'full_name', 'url'):
                setattr(author, field, dct.get(field))
        else:
            author = cls(username=username, **dct)
        return author

    @classmethod
    def fetch(cls):
        "Query 18F website API, creating Author instances for each blog author"
        Month.create_missing()
        response = requests.get('https://18f.gsa.gov/api/data/authors.json')
        for (username, author_data) in response.json().items():
            author = cls.from_api_data(username, author_data)
            db.session.add(author)
        GithubQueryLog.log('authors')
        db.session.commit()


class GithubQueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_type = db.Column(db.String(), unique=True, nullable=False)
    queried_at = db.Column(db.DateTime(), default=datetime.now)

    @classmethod
    def last_query_datetime(cls, query_type):
        qlog = cls.query.filter_by(query_type=query_type).first()
        if qlog:
            return qlog.queried_at
        else:
            return datetime.fromtimestamp(0)

    @classmethod
    def log(cls, query_type):
        qlog = cls.query.filter_by(query_type=query_type).first()
        if qlog:
            qlog.queried_at = datetime.now()
        else:
            qlog = cls(query_type=query_type, queried_at=datetime.now())
        db.session.add(qlog)


labels_issues = db.Table(
    'labels_issues',
    db.Column('label_id', db.Integer, db.ForeignKey('label.id')),
    db.Column('issue_id', db.Integer, db.ForeignKey('issue.id')))


class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    url = db.Column(db.String())
    color = db.Column(db.String(), nullable=True)

    @classmethod
    def get_or_create(cls, label_data):
        label = cls.query.filter_by(name=label_data['name']).first() \
                or cls(**label_data)
        return label


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commit_id = db.Column(db.Integer)
    url = db.Column(db.String())
    actor = db.Column(db.String())
    event = db.Column(db.String())
    created_at = db.Column(db.Date())
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))

    @classmethod
    def from_gh_data(cls, event_data):
        "Given dict of event data fetched from GitHub API, return instance"
        return cls(id=event_data['id'],
                   commit_id=event_data['commit_id'],
                   url=event_data['url'],
                   actor=event_data['actor']['login'],
                   event=event_data['event'],
                   created_at=to_py_date(event_data.get('created_at')), )


class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    commit_id = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.Date(), default=date.today)
    url = db.Column(db.String())
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))

    @classmethod
    def from_gh_data(cls, milestone_data):
        "Given dict of milestone data fetched from GitHub API, return instance"
        return cls(id=milestone_data['id'],
                   title=milestone_data['milestone']['title'],
                   commit_id=milestone_data.get('commit_id'),
                   created_at=to_py_date(milestone_data.get('created_at')),
                   url=milestone_data.get('url'), )


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    title = db.Column(db.String())
    body = db.Column(db.String())
    state = db.Column(db.String())
    # user = db.Column(db.String())
    comments = db.Column(db.String())
    locked = db.Column(db.Boolean)
    # assignee
    url = db.Column(db.String(), nullable=True)
    events_url = db.Column(db.String(), nullable=True)
    labels_url = db.Column(db.String(), nullable=True)
    comments_url = db.Column(db.String(), nullable=True)
    html_url = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.Date(), default=date.today)
    updated_at = db.Column(db.Date(), default=date.today)
    closed_at = db.Column(db.Date(), nullable=True)
    labels = db.relationship('Label',
                             secondary=labels_issues,
                             backref=db.backref('issues',
                                                lazy='dynamic'))
    milestones = db.relationship('Milestone', cascade='all, delete-orphan')
    events = db.relationship('Event', cascade='all, delete-orphan')

    @classmethod
    def from_gh_data(cls, issue_data):
        """Given dict of issue data fetched from GitHub API, return instance.

        If the issue already exists, delete it (and its milestones)
        and replace it."""
        issue = cls.query.filter_by(number=issue_data.get('number')).first()
        if issue:
            db.session.delete(issue)
        db.session.commit()
        insertable = {
            'id': issue_data.get('id'),
            'number': issue_data.get('number'),
            'title': issue_data.get('title'),
            'state': issue_data.get('state'),
            'body': issue_data.get('body'),
            'locked': issue_data.get('locked'),
            'url': issue_data.get('url'),
            'labels_url': issue_data.get('labels_url'),
            'html_url': issue_data.get('html_url'),
            'events_url': issue_data.get('events_url'),
            'updated_at': to_py_date(issue_data['updated_at']),
            'created_at': to_py_date(issue_data['created_at']),
            'closed_at': to_py_date(issue_data['closed_at']),
        }
        issue = cls(**insertable)
        for label_data in issue_data['labels']:
            issue.labels.append(Label.get_or_create(label_data))
        db.session.add(issue)
        db.session.commit()
        return issue

    @classmethod
    def fetch(cls, since):
        issues = drafts_api.fetch_issues(since=since)
        for issue_data in issues:
            issue = cls.from_gh_data(issue_data)
            milestones = drafts_api.fetch_milestone(issue.number)
            for milestone_data in milestones:
                issue.milestones.append(Milestone.from_gh_data(milestone_data))
            events = drafts_api.fetch_issue_events(issue.number)
            for event_data in events:
                issue.events.append(Event.from_gh_data(event_data))
        GithubQueryLog.log('issues')
        db.session.commit()


def update_db_from_github(refresh_timedelta):
    """Refresh author and issue data from Github / 18f API.

    Args:
        refresh_timedelta: Pull from each data source only if the last pull
            was at least this long ago.
    """
    DutyStation.fill()
    last_query = GithubQueryLog.last_query_datetime('authors')
    if (datetime.now() - last_query) > refresh_timedelta:
        Author.fetch()
    last_query = GithubQueryLog.last_query_datetime('issues')
    if (datetime.now() - last_query) > refresh_timedelta:
        Issue.fetch(since=last_query)
