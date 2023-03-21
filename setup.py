from setuptools import setup


# this file is kept for GitHub's dependency graph

setup(
    name="spectree",
    install_requires=[
        "pydantic>=1.2",
    ],
    extras_require={
        "email": ["pydantic[email]>=1.2"],
        "flask": ["flask"],
        "quart": ["quart"],
        "falcon": ["falcon>=3.0.0"],
        "starlette": ["starlette[full]"],
        "dev": [
            "pytest~=7.1",
            "flake8>=4,<7",
            "black>=22.3,<24.0",
            "isort~=5.10",
            "autoflake>=1.4,<3.0",
            "mypy>=0.971",
            "syrupy>=4.0.0",
        ],
    },
)
