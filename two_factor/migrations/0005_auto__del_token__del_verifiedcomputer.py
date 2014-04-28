# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
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


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Token'
        db.delete_table('two_factor_token')

        # Deleting model 'VerifiedComputer'
        db.delete_table('two_factor_verifiedcomputer')


    def backwards(self, orm):
        # Adding model 'Token'
        db.create_table('two_factor_token', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm[user_orm_label], unique=True)),
            ('backup_phone', self.gf('django.db.models.fields.CharField')(max_length=16, null=True, blank=True)),
            ('seed', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=16)),
        ))
        db.send_create_signal('two_factor', ['Token'])

        # Adding model 'VerifiedComputer'
        db.create_table('two_factor_verifiedcomputer', (
            ('last_used_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_orm_label])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('verified_until', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('two_factor', ['VerifiedComputer'])


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
        'two_factor.phonedevice': {
            'Meta': {'object_name': 'PhoneDevice'},
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "'f40d7cf8bbafa48eb19f8ae21cff16bd12d5c810'", 'max_length': '40'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_orm_label})
        }
    }

    complete_apps = ['two_factor']
