.DEFAULT_GOAL:=install

SOURCE_FILES=spectree tests examples

install:
	pip install -U -e .[email,quart,flask,falcon,starlette,dev]

import_test_pydantic2:
	pip install -e .[email,pydantic2]
	for module in flask quart falcon starlette; do \
		pip install -U $$module; \
		bash -c "python tests/import_module/test_$${module}_plugin.py" || exit 1; \
		pip uninstall $$module -y; \
	done

test_pydantic2: import_test_pydantic2
	pip install -U -e .[email,flask,quart,falcon,starlette,pydantic2]
	pytest tests -vv -rs

import_test_pydantic1:
	pip install -e .[email,pydantic1]
	for module in flask quart falcon starlette; do \
		pip install -U $$module; \
		bash -c "python tests/import_module/test_$${module}_plugin.py" || exit 1; \
		pip uninstall $$module -y; \
	done

test_pydantic1: import_test_pydantic1
	pip install -U -e .[email,flask,quart,falcon,starlette,pydantic1]
	pytest tests -vv -rs

test: test_pydantic1 test_pydantic2

snapshot_pydantic1:
	pip install -U -e .[pydantic1]
	pytest tests --snapshot-update

snapshot_pydantic2:
	pip install -U -e .[pydantic2]
	pytest tests --snapshot-update

doc:
	cd docs && make html

opendoc:
	cd docs/build/html && python -m http.server 8765

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
	flake8 ${SOURCE_FILES} --count --show-source --statistics --ignore=D203,E203,W503 --max-line-length=88 --max-complexity=15
	mypy --install-types --non-interactive ${SOURCE_FILES}

.PHONY: test doc
