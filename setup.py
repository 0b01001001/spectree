from setuptools import setup

# this file is kept for GitHub's dependency graph

setup(
    name="spectree",
    install_requires=[
        "pydantic>=1.2,<3",
    ],
    extras_require={
        "email": ["pydantic[email]>=1.2,<3"],
        "flask": ["flask"],
        "quart": ["quart"],
        "falcon": ["falcon>=3.0.0"],
        "starlette": ["starlette[full]"],
        "dev": [
            "pytest>=7.1,<9.0",
            "ruff>=0.1.3",
            "mypy>=0.971",
            "syrupy>=4.0.0",
        ],
        "docs": [
            "Sphinx",
            "shibuya",
            "myst-parser",
            "sphinx-sitemap",
        ],
    },
)
