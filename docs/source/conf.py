# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from pathlib import Path
from urllib.parse import quote

from docutils import nodes
from sphinx import addnodes

sys.path.insert(0, os.path.abspath("../../"))

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


# -- Project information -----------------------------------------------------

project = "spectree"
copyright = "2020, Keming Yang"
author = "Keming Yang"


# -- General configuration ---------------------------------------------------
autodoc_class_signature = "separated"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.githubpages",
    "myst_parser",
    "sphinx_sitemap",
]

# myst
myst_enable_extensions = [
    "tasklist",
    "fieldlist",
    "colon_fence",
    "replacements",
    "substitution",
    "smartquotes",
    "html_admonition",
    "deflist",
]
myst_heading_anchors = 3

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []
source_suffix = [".rst", ".md"]
language = "en"
html_baseurl = "https://0b01001001.github.io/spectree/"
html_extra_path = ["robots.txt"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "shibuya"
html_theme_options = {
    "og_image_url": "https://repository-images.githubusercontent.com/225120376/c3469400-c16d-11ea-9498-093594983a5a",
    "nav_links": [
        {
            "title": "Sponsor me",
            "url": "https://github.com/sponsors/kemingy",
        },
    ],
}
html_context = {
    "source_type": "github",
    "source_user": "0b01001001",
    "source_repo": "spectree",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# read the doc
master_doc = "index"


def resolve_repository_links(app, doctree):
    """Resolve repository-relative README links when rendered by Sphinx."""
    source_user = app.config.html_context["source_user"]
    source_repo = app.config.html_context["source_repo"]

    for node in list(doctree.findall(addnodes.pending_xref)):
        target = node.get("reftarget", "")
        path, separator, fragment = target.partition("#")
        if not path:
            continue

        repository_path = (REPOSITORY_ROOT / path).resolve()
        if not repository_path.is_relative_to(REPOSITORY_ROOT):
            continue
        if not repository_path.exists():
            continue

        if repository_path.is_relative_to(Path(app.srcdir)):
            docname = (
                repository_path.relative_to(app.srcdir).with_suffix("").as_posix()
            )
            if docname in app.env.found_docs:
                refuri = app.builder.get_relative_uri(app.env.docname, docname)
                if separator:
                    refuri = f"{refuri}#{quote(fragment)}"
                reference = nodes.reference("", "", internal=True, refuri=refuri)
                reference.extend(node.children)
                node.replace_self(reference)
                continue

        object_type = "tree" if repository_path.is_dir() else "blob"
        refuri = (
            f"https://github.com/{source_user}/{source_repo}/{object_type}/HEAD/"
            f"{quote(path)}"
        )
        if separator:
            refuri = f"{refuri}#{quote(fragment)}"

        reference = nodes.reference("", "", internal=False, refuri=refuri)
        reference.extend(node.children)
        node.replace_self(reference)


def setup(app):
    app.connect("doctree-read", resolve_repository_links)
