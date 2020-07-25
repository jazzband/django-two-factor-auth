TARGET?=tests

.PHONY: docs flake8 example test coverage migrations

docs:
	cd docs; make html
	open docs/_build/html/index.html

flake8:
	tox -e flake8,isort

example:
	DJANGO_SETTINGS_MODULE=example.settings PYTHONPATH=. \
		django-admin.py runserver

test:
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		django-admin.py test ${TARGET}

migrations:
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		django-admin.py makemigrations two_factor

coverage:
	coverage erase
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		coverage run ---parallel --source=two_factor \
		`which django-admin.py` test ${TARGET}
	coverage combine
	coverage html
	coverage report --precision=2

tx-pull:
	tx pull -a
	cd two_factor; django-admin.py compilemessages
	cd example; django-admin.py compilemessages

tx-push:
	cd two_factor; django-admin.py makemessages -l en
	cd example; django-admin.py makemessages -l en
	tx push -s
