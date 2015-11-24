import datetime

import pygal
from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool, OpenURL, TapTool
from bokeh.plotting import figure

from .models import (Author, Issue, Month)

WIDTH = 800
HEIGHT = 400
TODAY = datetime.date.today()
THICKNESS = 3
MARGIN = 6
TOOLS = "pan,box_zoom,reset"

chart_style = dict(explicit_size=True,
                   style=pygal.style.DarkGreenBlueStyle,
                   x_label_rotation=70,
                   x_labels_major_every=3,
                   show_minor_x_labels=False, )


def issue_lifecycles(data=None):
    "Returns (script, div) tuple of Bokeh chart of Issue status."
    if data is None:
        issues = Issue.query
    issues = issues.order_by(Issue.created_at)
    milestones = []
    for (row, issue) in enumerate(issues):
        milestones.extend((row, m)
                          for m in issue.milestones_for_chart() if m.state)
    y = [m[0] * (THICKNESS + MARGIN) for m in milestones]
    x = [m[1].created_at for m in milestones]
    end_angle = [m[1].arclength for m in milestones]
    color = [m[1].color for m in milestones]
    source = ColumnDataSource(data=dict(
        x=x,
        y=y,
        color=color,
        end_angle=end_angle,
        url=[m[1].issue.html_url for m in milestones],
        issue=[m[1].issue.title for m in milestones],
        status=[m[1].title for m in milestones],
        alpha=[m[1].opacity for m in milestones],
        date=[m[1].created_at.strftime("%b %d") for m in milestones],
        created=[m[1].issue.created_at.strftime("%b %d") for m in milestones],
        assignee=[m[1].issue.assignee.full_name if m[1].issue.assignee else ''
                  for m in milestones],
        x0=x,
        y0=[p - THICKNESS for p in y],
        y1=[p + THICKNESS for p in y],
        x1=[m[1].created_at if m[1].is_terminal else (m[1].next(
        ).created_at if m[1].next() else TODAY) for m in milestones]))

    hover = HoverTool(tooltips=[("issue", "@issue"),
                                ("date", "@date"),
                                ("status", "@status"),
                                ("assignee", "@assignee"), ])

    fig = figure(x_axis_type='datetime', title='Issue progress', tools=TOOLS)
    fig.yaxis.major_label_text_color = None
    fig.wedge('x',
              'y',
              source=source,
              radius=10,
              direction='anticlock',
              radius_units='screen',
              start_angle=0,
              end_angle='end_angle',
              color='color',
              alpha='alpha')
    fig.quad(left='x0',
             bottom='y0',
             right='x1',
             top='y1',
             source=source,
             color='color',
             alpha='alpha')
    fig.add_tools(hover)
    taptool = fig.select(type=TapTool)
    taptool.callback = OpenURL(url="@url")

    return components(fig)


def n_authors():
    """PyGal chart of cumulative number of authors per month."""

    author_count = [(str(m), len(m.authors)) for m in Month.non_empty()]
    title = 'Cumulative author count, by month'
    bar_chart = pygal.Bar(title=title, **chart_style)
    bar_chart.x_labels = [ac[0] for ac in author_count]
    bar_chart.add('Author count', [ac[1] for ac in author_count])
    return bar_chart


def n_authors_by_location():
    "PyGal chart of cumulative # of authors per month, by location category."

    title = 'Cumulative author count, by month and location'
    bar_chart = pygal.StackedBar(title=title, **chart_style)
    bar_chart.x_labels = [str(m) for m in Month.non_empty()]
    for loc in ('DC', 'SF', 'OTHER'):
        count = [m[1] for m in Month.author_count_by_location(loc, True)]
        bar_chart.add(loc, count)
    return bar_chart


def n_posts_histogram():

    title = '18F team members by number of posts'
    bar_chart = pygal.StackedBar(title=title,
                                 x_label_rotation=70,
                                 style=pygal.style.DarkGreenBlueStyle, )

    data = Author.authorship_histogram()
    bar_chart.x_labels = [k[2:].replace('_', ' ') for k in data.keys()]
    bar_chart.add('Team members', data.values())
    return bar_chart


def n_authors_by_team():

    title = 'Number of posts per member by team'
    bar_chart = pygal.Bar(title=title,
                          x_label_rotation=70,
                          style=pygal.style.DarkGreenBlueStyle, )

    data = Author.authorship_histogram_by_team()
    for row in data:
        bar = [{'value': len(v or []),
                'label': ', '.join(v or [])} for v in row[1:]]
        bar_chart.add(row[0], bar)
    bar_chart.x_labels = [k[2:].replace('_', ' ') for k in row.keys()[1:]]
    return bar_chart
