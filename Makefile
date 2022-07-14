check: lint test

SOURCE_FILES=spectree tests examples setup.py

install:
	pip install -e .[email,flask,falcon,starlette,dev]

test:
	pip install -U -e .[email,flask,falcon,starlette]
	pytest tests -vv -rs
	pip uninstall falcon email-validator -y && pip install falcon==2.0.0
	pytest tests -vv -rs
doc:
	cd docs && make html

opendoc:
	cd docs/build/html && python -m http.server

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	python -m build

publish: package
	twine upload dist/*

format:
	autoflake --in-place --recursive --remove-all-unused-imports --ignore-init-module-imports ${SOURCE_FILES}
	isort --project=spectree ${SOURCE_FILES}
	black ${SOURCE_FILES}

lint:
	isort --check --diff --project=spectree ${SOURCE_FILES}
	black --check --diff ${SOURCE_FILES}
	flake8 ${SOURCE_FILES} --count --show-source --statistics
	mypy --install-types --non-interactive --show-error-codes --warn-unused-ignores --disable-error-code attr-defined ${SOURCE_FILES}

.PHONY: test doc
