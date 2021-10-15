from io import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    readme = f.read()

with open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    requires = [req.strip() for req in f if req]


setup(
    name="spectree",
    version="0.6.3",
    author="Keming Yang",
    author_email="kemingy94@gmail.com",
    description=(
        "generate OpenAPI document and validate request&response "
        "with Python annotations."
    ),
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/0b01001001/spectree",
    packages=find_packages(exclude=["examples*", "tests*"]),
    package_data={},
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6",
    install_requires=requires,
    extras_require={
        "flask": ["flask"],
        "falcon": ["falcon"],
        "starlette": ["starlette[full]"],
        "dev": [
            "pytest>=6",
            "flake8>=3.8",
            "black>=20.8b1",
            "isort>=5.6",
            "autoflake>=1.4",
        ],
    },
    zip_safe=False,
    entry_points={
        "console_scripts": [],
    },
)
