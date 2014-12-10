# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

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
        # Adding model 'VerifiedComputer'
        db.create_table('two_factor_verifiedcomputer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_orm_label])),
            ('verified_until', self.gf('django.db.models.fields.DateTimeField')()),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
            ('last_used_at', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('two_factor', ['VerifiedComputer'])

        # Adding model 'Token'
        db.create_table('two_factor_token', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm[user_orm_label], unique=True)),
            ('seed', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('backup_phone', self.gf('django.db.models.fields.CharField')(max_length=16, null=True, blank=True)),
        ))
        db.send_create_signal('two_factor', ['Token'])


    def backwards(self, orm):
        # Deleting model 'VerifiedComputer'
        db.delete_table('two_factor_verifiedcomputer')

        # Deleting model 'Token'
        db.delete_table('two_factor_token')


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
        'two_factor.token': {
            'Meta': {'object_name': 'Token'},
            'backup_phone': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'seed': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
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
