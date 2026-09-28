import packaging.version

# ---------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------

project = "Flask"

# We are building a pinned Flask release, so we don't need
# pallets_sphinx_themes.get_version().
version = "3.1.3"
release = "3.1.3"

copyright = "2010 Pallets"
author = "Pallets"


# ---------------------------------------------------------------------
# General
# ---------------------------------------------------------------------

default_role = "code"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.log_cabinet",
    "sphinx_tabs.tabs",
]

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True


# ---------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------

extlinks = {
    "issue": (
        "https://github.com/pallets/flask/issues/%s",
        "#%s",
    ),
    "pr": (
        "https://github.com/pallets/flask/pull/%s",
        "#%s",
    ),
    "ghsa": (
        "https://github.com/pallets/flask/security/advisories/GHSA-%s",
        "GHSA-%s",
    ),
}


# ---------------------------------------------------------------------
# Intersphinx
# ---------------------------------------------------------------------

intersphinx_mapping = {
    "python": (
        "https://docs.python.org/3/",
        None,
    ),
    "werkzeug": (
        "https://werkzeug.palletsprojects.com/",
        None,
    ),
    "click": (
        "https://click.palletsprojects.com/",
        None,
    ),
    "jinja": (
        "https://jinja.palletsprojects.com/",
        None,
    ),
    "itsdangerous": (
        "https://itsdangerous.palletsprojects.com/",
        None,
    ),
    "sqlalchemy": (
        "https://docs.sqlalchemy.org/",
        None,
    ),
    "wtforms": (
        "https://wtforms.readthedocs.io/",
        None,
    ),
    "blinker": (
        "https://blinker.readthedocs.io/",
        None,
    ),
}


# ---------------------------------------------------------------------
# Local Flask GitHub role
# ---------------------------------------------------------------------

def github_link(
    name,
    rawtext,
    text,
    lineno,
    inliner,
    options=None,
    content=None,
):
    """
    Resolve Flask's :gh: role to a GitHub URL.
    """

    app = inliner.document.settings.env.app
    release = app.config.release

    base_url = "https://github.com/pallets/flask/tree/"

    if text.endswith(">"):
        words, text = text[:-1].rsplit("<", 1)
        words = words.strip()
    else:
        words = None

    if packaging.version.parse(release).is_devrelease:
        url = f"{base_url}main/{text}"
    else:
        url = f"{base_url}{release}/{text}"

    if words is None:
        words = url

    from docutils.nodes import reference
    from docutils.parsers.rst.roles import set_classes

    options = options or {}
    set_classes(options)

    node = reference(
        rawtext,
        words,
        refuri=url,
        **options,
    )

    return [node], []


def setup(app):
    app.add_role("gh", github_link)
