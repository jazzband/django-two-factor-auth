# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Session',
            fields=[
                ('session_key', models.CharField(max_length=40, serialize=False, verbose_name='session key', primary_key=True)),
                ('session_data', models.TextField(verbose_name='session data')),
                ('expire_date', models.DateTimeField(verbose_name='expiry date', db_index=True)),
                ('user_agent', models.CharField(max_length=200)),
                ('last_activity', models.DateTimeField(auto_now=True)),
                ('ip', models.GenericIPAddressField()),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'session',
                'verbose_name_plural': 'sessions',
            },
            bases=(models.Model,),
        ),
    ]
