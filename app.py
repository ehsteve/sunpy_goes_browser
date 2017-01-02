"""
A web app to browse GOES data
"""

import flask

from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.layouts import Column
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models import ColumnDataSource, CustomJS, HoverTool

import sunpy.lightcurve as lc
from sunpy.time import TimeRange, parse_time

import datetime

app = flask.Flask(__name__)

# set some defaults
DEFAULT_TR = TimeRange(['2011-06-07 00:00', '2011-06-07 12:00'])
PLOT_HEIGHT = 300
PLOT_WIDTH = 900
TOOLS = 'pan,box_zoom,box_select,crosshair,undo,redo,save,reset'
ONE_HOUR = datetime.timedelta(seconds=60*60)
ONE_DAY = datetime.timedelta(days=1)

formatter = DatetimeTickFormatter(hours="%F %H:%M")

#stats = PreText(text='', width=PLOT_WIDTH)

goes = lc.GOESLightCurve.create(DEFAULT_TR)
# add time string for display of hover tool
goes.data['time_str'] = goes.data.index.strftime('%F %H:%M:%S')
source = ColumnDataSource(data=goes.data)
source_static = ColumnDataSource(data=goes.data)

@app.route("/")
def index():
    """ Very simple embedding of a lightcurve chart
    """
    # FLASK
    # Grab the inputs arguments from the URL
    # This is automated by the button
    args = flask.request.args
    _from = str(args.get('_from', str(DEFAULT_TR.start)))
    _to = str(args.get('_to', str(DEFAULT_TR.end)))

    tr = TimeRange(parse_time(_from), parse_time(_to))

    if 'next' in args:
        tr = tr.next()

    if 'prev' in args:
        tr = tr.previous()

    if 'next_hour' in args:
        tr = TimeRange(tr.start + ONE_HOUR, tr.end + ONE_HOUR)

    if 'next_day' in args:
        tr = TimeRange(tr.start + ONE_DAY, tr.end + ONE_DAY)

    if 'prev_hour' in args:
        tr = TimeRange(tr.start - ONE_HOUR, tr.end - ONE_HOUR)

    if 'prev_day' in args:
        tr = TimeRange(tr.start - ONE_DAY, tr.end - ONE_DAY)

    _from = str(tr.start)
    _to = str(tr.end)

    # get the data
    goes = lc.GOESLightCurve.create(tr)
    # resample to reduce the number of points for debugging
    goes.data = goes.data.resample("1T").mean()
    # add time string for display of hover tool
    goes.data['time_str'] = goes.data.index.strftime('%F %H:%M:%S')
    source = ColumnDataSource(data=goes.data)
    source_static = ColumnDataSource(data=goes.data)

    # now create the bokeh plots
    # XRS-B Plot
    fig1 = figure(title="GOES", tools=TOOLS, plot_height=PLOT_HEIGHT, width=PLOT_WIDTH, x_axis_type='datetime', y_axis_type="log"
                , y_range=(10**-9, 10**-2), toolbar_location="right")
    fig1.xaxis.formatter = formatter
    fig1.line('index', 'xrsb', source=source_static, color='red', line_width=2, legend="xrsa 1-8 Angstrom")

    fig2 = figure(title="GOES", tools=TOOLS, plot_height=PLOT_HEIGHT, width=PLOT_WIDTH, x_axis_type='datetime', y_axis_type="log"
                , y_range=(10**-9, 10**-2))
    fig2.xaxis.formatter = formatter
    fig2.line('index', 'xrsa', source=source_static, color='blue', line_width=2, legend="xrsa 0.5-4.0 Angstrom")

    # link the x-range for common panning
    fig2.x_range = fig1.x_range

    fig = Column(fig1, fig2)

    source_static.callback = CustomJS(code="""
        var inds = cb_obj.selected['1d'].indices;
        var d1 = cb_obj.data;
        var m = 0;

        if (inds.length == 0) { return; }

        for (i = 0; i < inds.length; i++) {
            d1['color'][inds[i]] = "red"
            if (d1['y'][inds[i]] > m) { m = d1['y'][inds[i]] }
        }
        console.log(m);
        cb_obj.trigger('change');
    """)

    hover = HoverTool()
    hover.tooltips  = [
        ("time", "@time_str"),
        ("xrsb", "@xrsb"),
        ("xrsa", "@xrsa")
    ]

    fig1.add_tools(hover)

    hover2 = HoverTool()
    hover2.tooltips  = [
        ("time", "@time_str"),
        ("xrsb", "@xrsb"),
        ("xrsa", "@xrsa")
    ]
    fig2.add_tools(hover2)

    # Configure resources to include BokehJS inline in the document.
    # For more details see:
    #   http://bokeh.pydata.org/en/latest/docs/reference/resources_embedding.html#bokeh-embed
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # For more details see:
    #   http://bokeh.pydata.org/en/latest/docs/user_guide/embedding.html#components
    script, div = components(fig, INLINE)
    html = flask.render_template(
        'embed.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
        _from=_from,
        _to=_to,
    )
    return encode_utf8(html)

if __name__ == "__main__":
    print(__doc__)
    app.run(debug=True)
