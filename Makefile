.DEFAULT_GOAL:=install

SOURCE_FILES=spectree tests examples
MYPY_SOURCE_FILES=spectree tests # temporary

install:
	pip install -U -e .[email,quart,flask,falcon,starlette,dev]

import_test:
	pip install -e .[email]
	for module in flask quart falcon starlette; do \
		pip install -U $$module; \
		bash -c "python tests/import_module/test_$${module}_plugin.py" || exit 1; \
		pip uninstall $$module -y; \
	done

test: import_test
	pip install -U -e .[email,flask,quart,falcon,starlette]
	pytest tests -vv -rs
	pip install --force-reinstall 'pydantic[email]<2'
	pytest tests -vv -rs

doc:
	cd docs && make html

opendoc:
	cd docs/build/html && python -m http.server 8765 -b 127.0.0.1

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
	flake8 ${SOURCE_FILES} --count --show-source --statistics --ignore=D203,E203,W503 --max-line-length=88 --max-complexity=17
	mypy --install-types --non-interactive ${MYPY_SOURCE_FILES}

.PHONY: test doc
