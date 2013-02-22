# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SmartConnector'
        db.create_table('smartconnectorscheduler_smartconnector', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('composite_stage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Stage'])),
        ))
        db.send_create_signal('smartconnectorscheduler', ['SmartConnector'])

        # Adding model 'Context'
        db.create_table('smartconnectorscheduler_context', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.UserProfile'])),
            ('current_stage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Stage'])),
        ))
        db.send_create_signal('smartconnectorscheduler', ['Context'])

        # Adding model 'DirectiveArgSet'
        db.create_table('smartconnectorscheduler_directiveargset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('directive', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Directive'])),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
            ('schema', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Schema'])),
        ))
        db.send_create_signal('smartconnectorscheduler', ['DirectiveArgSet'])

        # Adding model 'Directive'
        db.create_table('smartconnectorscheduler_directive', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal('smartconnectorscheduler', ['Directive'])

        # Adding model 'Stage'
        db.create_table('smartconnectorscheduler_stage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('impl', self.gf('django.db.models.fields.CharField')(max_length=256, null=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='')),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['smartconnectorscheduler.Stage'])),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('smartconnectorscheduler', ['Stage'])

        # Adding model 'Platform'
        db.create_table('smartconnectorscheduler_platform', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal('smartconnectorscheduler', ['Platform'])

        # Adding model 'CommandArgument'
        db.create_table('smartconnectorscheduler_commandargument', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('template_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal('smartconnectorscheduler', ['CommandArgument'])

        # Adding model 'ContextParameter'
        db.create_table('smartconnectorscheduler_contextparameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.ParameterName'])),
            ('paramset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.ContextParameterSet'])),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('smartconnectorscheduler', ['ContextParameter'])

        # Adding model 'ContextParameterSet'
        db.create_table('smartconnectorscheduler_contextparameterset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('context', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Context'])),
            ('schema', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Schema'])),
            ('ranking', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('smartconnectorscheduler', ['ContextParameterSet'])

        # Adding model 'Command'
        db.create_table('smartconnectorscheduler_command', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('directive', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Directive'])),
            ('initial_stage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Stage'])),
            ('platform', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['smartconnectorscheduler.Platform'])),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal('smartconnectorscheduler', ['Command'])


    def backwards(self, orm):
        # Deleting model 'SmartConnector'
        db.delete_table('smartconnectorscheduler_smartconnector')

        # Deleting model 'Context'
        db.delete_table('smartconnectorscheduler_context')

        # Deleting model 'DirectiveArgSet'
        db.delete_table('smartconnectorscheduler_directiveargset')

        # Deleting model 'Directive'
        db.delete_table('smartconnectorscheduler_directive')

        # Deleting model 'Stage'
        db.delete_table('smartconnectorscheduler_stage')

        # Deleting model 'Platform'
        db.delete_table('smartconnectorscheduler_platform')

        # Deleting model 'CommandArgument'
        db.delete_table('smartconnectorscheduler_commandargument')

        # Deleting model 'ContextParameter'
        db.delete_table('smartconnectorscheduler_contextparameter')

        # Deleting model 'ContextParameterSet'
        db.delete_table('smartconnectorscheduler_contextparameterset')

        # Deleting model 'Command'
        db.delete_table('smartconnectorscheduler_command')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'smartconnectorscheduler.command': {
            'Meta': {'object_name': 'Command'},
            'directive': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Directive']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_stage': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Stage']"}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'platform': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Platform']"})
        },
        'smartconnectorscheduler.commandargument': {
            'Meta': {'object_name': 'CommandArgument'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'template_url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'smartconnectorscheduler.context': {
            'Meta': {'object_name': 'Context'},
            'current_stage': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Stage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.UserProfile']"})
        },
        'smartconnectorscheduler.contextparameter': {
            'Meta': {'ordering': "('name',)", 'object_name': 'ContextParameter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.ParameterName']"}),
            'paramset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.ContextParameterSet']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'smartconnectorscheduler.contextparameterset': {
            'Meta': {'ordering': "['-ranking']", 'object_name': 'ContextParameterSet'},
            'context': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Context']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ranking': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'schema': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Schema']"})
        },
        'smartconnectorscheduler.directive': {
            'Meta': {'object_name': 'Directive'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'smartconnectorscheduler.directiveargset': {
            'Meta': {'object_name': 'DirectiveArgSet'},
            'directive': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Directive']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'schema': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Schema']"})
        },
        'smartconnectorscheduler.parametername': {
            'Meta': {'ordering': "['-ranking']", 'unique_together': "(('schema', 'name'),)", 'object_name': 'ParameterName'},
            'choices': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'help_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'max_length': ('django.db.models.fields.IntegerField', [], {'default': '255'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ranking': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'schema': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Schema']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'smartconnectorscheduler.platform': {
            'Meta': {'object_name': 'Platform'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'smartconnectorscheduler.schema': {
            'Meta': {'unique_together': "(('namespace', 'name'),)", 'object_name': 'Schema'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '50'}),
            'namespace': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'smartconnectorscheduler.smartconnector': {
            'Meta': {'object_name': 'SmartConnector'},
            'composite_stage': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Stage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'smartconnectorscheduler.stage': {
            'Meta': {'object_name': 'Stage'},
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'impl': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['smartconnectorscheduler.Stage']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'smartconnectorscheduler.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'company': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nickname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'smartconnectorscheduler.userprofileparameter': {
            'Meta': {'ordering': "('name',)", 'object_name': 'UserProfileParameter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.ParameterName']"}),
            'paramset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.UserProfileParameterSet']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'smartconnectorscheduler.userprofileparameterset': {
            'Meta': {'ordering': "['-ranking']", 'object_name': 'UserProfileParameterSet'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ranking': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'schema': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.Schema']"}),
            'user_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['smartconnectorscheduler.UserProfile']"})
        }
    }

    complete_apps = ['smartconnectorscheduler']