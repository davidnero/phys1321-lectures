__version__ = "2022.1"

import re
import io
import contextlib
import numpy as np
import matplotlib.pyplot as plt
import IPython
from IPython import get_ipython
from IPython.core.magic import register_line_magic, register_cell_magic
from IPython.display import HTML, display, YouTubeVideo


####################################################################################################
# Color Definitions (change these if you like)
####################################################################################################

GRADED_CELL_COLOR = "lavender"
TEST_BLANK_COLOR = "lightyellow"
TEST_PASSED_COLOR = "lightgreen"
TEST_FAILED_COLOR = "pink"


####################################################################################################
# Restore Default Settings for matplotlib
####################################################################################################

# this won't be needed anymore once matplotlib-inline updates to 0.1.4
# beware that matplotlib 3.5.2 has a bug that delays rc updates until after first plot is created
from matplotlib import rcdefaults
rcdefaults()


####################################################################################################
# Patch Functions
####################################################################################################

# globals to hold cell contents and outputs
_LAST_IN = _LAST_OUT = ""
_LAST_PLOT = None
_LAST_DISPLAY = []


# wrap show() to grab a copy of a figure before it's closed
_old_show = plt.show
def _new_show(*args, **kwargs):
    global _LAST_PLOT
    _LAST_PLOT = plt.gcf()
    _old_show(*args, **kwargs)


# wrap print() to grab a copy of whatever is printed
_old_print = print
def _new_print(*args, **kwargs):
    global _LAST_OUT
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        _old_print(*args, **kwargs)
    _LAST_OUT += out.getvalue()
    _old_print(*args, **kwargs)


# wrap display() to grab the text representation of rich output objects
_old_display = IPython.display.display
def _new_display(*args, **kwargs):
    global _LAST_DISPLAY
    _LAST_DISPLAY += args
    _old_display(*args, **kwargs)


####################################################################################################
# Magic Commands
####################################################################################################

@register_line_magic
def background(color):
    """
    Change the background color of a code cell.
    """
    js = (
        "var cell = this.closest('.jp-CodeCell');"
        "if (cell) {"
        "    var input_area = cell.querySelector('.jp-Editor');"
        "} else {"
        "    var cell = this.closest('.cell');"
        "    var input_area = cell.querySelector('.input_area');"
        "}"
        f"input_area.style.background='{color}';"
        "this.parentNode.removeChild(this);"
        )
    display(HTML(f'<img src onerror="{js}">')) # Such hackery. Much javascript.


@register_line_magic
def video(youtube_id):
    """
    Display a YouTube video.
    """
    display(YouTubeVideo(youtube_id, 720, 480, rel=0))


@register_line_magic
def download(url):
    """
    Download a file, or use a local copy if it exists. Local files are searched for in the working
    directory and in "~/phys1321 files" (to allow grading when offline).
    """
    system_folder = "phys1321 files"
    import pathlib, shutil
    from urllib.request import urlretrieve
    from urllib.parse import urlparse, unquote

    filename = unquote(urlparse(url).path.split("/")[-1])
    system_path = pathlib.Path.home() / system_folder / filename

    if pathlib.Path(filename).exists(): # local copy already exists
        print(f"Using local copy of {filename}")
    elif system_path.exists():
        print(f"Using system copy of {filename}")
        shutil.copy(system_path, ".") # copy system copy to working folder
    else:
        print(f"Downloading {filename}")
        urlretrieve(url, filename) # download from url


@register_cell_magic
def graded(line, cell):
    """
    Store input and output for testing. Also changes the background color.
    """
    global _LAST_IN, _LAST_OUT, _LAST_PLOT, _LAST_DISPLAY
    background(GRADED_CELL_COLOR)
    _LAST_IN = cell
    _LAST_PLOT = None # should only exist if this cell makes one
    _LAST_DISPLAY = [] # clear
    _LAST_OUT = "" # reset print buffer

    # monkey patch show, display, and print
    plt.show = _new_show
    IPython.display.display = _new_display
    get_ipython().user_ns["print"] = _new_print # print = _new_print won't work

    # run the cell
    get_ipython().run_cell(cell)

    # restore patched functions
    plt.show = _old_show # restore
    IPython.display.display = _old_display
    get_ipython().user_ns["print"] = _old_print


