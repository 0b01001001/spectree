check: lint test

install:
	pip install -e .

test:
	pytest tests -vv

doc:
	cd docs && make html

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	python setup.py sdist bdist_wheel

publish: package
	twine upload dist/*

lint:
	flake8 . --count --show-source --statistics

.PHONY: test doc