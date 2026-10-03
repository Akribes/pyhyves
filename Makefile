.PHONY: test style verify format

test:
	pytest --cov=pyhyves tests

style:
	mypy --strict pyhyves
	ruff check pyhyves tests

verify: test style

format:
	ruff check --fix pyhyves tests