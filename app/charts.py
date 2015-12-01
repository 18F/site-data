import datetime

from bokeh.embed import components
from bokeh.models import ColumnDataSource, OpenURL, TapTool, HoverTool
from bokeh.plotting import figure
from bokeh.charts import Bar, Histogram
from pandas import DataFrame

from .models import (Author, Issue, Month)

WIDTH = 800
HEIGHT = 400
TODAY = datetime.date.today()
THICKNESS = 3
MARGIN = 6
TOOLS = "pan,box_zoom,reset"


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


def n_authors_by_location():
    "chart of cumulative # of authors per month, by location category."

    data = DataFrame({'authors': a.full_name,
                      'location': a.duty_station.group,
                      'month': m.begin} for (a, m) in Month.all_authors())
    bar = Bar(data,
              label='month',
              values='authors',
              agg='count',
              stack='location',
              legend='top_left',
              title='Published authors by month (cumulative)')
    return components(bar)


def n_posts_histogram():

    title = '18F team members by number of posts'
    data = DataFrame({'authors': a.full_name,
                      'posts': a.posts.count()} for a in Author.query)
    histogram = Histogram(data, 'posts', title=title)
    # not working
    # histogram.add_tools(HoverTool(tooltips=[('posts', '@posts'), ('members', '@authors')]))
    return components(histogram)
