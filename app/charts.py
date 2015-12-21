import datetime

from bokeh.embed import components
from bokeh.models import ColumnDataSource, OpenURL, TapTool, HoverTool
from bokeh.plotting import figure
from bokeh.charts import Bar, Histogram
from pandas import DataFrame

from .models import (Author, Month)
from .github_issue_lifecycles.app.charts import lifecycles

WIDTH = 800
HEIGHT = 400
TODAY = datetime.date.today()
THICKNESS = 3
MARGIN = 6
TOOLS = "pan,box_zoom,reset"


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
