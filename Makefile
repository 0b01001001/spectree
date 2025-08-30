.DEFAULT_GOAL:=install

SOURCE_FILES=spectree tests examples
MYPY_SOURCE_FILES=spectree tests # temporary

install:
	uv sync --all-extras --all-groups
	uv run -- prek install

import_test:
	for module in flask quart falcon starlette; do \
		uv sync --extra $$module; \
		bash -c "uv run tests/import_module/test_$${module}_plugin.py" || exit 1; \
	done

test: import_test
	uv pip sync pylock.toml
	uv run -- pytest tests -vv -rs --disable-warnings
	uv pip sync pylock.legacy.toml --strict
	uv run --no-sync -- pytest tests -vv -rs --disable-warnings

update_snapshot:
	@uv run -- pytest --snapshot-update

update_lock:
	uv pip compile --all-extras --group docs --group dev -o pylock.toml pyproject.toml
	uv pip compile --all-extras --group docs --group dev -o pylock.legacy.toml pyproject.toml requirements-legacy.txt

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

.PHONY: test doc
