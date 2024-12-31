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

sys.path.insert(0, os.path.abspath("../../"))


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
