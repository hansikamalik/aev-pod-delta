.PHONY: test contract coverage report regression ci

test:        ## fast inner loop: everything except regression
	python3 -m pytest -q -m "not regression"

contract:    ## the P0 gate — every connector must pass
	python3 -m pytest tests/contract -m contract -v

regression:  ## full suite, run after every merge + Day 7
	python3 -m pytest -q

coverage:    ## module test coverage for the weekly report
	python3 -m pytest --cov --cov-report=term-missing -q

report:      ## HTML report for the final test report deliverable
	python3 -m pytest -m "not regression" --html=reports/test-report.html --self-contained-html -q

ci: coverage regression  ## what CI runs on every PR
