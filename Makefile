TARGET?=tests

.PHONY: docs flake8 example test coverage

docs:
	cd docs; make html
	open docs/_build/html/index.html

flake8:
	flake8 --ignore=W999 two_factor example tests

example:
	DJANGO_SETTINGS_MODULE=example.settings PYTHONPATH=. \
		django-admin.py runserver

test:
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		django-admin.py test ${TARGET}

coverage:
	coverage erase
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		coverage run --branch --source=two_factor \
		`which django-admin.py` test ${TARGET}
	coverage combine
	coverage html
	coverage report

tx-pull:
	tx pull -a
	cd two_factor; django-admin.py compilemessages
	cd example; django-admin.py compilemessages

tx-push:
	cd two_factor; django-admin.py makemessages -l en
	cd example; django-admin.py makemessages -l en
	tx push -s
