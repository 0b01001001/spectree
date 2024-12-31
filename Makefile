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
	pytest tests -vv -rs --disable-warnings
	pip install --force-reinstall 'pydantic[email]<2'
	pytest tests -vv -rs --disable-warnings

update_snapshot:
	@pytest --snapshot-update

doc:
	@cd docs && make html

opendoc:
	@cd docs/build/html && python -m http.server 8765 -b 127.0.0.1

clean:
	@-rm -rf build/ dist/ *.egg-info .pytest_cache
	@find . -name '*.pyc' -type f -exec rm -rf {} +
	@find . -name '__pycache__' -exec rm -rf {} +

package: clean
	@python -m build

publish: package
	@twine upload dist/*

format:
	@ruff format ${SOURCE_FILES}
	@ruff check --fix ${PY_SOURCE}

lint:
	@ruff check ${SOURCE_FILES}
	@mypy --install-types --non-interactive ${MYPY_SOURCE_FILES}

.PHONY: test doc
