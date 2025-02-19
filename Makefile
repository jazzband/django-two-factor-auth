.PHONY: docs flake8 example test coverage migrations

docs:
	cd docs; make html
	open docs/_build/html/index.html

flake8:
	tox -e flake8,isort

example:
	DJANGO_SETTINGS_MODULE=example.settings PYTHONPATH=. \
		django-admin migrate
	DJANGO_SETTINGS_MODULE=example.settings PYTHONPATH=. \
		django-admin runserver

example-webauthn:
	DJANGO_SETTINGS_MODULE=example.settings_webauthn PYTHONPATH=. \
		django-admin migrate
	DJANGO_SETTINGS_MODULE=example.settings_webauthn PYTHONPATH=. \
		django-admin runserver

test:
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		django-admin test ${TARGET}

migrations:
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		django-admin makemigrations two_factor

coverage:
	coverage erase
	DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=. \
		coverage run --parallel --source=two_factor \
		`which django-admin` test ${TARGET}
	coverage combine
	coverage html
	coverage report --precision=2

tx-pull:
	tx pull -a --force
	cd two_factor; django-admin compilemessages
	cd example; django-admin compilemessages

tx-push:
	cd two_factor; django-admin makemessages -l en -e html,txt,py,xml
	cd example; django-admin makemessages -l en -e html,txt,py,xml
	tx push -s
