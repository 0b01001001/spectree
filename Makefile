.DEFAULT_GOAL:=install

SOURCE_FILES=spectree tests examples
MYPY_SOURCE_FILES=spectree tests # temporary

install:
	uv sync --all-extras --all-groups
	uv run -- prek install

import_test:
	for module in flask quart falcon starlette; do \
		uv sync --extra pydantic --extra $$module; \
		bash -c "uv run tests/import_module/test_$${module}_plugin.py" || exit 1; \
	done
	uv sync --extra msgspec --extra falcon
	bash -c "uv run tests/import_module/test_msgspec_plugin.py"

import_test_without_msgspec:
	for module in flask quart falcon starlette; do \
		uv sync --extra pydantic --extra $$module; \
		bash -c "uv run tests/import_module/test_$${module}_plugin.py" || exit 1; \
	done

test: import_test
	uv sync --all-extras --group dev
	uv run -- pytest tests -vv -rs --disable-warnings

test_without_msgspec: import_test_without_msgspec
	uv sync --extra pydantic --extra flask --extra quart --extra falcon --extra starlette --extra offline --group dev
	uv run -- pytest tests -vv -rs --disable-warnings -m "not msgspec"

update_snapshot:
	@uv run -- pytest --snapshot-update

doc:
	@cd docs && make html

opendoc:
	@cd docs/build/html && uv run -m http.server 8765 -b 127.0.0.1

clean:
	@-rm -rf build/ dist/ *.egg-info .pytest_cache
	@find . -name '*.pyc' -type f -exec rm -rf {} +
	@find . -name '__pycache__' -exec rm -rf {} +

package: clean
	@uv build

publish: package
	@uv publish dist/*

format:
	@uv run -- ruff format ${SOURCE_FILES}
	@uv run -- ruff check --fix ${SOURCE_FILES}

lint:
	@uv run -- ruff format --check ${SOURCE_FILES}
	@uv run -- ruff check ${SOURCE_FILES}
	@uv run -- mypy --install-types --non-interactive ${MYPY_SOURCE_FILES}

changelog:
	@git-cliff --config cliff.toml --repository . --output CHANGELOG.md

.PHONY: test doc