@register_cell_magic
def tests(line, cell):
    """
    This cell runs tests. Change the background color based on the result.
    """
    no_code = True
    for line in _LAST_IN.split("\n"):
        # lines that include just white space, full line comments, or empty cells are fine,
        # otherwise it's considered code
        if not re.match(r"\s+|\s*#.*|^$", line): no_code = False
    if no_code:
        background(TEST_BLANK_COLOR)
        print("Nothing to test yet...")
    else:
        result = get_ipython().run_cell(cell) # result = True if there are no errors
        if result.success:
            background(TEST_PASSED_COLOR)
            print("All tests passed!")
        else:
            background(TEST_FAILED_COLOR)


####################################################################################################
# Tests
####################################################################################################

def equal(A, B):
    """
    Check that A = B.
    """
    np.testing.assert_equal(A, B)


def similar(A, B, rtol=0.01, atol=1e-12):
    """
    Check that A = B with tolerance atol + rtol*B.
    """
    np.testing.assert_allclose(A, B, rtol=rtol, atol=atol)


def code_contains(*args, forbidden=False):
    """
    Check that <args> appear in the previous graded cell.
    If forbidden, check that <args> do NOT appear.
    """
    for arg in args:
        match = re.search(arg, _LAST_IN)
        if not match:
            if not forbidden:
                raise AssertionError(f"The previous cell doesn't include '{arg}'.")
        else:
            if forbidden:
                raise AssertionError(f"The previous cell contains a forbidden string: '{match.group()}'.")


def printed(*args):
    """
    Check that <args> were printed by previous graded cell.
    """
    for arg in args:
        if not re.search(str(arg), _LAST_OUT):
            raise AssertionError(f"Printed output doesn't contain '{arg}'.")


def get_plot():
    """
    Return the figure object from the last graded cell.
    """
    return _LAST_PLOT


def plot_shown():
    """
    Check that previous graded cell created a plot.
    """
    assert _LAST_PLOT, "Plot missing. Did you use plt.show()?"


def plot_has(*args):
    """
    Check that previous graded cell created a plot with all of the <args> set.
    <args> are strings like "title" or "legend".

    Note: This function only checks the most recent figure. If you need to show
    more than one plot from a single cell, use subplots. This will also break if
    you .close() the figure before this test is run.
    """
    assert _LAST_PLOT, "Plot missing. Did you use plt.show()?"

    for arg in args:
        found = False
        for ax in _LAST_PLOT.axes:
            if hasattr(ax, "get_" + arg):
                if getattr(ax, "get_" + arg)():
                    found = True
        assert found, f"'{arg}' was not set for plot"


def plot_snapshot():
    """
    Print the state of the plot from the previous graded cell.
    """
    assert _LAST_PLOT, "Plot missing. Did you use plt.show()?"

    def inspect(obj, depth=0):
        if hasattr(obj, "get_children"):
            children = getattr(obj, "get_children")()
            for child in children:
                print("\t" * depth, child, sep="")
                inspect(child, depth+1)

    inspect(_LAST_PLOT)


def animation_shown():
    """
    Check that previous graded cell created an animation.

    Note: This function requires that display(video_as_html) was called
    """
    found = False
    for d in _LAST_DISPLAY:
        if hasattr(d, "data"):
            if "</video>" in d.data:
                found = True
    assert found, "Animation missing. Did you show it with display()?"


def widget_snapshot():
    """
    Display widget's current state for manual grading

    Note: This function requires that display(widget) was called
    """
    # prints string representation of EVERYTHING that was displayed
    for widget in _LAST_DISPLAY:
        s = str(widget)
        matches = re.findall(r"outputs=\(.*?\)", s)
        for match in matches:
            s = s.replace(match, "")
        print(s)


def widget_has(*args):
    """
    Check that widget is contains <args>, where <args> are strings like
    "IntSlider" or "HBox".

    Note: This function requires that display(widget) was called
    """
    for arg in args:
        match = re.search(arg, str(_LAST_DISPLAY))
        assert match, f"Widget property '{arg}' not found.  Did you use display()?"