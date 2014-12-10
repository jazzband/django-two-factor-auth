# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

# Safe User import for Django < 1.5
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

user_orm_label = '%s.%s' % (User._meta.app_label, User._meta.object_name)
user_model_label = '%s.%s' % (User._meta.app_label, User._meta.module_name)


class Migration(DataMigration):

    def forwards(self, orm):
        for token in orm['two_factor.token'].objects.all():
            if token.method == 'generator':
                orm['otp_totp.totpdevice'].objects.create(
                    name='default',
                    user_id=token.user_id,
                    key=token.seed,
                )
            else:
                orm['two_factor.phonedevice'].objects.create(
                    name='default',
                    user_id=token.user_id,
                    key=token.seed,
                    number=token.phone,
                    method=token.method,
                )

    def backwards(self, orm):
        pass

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {'object_name': User.__name__, 'db_table': "'%s'" % User._meta.db_table},
            User._meta.pk.attname: (
                'django.db.models.fields.AutoField', [],
                {'primary_key': 'True',
                'db_column': "'%s'" % User._meta.pk.column}
            ),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'otp_totp.totpdevice': {
            'Meta': {'object_name': 'TOTPDevice'},
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'digits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '6'}),
            'drift': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "'8bc2d86ec59c342e30159ee230a5c63078181d92'", 'max_length': '80'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'step': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '30'}),
            't0': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'tolerance': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_orm_label})
        },
        'two_factor.phonedevice': {
            'Meta': {'object_name': 'PhoneDevice'},
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "'7efc60318ba39e8e9d8f0101958c691b0b1b574b'", 'max_length': '40'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_orm_label})
        },
        'two_factor.token': {
            'Meta': {'object_name': 'Token'},
            'backup_phone': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'seed': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['%s']" % user_orm_label, 'unique': 'True'})
        },
        'two_factor.verifiedcomputer': {
            'Meta': {'object_name': 'VerifiedComputer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'last_used_at': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_orm_label}),
            'verified_until': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['two_factor']
    symmetrical = True
