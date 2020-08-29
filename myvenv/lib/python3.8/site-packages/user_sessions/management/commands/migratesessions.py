# -*- coding: UTF-8 -*-
import importlib
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from user_sessions.models import Session as UserSession

logger = logging.getLogger(__name__)


def get_model_class(full_model_name):
    try:
        old_model_package, old_model_class_name = full_model_name.rsplit('.', 1)
        package = importlib.import_module(old_model_package)
        return getattr(package, old_model_class_name)
    except RuntimeError as e:
        if 'INSTALLED_APPS' in e.message:
            raise RuntimeError(
                "To run this command, temporarily append '{model}' to settings.INSTALLED_APPS"
                .format(model=old_model_package.rsplit('.models')[0]))
        raise


class Command(BaseCommand):
    """
    Convert existing (old) sessions to the user_sessions SessionStore.

    If you have an operational site and switch to user_sessions, you might want to keep your
    active users logged in. We assume the old sessions are stored in a database table `oldmodel`.
    This command creates a `user_session.Session` object for each session of the previous model.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            '--oldmodel',
            dest='oldmodel',
            default='django.contrib.sessions.models.Session',
            help='Existing session model to migrate to the new UserSessions database table'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        old_sessions = get_model_class(options['oldmodel']).objects.all()
        logger.info("Processing %d session objects" % old_sessions.count())
        conversion_count = 0
        for old_session in old_sessions:
            if not UserSession.objects.filter(session_key=old_session.session_key).exists():
                data = old_session.get_decoded()
                user = None
                if '_auth_user_id' in data:
                    user = User.objects.filter(pk=data['_auth_user_id']).first()
                UserSession.objects.create(
                    session_key=old_session.session_key,
                    session_data=old_session.session_data,
                    expire_date=old_session.expire_date,
                    user=user,
                    ip='127.0.0.1'
                )
                conversion_count += 1

        logger.info("Created %d new session objects" % conversion_count)
