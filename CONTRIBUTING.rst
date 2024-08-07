.. image:: https://jazzband.co/static/img/jazzband.svg
   :target: https://jazzband.co/
   :alt: Jazzband

This is a `Jazzband <https://jazzband.co>`_ project. By contributing you agree
to abide by the `Contributor Code of Conduct <https://jazzband.co/about/conduct>`_
and follow the `guidelines <https://jazzband.co/about/guidelines>`_.

Contribute
==========

* Submit issues to the `issue tracker`_ on Github.
* Fork the `source code`_ at Github.
* Write some code and make sure it is covered with unit tests.
* Send a pull request with your changes.
* Provide a translation using Transifex_.

Local installation
------------------

Install the development dependencies, which also installs the package in editable mode
for local development and additional development tools.

.. code-block:: console

    pip install -r requirements_dev.txt

Running tests
-------------
This project aims for full code-coverage, this means that your code should be
well-tested. Also test branches for hardened code. You can run the full test
suite with::

    make test

Or run a specific test with::

    make test TARGET=tests.tests.TwilioGatewayTest

For Python compatibility, tox_ is used. You can run the full test suite,
covering all supported Python and Django version with::

    tox

Releasing
---------
The following actions are required to push a new version:

* Update release notes and version number in `pyproject.toml` and `docs/conf.py`

* If any new translations strings were added, push the new source language to
  Transifex_. Make sure translators have sufficient time to translate those
  new strings::

    make tx-push

* Add migrations::

    python example/manage.py makemigrations two_factor
    git commit two_factor/migrations -m "Added migrations"

* Update translations::

    make tx-pull

* Trigger the packaging and upload::

    git tag <tag number>
    git push && git push --tags

The `.github/workflows/release.yml` file should do the remaining work and
publish the release to PyPi.

.. _issue tracker: https://github.com/jazzband/django-two-factor-auth/issues
.. _source code: https://github.com/jazzband/django-two-factor-auth
.. _Transifex: https://explore.transifex.com/Bouke/django-two-factor-auth/
