import calendar
from datetime import date, datetime
from . import db
from .utils import to_python_datetime


author_months = db.Table('author_months',
    db.Column('month_begin', db.Integer, db.ForeignKey('month.begin')),
    db.Column('author_id', db.Integer, db.ForeignKey('author.id'))
    )


class Month(db.Model):
    begin = db.Column(db.Date(), primary_key=True)
    authors = db.relationship('Author', secondary=author_months,
        backref=db.backref('months', lazy='dynamic'))

    def __str__(self):
        return '{0}-{1}'.format(self.begin.year, self.begin.month)

    @classmethod
    def get_or_create(cls, first_day):
        return cls.query.get(first_day) or cls(begin=first_day)

    def next(self):
        if self.begin.month == 12:
            next_begin = date(self.begin.year+1, 1, 1)
        else:
            next_begin = date(self.begin.year, self.begin.month+1, 1)
        return self.get_or_create(next_begin)

    def end(self):
        last_day = calendar.monthrange(self.begin.year, self.begin.month)[1]
        return date(self.begin.year, self.begin.month, last_day)

    def author_list_is_complete(self):
        GithubQueryLog.last_query_datetime('authors').date() > self.end()


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String())
    first_name = db.Column(db.String())
    last_name = db.Column(db.String())
    full_name = db.Column(db.String())
    url = db.Column(db.String(), nullable=True)

    @classmethod
    def from_gh_data(cls, username, dct):
        "Finds and updates, or creates, instance based on ``from_gh_data``."
        author = cls.query.filter_by(username=username).first()
        if author:
            for field in ('first_name', 'last_name', 'full_name', 'url'):
                setattr(author, field, dct.get(field))
        else:
            author = cls(username=username, **dct)
        return author


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
    def was_fetched_today(cls, query_type):
        return (cls.last_query_datetime(query_type).date() >=
                datetime.today().date())

    @classmethod
    def log(cls, query_type):
        qlog = cls.query.filter_by(query_type=query_type).first()
        if qlog:
            qlog.queried_at = datetime.now()
        else:
            qlog = cls(query_type=query_type, queried_at=datetime.now())
        db.session.add(qlog)


labels_issues = db.Table('labels_issues',
    db.Column('label_id', db.Integer, db.ForeignKey('label.id')),
    db.Column('issue_id', db.Integer, db.ForeignKey('issue.id'))
    )


class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    url = db.Column(db.String())
    color = db.Column(db.String(), nullable=True)


class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    commit_id = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.DateTime(), default=datetime.now)
    url = db.Column(db.String())
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'))

    @classmethod
    def from_dict(cls, milestone_data):
        "Given dict of milestone data fetched from GitHub API, return instance"
        return cls(id=milestone_data['id'],
            title=milestone_data['milestone']['title'],
            commit_id=milestone_data.get('commit_id'),
            created_at=to_python_datetime(milestone_data.get('created_at')),
            url=milestone_data.get('url'),
            )


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
    created_at = db.Column(db.DateTime(), default=datetime.now)
    updated_at = db.Column(db.DateTime(), default=datetime.now)
    closed_at = db.Column(db.DateTime(), nullable=True)
    labels = db.relationship('Label', secondary=labels_issues,
        backref=db.backref('issues', lazy='dynamic'))
    milestones = db.relationship('Milestone')

    @classmethod
    def from_dict(cls, issue_data):
        "Given dict of issue data fetched from GitHub API, return instance"
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
            'updated_at': to_python_datetime(issue_data['updated_at']),
            'created_at': to_python_datetime(issue_data['created_at']),
            'closed_at': to_python_datetime(issue_data['closed_at']),
            }
        return cls(**insertable)
