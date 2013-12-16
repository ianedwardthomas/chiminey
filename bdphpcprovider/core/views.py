# Copyright (C) 2013, RMIT University

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
#
#
import os
import functools
import logging
import json
import django
from pprint import pformat

# FIXME,TODO: replace basic authentication with basic+SSL,
# or better digest or oauth
from tastypie.authentication import (BasicAuthentication, ApiKeyAuthentication, MultiAuthentication)
from tastypie.authorization import DjangoAuthorization, Authorization
from tastypie import fields
from tastypie.resources import Resource, ModelResource, ALL_WITH_RELATIONS, ALL
from tastypie.utils import dict_strip_unicode_keys
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.paginator import Paginator
from django.contrib.auth.models import User
from django.core.validators import ValidationError
from django import forms
from django.contrib.sessions.models import Session

from django.core.exceptions import MultipleObjectsReturned

from django.core.urlresolvers import reverse

from django.contrib.auth import authenticate, login

from django.http import (
    HttpResponseRedirect,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseNotAllowed,
    HttpResponseBadRequest)


from bdphpcprovider.smartconnectorscheduler import models
from bdphpcprovider.smartconnectorscheduler.errors import InvalidInputError
from bdphpcprovider.smartconnectorscheduler import hrmcstages
from bdphpcprovider.smartconnectorscheduler import platform
from bdphpcprovider.smartconnectorscheduler.errors import deprecated

from django.utils.encoding import smart_unicode
from bdphpcprovider.core.auth import logged_in_or_basicauth

logger = logging.getLogger(__name__)


# TODO: this code should be copied to maintain separation between api/ui
from bdphpcprovider.simpleui import validators
from bdphpcprovider.core import serverside_validators

logger = logging.getLogger(__name__)


class MyBasicAuthentication(BasicAuthentication):
    def __init__(self, *args, **kwargs):
        super(MyBasicAuthentication, self).__init__(*args, **kwargs)

    def is_authenticated(self, request, **kwargs):
        if 'sessionid' in request.COOKIES:
            s = Session.objects.get(pk=request.COOKIES['sessionid'])
            if '_auth_user_id' in s.get_decoded():
                u = User.objects.get(id=s.get_decoded()['_auth_user_id'])
                request.user = u
                return True
        return super(MyBasicAuthentication, self).is_authenticated(request, **kwargs)


class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        allowed_methods = ['get']
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']


class UserProfileResource(ModelResource):
    userid = fields.ForeignKey(UserResource, 'user')

    class Meta:
        queryset = models.UserProfile.objects.all()
        resource_name = 'userprofile'
        allowed_methods = ['get']
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        authorization = DjangoAuthorization()
    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)

    # def obj_create(self, bundle, **kwargs):
    #     return super(UserProfileResource, self).obj_create(bundle,
    #         user=bundle.request.user)

    def get_object_list(self, request):
        # FIXME: we never seem to be authenticated here
        if request.user.is_authenticated():
            return models.UserProfile.objects.filter(user=request.user)
        else:
            return models.UserProfile.objects.none()


class SchemaResource(ModelResource):
    class Meta:
        queryset = models.Schema.objects.all()
        resource_name = 'schema'
        allowed_methods = ['get']
        filtering = {
            'schema': ALL_WITH_RELATIONS,
            'namespace': ALL_WITH_RELATIONS,
        }


class DirectiveResource(ModelResource):
    class Meta:
        queryset = models.Directive.objects.all()
        resource_name = 'directive'
        allowed_methods = ['get']


class DirectiveArgSetResource(ModelResource):
    schema = fields.ForeignKey(SchemaResource,
        attribute='schema')
    directive = fields.ForeignKey(DirectiveResource,
        attribute='directive')
    class Meta:
        queryset = models.DirectiveArgSet.objects.all()
        resource_name = 'directiveargset'
        allowed_methods = ['get']
        filtering = {
            'directive': ALL_WITH_RELATIONS,
        }

class ParameterNameResource(ModelResource):
    schema = fields.ForeignKey(SchemaResource,
        attribute='schema')


    class Meta:
        queryset = models.ParameterName.objects.all()
        resource_name = 'parametername'
        allowed_methods = ['get']
        filtering = {
            'schema': ALL_WITH_RELATIONS
        }


class UserProfileParameterSetResource(ModelResource):
    user_profile = fields.ForeignKey(UserProfileResource,
        attribute='user_profile')
    schema = fields.ForeignKey(SchemaResource,
        attribute='schema')

    class Meta:
        queryset = models.UserProfileParameterSet.objects.all()
        resource_name = 'userprofileparameterset'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get']

    def get_object_list(self, request):
        return models.UserProfileParameterSet.objects.filter(user_profile__user=request.user)


class UserProfileParameterResource(ModelResource):
    name = fields.ForeignKey(ParameterNameResource,
        attribute='name')
    paramset = fields.ForeignKey(UserProfileParameterSetResource,
        attribute='paramset')

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(paramset__user_profile__user=request.user)

    def obj_create(self, bundle, **kwargs):
        return super(UserProfileParameterResource, self).obj_create(bundle,
            user=bundle.request.user)

    def get_object_list(self, request):
        return models.UserProfileParameter.objects.filter(paramset__user_profile__user=request.user)

    class Meta:
        queryset = models.UserProfileParameter.objects.all()
        resource_name = 'userprofileparameter'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())

        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        # curl --digest --user user2 --dump-header - -H "Content-Type: application/json" -X PUT --data ' {"value": 44}' http://115.146.86.247/api/v1/userprofileparameter/48/?format=json
        allowed_methods = ['get', 'put']
        # TODO: validation on put value to correct type


class ContextResource(ModelResource):
    hrmc_schema = "http://rmit.edu.au/schemas/input/hrmc/"
    system_schema = "http://rmit.edu.au/schemas/input/system"
    sweep_schema = 'http://rmit.edu.au/schemas/input/sweep/'

    owner = fields.ForeignKey(UserProfileResource,
        attribute='owner')

    directive = fields.ForeignKey(DirectiveResource,
        attribute='directive', full=True, null=True)

    parent = fields.ForeignKey('self',
        attribute='parent', null=True)

    class Meta:
        queryset = models.Context.objects.all()
        resource_name = 'context'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get', 'post']
        paginator_class = Paginator

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)

    def get_object_list(self, request):
        return models.Context.objects.filter(owner__user=request.user).order_by('-id')

    def post_list(self, request, **kwargs):
        #curl --user user2 --dump-header - -H "Content-Type: application/json" -X POST --data ' {"number_vm_instances": 8, "minimum_number_vm_instances": 8, "iseed": 42, "input_location": "file://127.0.0.1/myfiles/input", "optimisation_scheme": 2, "threshold": "[2]", "error_threshold": "0.03", "max_iteration": 10}' http://115.146.86.247/api/v1/context/?format=json

        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)
        bundle.data['username'] = request.user.username
        if 'smart_connector' in bundle.data:

            dispatch_table = {
                'hrmc': self._post_to_hrmc,
                'sweep': self._post_to_sweep_hrmc,
                'sweep_make': self._post_to_sweep_make,
                'sweep_vasp': self._post_to_sweep_vasp,
                'copydir': self._post_to_copy,
                'remotemake': self._post_to_remotemake}

            smart_connector = bundle.data['smart_connector']
            logger.debug("smart_connector=%s" % smart_connector)

            try:
                if smart_connector in dispatch_table:
                    logger.debug("dispatching %s" % smart_connector)
                    (myplatform, directive_name,
                     directive_args, system_settings) = dispatch_table[smart_connector](bundle, smart_connector)
                else:
                    return http.HttpBadRequest()
            except Exception, e:
                logger.error("post_list error %s" % e)
                raise ImmediateHttpResponse(http.HttpBadRequest(e))
                #return self.create_response(request, bundle, response_class=http.HttpForbidden)
        location = []
        try:
            (run_settings, command_args, run_context) \
                 = hrmcstages.make_runcontext_for_directive(
                 myplatform,
                 directive_name,
                 directive_args, system_settings, request.user.username)

        except InvalidInputError, e:
            bundle.obj = None
            logger.error(e)
        else:
            logger.debug("run_context=%s" % run_context)

            # make success message for context.
            mess = "info, job started"
            message, was_created = models.ContextMessage.objects.get_or_create(context=run_context)
            message.message = mess
            message.save()

            bundle.obj.pk = run_context.id
            # We do not call obj_create because make_runcontext_for_directive()
            # has already created the object.

            location = self.get_resource_uri(bundle)

        return http.HttpCreated(location=location)

    @deprecated
    def _post_to_hrmc(self, bundle, smart_connector):
        platform = 'nectar'
        directive_name = "hrmc"
        logger.debug("%s" % directive_name)
        directive_args = []

        try:
            directive_args.append(
             ['',
                 ['http://rmit.edu.au/schemas/hrmc',
                     ('number_vm_instances',
                         bundle.data[self.hrmc_schema+'number_vm_instances']),
                     ('minimum_number_vm_instances',
                         bundle.data[self.hrmc_schema+'minimum_number_vm_instances']),
                     (u'iseed', bundle.data[self.hrmc_schema+'iseed']),
                     ('max_seed_int', 1000),
                     (u'random_numbers', 'file://127.0.0.1/randomnums.txt'),
                     ('input_location',  bundle.data[self.hrmc_schema+'input_location']),
                     ('optimisation_scheme', bundle.data[self.hrmc_schema+'optimisation_scheme']),
                     ('threshold', str(bundle.data[self.hrmc_schema+'threshold'])),
                     ('error_threshold', str(bundle.data[self.hrmc_schema+'error_threshold'])),
                     ('max_iteration', bundle.data[self.hrmc_schema+'max_iteration']),
                     ('pottype', bundle.data[self.hrmc_schema+'pottype'])
                 ]
             ])
        except KeyError, e:
            raise ImmediateHttpResponse(http.BadRequest(e))

        logger.debug("directive_args=%s" % pformat(directive_args))
        # make the system settings, available to initial stage and merged with run_settings
        system_dict = {u'system': u'settings', u'output_location': bundle.data[os.path.join(self.system_schema, 'output_location')]}

        logger.debug('post_to_hrmc output_location = %s' % bundle.data[os.path.join(self.system_schema, 'output_location')])

        system_settings = {u'http://rmit.edu.au/schemas/system/misc': system_dict}

        logger.debug("directive_name=%s" % directive_name)
        logger.debug("directive_args=%s" % directive_args)

        return (platform, directive_name, directive_args, system_settings)

    def validate_input(self, data, directive_name):
        logger.debug(data)
        username = data['http://rmit.edu.au/schemas/bdp_userprofile/username']
        logger.debug(username)
        subtype_validation = {
            'password': ('string', validators.validate_string_not_empty, forms.PasswordInput, None),
            'hidden': ('natural number', validators.validate_hidden, None, None),
            'string_not_empty': ('string_not_empty', validators.validate_string_not_empty, None, None),
            'natural': ('natural number', validators.validate_natural_number, None, None),
            'string': ('string', validators.validate_string, None, None),
            'whole': ('whole number', validators.validate_whole_number, None, None),
            'nectar_platform': ('NeCTAR platform name', serverside_validators.validate_platform, None, None),
            'storage_bdpurl': ('Storage platform name with optional offset path', serverside_validators.validate_platform, forms.TextInput, 255),
            'even': ('even number', validators.validate_even_number, None, None),
            'bdpurl': ('BDP url', validators.validate_BDP_url, forms.TextInput, 255),
            'float': ('floading point number', validators.validate_float_number, None, None),
            'jsondict': ('JSON Dictionary', validators.validate_jsondict, forms.Textarea(attrs={'cols':30, 'rows': 5}), None),
            'bool': ('On/Off', validators.validate_bool, None,  None),
            'platform': ('platform', serverside_validators.validate_platform, None,  None),
            'mytardis': ('platform', serverside_validators.validate_platform, None,  None),
            'choicefield': ('choicefield', functools.partial(validators.myvalidate_choice_field, choices=('MC','MCSA')), forms.Select(),  None),

        }
        directive = models.Directive.objects.get(name=directive_name)
        for das in models.DirectiveArgSet.objects.filter(directive=directive):
            logger.debug("checking das=%s" % das)
            for param in models.ParameterName.objects.filter(schema=das.schema):
                logger.debug("checking param=%s"  % param.name)
                value = data[os.path.join(das.schema.namespace, param.name)]
                # # FIXME: if a input field is blank, then may have been disabled.
                # # Therefore, we pass in initial default value, with assumption
                # # that it will be ignored anyway.  This might not be the best
                # # idea, because user that leaves field blank will get default value
                # # sent and not blank.  Therefore, fields cannot be blank.

                # if str(value) == "":
                #     logger.warn("skipping %s because disabled as input" % param.name)
                #     data[os.path.join(das.schema.namespace, param.name)] = param.initial
                #     logger.debug("data=%s" % data)
                #     continue;

                validator = subtype_validation[param.subtype][1]
                logger.debug("validator=%s" % validator)
                current_subtype = param.subtype
                logger.debug(current_subtype)
                if current_subtype == 'storage_bdpurl' or current_subtype == 'nectar_platform' or\
                                current_subtype == 'platform' or current_subtype == 'mytardis':
                    value = validator(value, username)
                else:
                    value = validator(value)
                data[os.path.join(das.schema.namespace, param.name)] = value

    def _post_to_sweep_hrmc(self, bundle, directive):
        return self._post_to_sweep(bundle=bundle,
            directive=directive,
            subdirective="hrmc")

    def _post_to_sweep_make(self, bundle, directive):
        return self._post_to_sweep(bundle=bundle,
            directive=directive,
            subdirective="remotemake")


    def _post_to_sweep_vasp(self, bundle, directive):
        return self._post_to_sweep(bundle=bundle,
            directive=directive,
            subdirective="vasp")


    def _post_to_sweep(self, bundle, directive, subdirective):
        logger.debug("_post_to_sweep for %s" % subdirective)
        platform = 'local'
        logger.debug("%s" % directive)

        try:
            self.validate_input(bundle.data, directive)
        except ValidationError, e:
            logger.error(e)
            raise
        directive_obj = models.Directive.objects.get(name=directive)
        dirargs = models.DirectiveArgSet.objects.filter(directive=directive_obj)
        schemas = [x.schema.namespace for x in dirargs]
        dargs = {}
        for key in bundle.data:
            if os.path.dirname(key) in schemas:
                d = dargs.setdefault(os.path.dirname(key), {})
                d[os.path.basename(key)] = bundle.data[key]

        logger.debug("dargs=%s" % pformat(dargs))

        d_arg = []
        for key in dargs:
            directive_arg = []
            directive_arg.append(key)
            for k, v in dargs[key].items():
                directive_arg.append((k, v))
            d_arg.append(directive_arg)

        d_arg.append(
        ['http://rmit.edu.au/schemas/system',
            (u'random_numbers', 'file://127.0.0.1/randomnums.txt'),
            ('system', 'settings'),
            ('max_seed_int', 1000),
        ])
        d_arg.append(
        ['http://rmit.edu.au/schemas/stages/sweep',
            ('directive', subdirective)
        ])
        d_arg.append(
        ['http://rmit.edu.au/schemas/bdp_userprofile',
            (u'username', str(bundle.data['http://rmit.edu.au/schemas/bdp_userprofile/username'])),
        ])

        directive_args = [''] + d_arg


        logger.debug("directive_args=%s" % pformat(directive_args))

        # directive_args = ['',
        #         ['http://rmit.edu.au/schemas/input/hrmc',
        #             ('pottype', bundle.data[self.hrmc_schema + 'pottype']),
        #             ('max_iteration', bundle.data[self.hrmc_schema + 'max_iteration']),
        #             ('error_threshold', str(bundle.data[self.hrmc_schema + 'error_threshold'])),
        #             ('threshold', str(bundle.data[self.hrmc_schema + 'threshold'])),
        #             ('optimisation_scheme', bundle.data[self.hrmc_schema + 'optimisation_scheme']),
        #             ('iseed', bundle.data[self.hrmc_schema + 'iseed']),
        #             ('fanout_per_kept_result', bundle.data[self.hrmc_schema + 'fanout_per_kept_result']),
        #         ],
        #         ['http://rmit.edu.au/schemas/input/sweep',
        #             ('sweep_map', bundle.data[self.sweep_schema + 'sweep_map']),
        #         ],
        #         ['http://rmit.edu.au/schemas/input/reliability',
        #             ('maximum_retry',
        #                 bundle.data['http://rmit.edu.au/schemas/input/reliability/' + 'maximum_retry']),
        #             ('reschedule_failed_processes',
        #                 int(bundle.data['http://rmit.edu.au/schemas/input/reliability/' + 'reschedule_failed_processes'])),
        #         ],
        #         ['http://rmit.edu.au/schemas/input/system/cloud',
        #             ('number_vm_instances',
        #                 bundle.data['http://rmit.edu.au/schemas/input/system/cloud/number_vm_instances']),
        #             ('minimum_number_vm_instances',
        #                 bundle.data['http://rmit.edu.au/schemas/input/system/cloud/minimum_number_vm_instances']),
        #             ('computation_platform',
        #              bundle.data['http://rmit.edu.au/schemas/input/system/cloud/computation_platform']),
        #         ],
        #         ['http://rmit.edu.au/schemas/input/system',
        #             ('input_location', bundle.data['http://rmit.edu.au/schemas/input/system/input_location']),
        #             ('output_location', bundle.data['http://rmit.edu.au/schemas/input/system/output_location'])
        #         ],
        #         ['http://rmit.edu.au/schemas/input/mytardis',
        #             #('experiment_id', bundle.data[self.hrmc_schema + 'experiment_id']),
        #             ('experiment_id', 0),
        #         ],

        #         ['http://rmit.edu.au/schemas/system',
        #             (u'random_numbers', 'file://127.0.0.1/randomnums.txt'),
        #             ('system', 'settings'),
        #             ('max_seed_int', 1000),
        #         ],
        #         # ['http://rmit.edu.au/schemas/stages/run',
        #         #     #('run_map', bundle.data['run_map'])
        #         #     ('run_map', "{}")
        #         # ],
        #         ['http://rmit.edu.au/schemas/stages/sweep',
        #             ('directive', 'hrmc')
        #         ],
        #         ['http://rmit.edu.au/schemas/bdp_userprofile',
        #             (u'username', str(bundle.data['http://rmit.edu.au/schemas/bdp_userprofile/username'])),
        #         ],
        #     ]

        logger.debug("directive_args=%s" % pformat(directive_args))

        return (platform, directive, [directive_args], {})


        # make the system settings, available to initial stage and merged with run_settings

        logger.debug("directive_name=%s" % directive_name)
        logger.debug("directive_args=%s" % directive_args)

        return (platform, directive_name, directive_args, {})

    @deprecated
    def _post_to_remotemake(self, bundle, smart_connector):
        platform = 'nci'
        directive_name = "remotemake"
        logger.debug("%s" % directive_name)
        directive_args = []

        try:
            self.validate_input(bundle.data, directive_name)
        except ValidationError, e:
            logger.error(e)
            raise

        directive_args.append(
            ['',

                ['http://rmit.edu.au/schemas/input/sweep',
                    ('sweep_map', bundle.data[self.sweep_schema + 'sweep_map']),
                ],
                ['http://rmit.edu.au/schemas/system',
                    (u'random_numbers', 'file://127.0.0.1/randomnums.txt'),
                    ('system', 'settings'),
                    ('max_seed_int', 1000),
                ],
                ['http://rmit.edu.au/schemas/input/system',
                    ('input_location', bundle.data['http://rmit.edu.au/schemas/input/system/input_location']),
                    ('output_location', bundle.data['http://rmit.edu.au/schemas/input/system/output_location'])
                ],
                ['http://rmit.edu.au/schemas/input/mytardis',
                    #('experiment_id', bundle.data[self.hrmc_schema + 'experiment_id']),
                    ('experiment_id', 0),
                ],
            ])

        #remotemake_schema = "http://rmit.edu.au/schemas/remotemake`"
        # directive_args.append(
        #     ['',
        #         ['http://rmit.edu.au/schemas/remotemake',
        #             ('input_location',  bundle.data[remotemake_schema+'input_location']),
        #             ('experiment_id', bundle.data[remotemake_schema+'experiment_id'])],
        #         ['http://rmit.edu.au/schemas/stages/make',
        #             ('sweep_map', bundle.data[self.sweep_schema+'sweep_map'])]])

        logger.debug("directive_args=%s" % pformat(directive_args))
        # make the system settings, available to initial stage and merged with run_settings

        # system_dict = {
        #     u'system': u'settings',
        #     u'output_location': bundle.data[self.system_schema+'output_location']}
        # system_settings = {u'http://rmit.edu.au/schemas/system/misc': system_dict}

        logger.debug("directive_name=%s" % directive_name)
        logger.debug("directive_args=%s" % directive_args)

        return (platform, directive_name, directive_args, {})

    @deprecated
    def _post_to_copy(self, bundle, smart_connector):
        platform = 'nci'  # FIXME: should be local, why local Ian?
        directive_name = "copydir"
        logger.debug("%s" % directive_name)
        directive_args = []

        directive_args.append([bundle.data['source_bdp_url'], []])
        directive_args.append([bundle.data['destination_bdp_url'], []])


        logger.debug("directive_args=%s" % pformat(directive_args))

        # make the system settings, available to initial stage and merged with run_settings
        system_dict = {u'system': u'settings'}
        system_settings = {u'http://rmit.edu.au/schemas/system/misc': system_dict}

        logger.debug("directive_name=%s" % directive_name)
        logger.debug("directive_args=%s" % directive_args)

        return (platform, directive_name, directive_args, system_settings)


# class DictObject(object):
#     def __init__(self, initial=None):
#         self.__dict__['_data'] = {}

#         if hasattr(initial, 'items'):
#             self.__dict__['_data'] = initial

#     def __getattr__(self, name):
#         return self._data.get(name, None)

#     def __setattr__(self, name, value):
#         self.__dict__['_data'][name] = value

#     def to_dict(self):
#         return self._data

from tastypie.bundle import Bundle

# class ContextInfoResource2(Resource):
#     class Meta:
#         resource_name = 'contextinfo'
#         authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
#         authorization = DjangoAuthorization()
#         allowed_methods = ['get']
#         paginator_class = Paginator
#         qs = models.Context.objects.none()

#     def dehydrate(self, bundle):
#         bundle.data['custom_field'] = "Whatever you want"
#         return bundle

# from tastypie.serializers import Serializer

# class ContextInfoResource(Resource):

#     class Meta:
#         resource_name = 'contextinfo'
#         object_class = str
#         authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
#         authorization = DjangoAuthorization()
#         allowed_methods = ['get']
#         paginator_class = Paginator
#         serializer = Serializer()


#     def obj_get(self, request=None, **kwargs):
#         do = "hello"
#         logger.debug("do=%s" % do)
#         return do

#     def get_object_list(self, request=None, **kwargs):
#         infos = []
#         logger.error('Got Request %s kwargs %s' % (request, kwargs))
#         info = self.obj_get(request, **kwargs)
#         infos.append(info)

#         return infos

#     def detail_uri_kwargs(self, bundle_or_obj):
#         kwargs = {}

#         if isinstance(bundle_or_obj, Bundle):
#         #     kwargs['pk'] = bundle_or_obj.obj.id
#         # else:
#         #     kwargs['pk'] = bundle_or_obj.id
#             kwargs['pk'] = 1
#         else:
#             kwargs['pk'] =  1

#         return kwargs


#     # def obj_get_list(self, request=None, **kwargs):
#     #     return [DictObject(initial={"foo":"bar"})]

#     def obj_get_list(self, request=None, **kwargs):
#         return self.get_object_list(kwargs['bundle'].request)

#     def rollback(self, bundles):
#         pass

class ContextMessageResource(ModelResource):
    context = fields.ForeignKey(ContextResource,
        attribute="context", full=True, null=True)

    class Meta:
        queryset = models.ContextMessage.objects.all()
        resource_name  = "contextmessage"
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get']
        paginator_class = Paginator

    def get_object_list(self, request):
        return models.ContextMessage.objects.filter(context__owner__user=request.user)\
            .order_by('-context__parent__id', 'context__id')




class ContextParameterSetResource(ModelResource):
    context = fields.ForeignKey(ContextResource,
        attribute='context')
    schema = fields.ForeignKey(SchemaResource,
        attribute='schema')

    class Meta:
        queryset = models.ContextParameterSet.objects.all()
        resource_name = 'contextparameterset'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get']

    def get_object_list(self, request):
        return models.ContextParameterSet.objects.filter(context__owner__user=request.user)



class PlatformInstanceResource(ModelResource):
    class Meta:
        queryset = models.PlatformInstance.objects.all()
        resource_name = 'platform'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get']

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)


class PlatformParameterSetResource(ModelResource):
    #platform_name =
    schema = fields.ForeignKey(SchemaResource, attribute='schema', full=True)
    class Meta:
        queryset = models.PlatformParameterSet.objects.all()
        resource_name = 'platformparamset'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get', 'post']
        filtering = {
            'schema': ALL_WITH_RELATIONS,
        }

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)


    def post_list(self, request, **kwargs):
        if django.VERSION >= (1, 4):
            body = request.body
        else:
            body = request.raw_post_data
        deserialized = self.deserialize(request, body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)
        bundle.data['username'] = request.user.username
        #logger.debug('bundle.data=%s' % bundle.data)
        #bundle.data['operation'] = bundle.data['http://rmit.edu.au/schemas/platform/computation/cloud/ec2_based/operation']
        try:
            if 'operation' in bundle.data:
                logger.debug('operation=%s' % bundle.data['operation'])
                if bundle.data['operation'] == 'create':
                    created, message = self.create_platform(bundle)
                    if not created:
                        response = http.HttpConflict()
                        response['message'] = message
                        return response
                elif bundle.data['operation'] == 'update':
                    updated, message  = self.update_platform(bundle)
                    if not updated:
                        response = http.HttpConflict()
                        response['message'] = message
                        return response
                elif bundle.data['operation'] == 'delete':
                    deleted, message = self.delete_platform(bundle)
                    if not deleted:
                        response = http.HttpConflict()
                        response['message'] = message
                        return response
                location = self.get_resource_uri(bundle)
            else:
                return http.HttpBadRequest()
        except Exception, e:
            logger.error(e)
            raise ImmediateHttpResponse(http.HttpBadRequest(e))
        response = http.HttpCreated(location=location)
        response['message'] = message
        return response

    def create_platform(self, bundle):
        username = bundle.data['username']
        schema_namespace = bundle.data['schema']
        parameters = bundle.data['parameters']
        platform_name = bundle.data['platform_name']
        created, message = platform.create_platform(
            platform_name, username, schema_namespace, parameters)
        logger.debug('created=%s' % created)
        return created, message

    def update_platform(self, bundle):
        username = bundle.data['username']
        updated_parameters = bundle.data['parameters']
        platform_name = bundle.data['platform_name']
        updated, message = platform.update_platform(platform_name,
            username, updated_parameters)
        logger.debug('updated=%s' % updated)
        return updated, message

    def delete_platform(self, bundle):
        username = bundle.data['username']
        platform_name = bundle.data['platform_name']
        deleted, message  = platform.delete_platform(platform_name, username)
        logger.debug('deleted=%s' % deleted)
        return deleted, message


class PlatformParameterResource(ModelResource):
    name = fields.ForeignKey(ParameterNameResource, attribute='name', full=True)
    paramset = fields.ForeignKey(PlatformParameterSetResource, attribute='paramset', full=True)

    class Meta:
        queryset = models.PlatformParameter.objects.all()
        resource_name = 'platformparameter'
        # TODO: FIXME: BasicAuth is horribly insecure without using SSL.
        # Digest is better, but configuration proved tricky.
        authentication = MultiAuthentication(ApiKeyAuthentication(), MyBasicAuthentication())
        #authentication = DigestAuthentication()
        authorization = DjangoAuthorization()
        allowed_methods = ['get']
        filtering = {
            'name': ALL_WITH_RELATIONS,
            'paramset': ALL_WITH_RELATIONS,
        }

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)


    def get_object_list(self, request):
        from urlparse import urlparse, parse_qsl
        url = urlparse(request.META['REQUEST_URI'])
        query = parse_qsl(url.query)
        query_settings = dict(x[0:] for x in query)
        logger.debug('query=%s' % query)
        logger.debug('query_settings=%s' % query_settings)
        schema = query_settings['schema']
        return models.PlatformParameter.objects.filter(
            paramset__schema__namespace__startswith=schema)


# class PresetResource(ModelResource):
#     user_profile = fields.ForeignKey(UserProfileResource, 'user_profile')
#     directive = fields.ForeignKey(DirectiveResource, 'directive')

#     class Meta:
#         queryset = models.Preset.objects.all()
#         resource_name = 'preset'
#         allowed_methods = ['get', 'post']
#         authentication = MultiAuthentication(
#             ApiKeyAuthentication(),
#             MyBasicAuthentication())
#         authorization = DjangoAuthorization()

#     def apply_authorization_limits(self, request, object_list):
#         return object_list.filter(user_profile__user=request.user)

#     def get_object_list(self, request):
#         if request.user.is_authenticated():
#             return models.Preset.objects.filter(user_profile__user=request.user)
#         else:
#             return models.Preset.objects.none()


# class PresetParameterSetResource(ModelResource):
#     preset = fields.ForeignKey(PresetResource, attribute='preset')
#     schema = fields.ForeignKey(SchemaResource, attribute='schema')

#     class Meta:
#         queryset = models.PresetParameterSet.objects.all()
#         resource_name = 'presetparameterset'
#         authentication = MultiAuthentication(
#             ApiKeyAuthentication(),
#             MyBasicAuthentication())
#         authorization = DjangoAuthorization()
#         allowed_methods = ['get', 'post', 'put']

#     def apply_authorization_limits(self, request, object_list):
#         return object_list.filter(preset__user_profile__user=request.user)

#     def get_object_list(self, request):
#         return models.PresetParameterSet.objects.filter(
#             preset__user_profile__user=request.user)


# class PresetParameterResource(ModelResource):
#     name = fields.ForeignKey(ParameterNameResource, attribute='name')
#     paramset = fields.ForeignKey(
#         PresetParameterSetResource,
#         attribute='paramset')

#     def apply_authorization_limits(self, request, object_list):
#         return object_list.filter(
#             paramset__preset__user_profile__user=request.user)

#     def obj_create(self, bundle, **kwargs):
#         return super(PresetParameterResource, self).obj_create(bundle,
#             user=bundle.request.user)

#     def get_object_list(self, request):
#         return models.PresetParameter.objects.filter(
#             paramset__preset__user_profile__user=request.user)

#     class Meta:
#         queryset = models.PresetParameter.objects.all()
#         resource_name = 'presetparameter'
#         authentication = MultiAuthentication(
#             ApiKeyAuthentication(), MyBasicAuthentication())
#         authorization = DjangoAuthorization()
#         allowed_methods = ['get', 'put', 'post']


def has_session_key(func):
    def wrapper(request, *args, **kwargs):
        if 'sessionid' in request.COOKIES:
            s = Session.objects.get(pk=request.COOKIES['sessionid'])
            if '_auth_user_id' in s.get_decoded():
                u = User.objects.get(id=s.get_decoded()['_auth_user_id'])
                request.user = u
                return func(request, *args, **kwargs)

        response = HttpResponse()
        response.status_code = 401
        return response
    return wrapper

# def _auth_user(request):
#     if found_session_cookie(request):
#         return None

#     if request.method == 'POST':
#         logger.debug("post=%s" % request.POST)
#         try:
#             username = request.POST['username']
#             password = request.POST['password']
#         except Exception:
#             return HttpResponse('Unauthorized', status=401)
#         user = authenticate(username=username, password=password)
#         logger.debug(user)
#         if user is None:
#             return HttpResponse('Unauthorized', status=401)
#         if not user.is_active:
#             return HttpResponseForbidden()
#         login(request, user)
#         return None

#     if request.method == 'GET':
#         pass

#     return HttpResponseForbidden()


def _preset_as_dict(request, ps):
    p_data = {}
    for pset in models.PresetParameterSet.objects.filter(preset=ps):
        for pp in models.PresetParameter.objects.filter(paramset=pset):
            p_data["%s/%s" % (pp.name.schema.namespace, pp.name.name)] = pp.value
    logger.debug("p_data=%s" % pformat(p_data))
    return p_data


def _delete_preset(request, pk):
    """ Deletes a prest by pk
        e.g., /coreapi/delete/4

    """
    user_profile = models.UserProfile.objects.get(user=request.user)
    try:
        ps = models.Preset.objects.get(id=pk, user_profile=user_profile)
    except models.Preset.DoesNotExist:
        return HttpResponseNotFound()
    except MultipleObjectsReturned:
        return HttpResponseBadRequest()
    ps.delete()
    response = HttpResponse()
    response.status_code = 200
    return response


def _fix_put(request):
    if request.method == "PUT":
        if hasattr(request, '_post'):
            del request._post
            del request._files
        try:
            request.method = "POST"
            request._load_post_and_files()
            request.method = "PUT"
        except AttributeError:
            request.META['REQUEST_METHOD'] = 'POST'
            request._load_post_and_files()
            request.META['REQUEST_METHOD'] = 'PUT'
    request.PUT = request.POST


def _put_pset_by_data(request, data_packet):
    try:
        direct_name = data_packet['direct_name']
        data = data_packet['data']
        name = data_packet['name']
    except IndexError:
        return HttpResponseBadRequest()
    logger.debug("data_packet=%s" % pformat(data_packet))

    logger.debug("name=%s" % name)
    try:
        user_profile = models.UserProfile.objects.get(user=request.user)
    except models.UserProfile.DoesNotExist:
        return HttpResponseNotFound(request.user)
    logger.debug("user_profile=%s" % user_profile)
    if not user_profile:
        return HttpResponseNotFound()
    try:
        directive = models.Directive.objects.get(
            name=direct_name,
            hidden=False)
    except models.Directive.DoesNotExist:
        return HttpResponseNotFound(direct_name)
    logger.debug("directive=%s" % directive)
    if not directive:
        return HttpResponseNotFound()

    ps = models.Preset.objects.create(
        name=name,
        user_profile=user_profile,
        directive=directive)
    logger.debug("ps=%s" % ps)

    parameters_data = data
    parameters = json.loads(parameters_data)
    ranking = 0
    # TODO: we don't check types here
    # for pset in list(parameters):
    #     logger.debug("pset=%s" % pset)
    #     pset_data = {}
    #     schema_name = None

    new_pset = models.PresetParameterSet.objects.create(
        preset=ps, ranking=ranking)

    logger.debug("new_pset=%s" % new_pset)
    for pp_k, pp_v in dict(parameters).items():
        logger.debug("pp_k=%s,pp_v=%s" % (pp_k, pp_v))
        schema_name, key = os.path.split(pp_k)
        # Assume all parameters in set from same schema
        logger.debug("schema_name=%s" % schema_name)
        schema = None
        try:
            schema = models.Schema.objects.get(
                namespace=schema_name)
        except models.Schema.DoesNotExist:
            return HttpResponseNotFound(schema_name)
        logger.debug("schema=%s" % schema)
        logger.debug("new_pset=%s" % new_pset)
        logger.debug("new_pset.id=%s" % new_pset.id)
        p_name = os.path.basename(pp_k)
        logger.debug("p_name=%s" % p_name)
        new_name = None
        try:
            # could cache this value for speed
            new_name = models.ParameterName.objects.get(
                schema=schema,
                name=p_name)
        except models.Schema.DoesNotExist:
            return HttpResponseNotFound(p_name)

        logger.debug("new_name=%s" % new_name)
        try:
            new_p = models.PresetParameter.objects.create(
                name=new_name,
                paramset=new_pset, value=pp_v)
        except Exception, e:
            logger.error(e)
            return HttpResponseBadRequest()

        new_p.value = pp_v
        new_p.save()
        # logger.debug("new_p=%s" % new_p)
        logger.debug("done")
        ranking += 1

    response = HttpResponse()
    response.status_code = 201
    response['location'] = reverse('preset_detail', args=[ps.pk])
    return response


@has_session_key
@logged_in_or_basicauth()
def preset_list(request):

    def _post_pset_by_data(request, data_packet):
        try:
            direct_name = data_packet['direct_name']
            data = data_packet['data']
            name = data_packet['name']
        except IndexError:
            return HttpResponseBadRequest()
        logger.debug("data_packet=%s" % pformat(data_packet))

        logger.debug("name=%s" % name)
        try:
            user_profile = models.UserProfile.objects.get(user=request.user)
        except models.UserProfile.DoesNotExist:
            return HttpResponseNotFound(request.user)
        logger.debug("user_profile=%s" % user_profile)
        if not user_profile:
            return HttpResponseNotFound()
        try:
            directive = models.Directive.objects.get(
                name=direct_name,
                hidden=False)
        except models.Directive.DoesNotExist:
            return HttpResponseNotFound(direct_name)
        logger.debug("directive=%s" % directive)
        if not directive:
            return HttpResponseNotFound()
        try:
            ps = models.Preset.objects.get(
                name=name,
                user_profile=user_profile)
        except models.Preset.DoesNotExist:
            pass
        else:
            return HttpResponseBadRequest()

        ps = models.Preset.objects.create(
            name=name,
            user_profile=user_profile,
            directive=directive)
        logger.debug("ps=%s" % ps)

        parameters_data = data
        parameters = json.loads(parameters_data)
        logger.debug("parameters=%s" % pformat(parameters))
        ranking = 0
        # TODO: we don't check types here
        # for pset in list(parameters):
        #     logger.debug("pset=%s" % pset)
        #     pset_data = {}
        #     schema_name = None

        new_pset = models.PresetParameterSet.objects.create(
            preset=ps, ranking=ranking)

        logger.debug("new_pset=%s" % new_pset)
        for pp_k, pp_v in dict(parameters).items():
            logger.debug("pp_k=%s,pp_v=%s" % (pp_k, pp_v))
            schema_name, key = os.path.split(pp_k)
            # Assume all parameters in set from same schema
            logger.debug("schema_name=%s" % schema_name)
            schema = None
            try:
                schema = models.Schema.objects.get(
                    namespace=schema_name)
            except models.Schema.DoesNotExist:
                return HttpResponseNotFound(schema_name)
            logger.debug("schema=%s" % schema)
            logger.debug("new_pset=%s" % new_pset)
            logger.debug("new_pset.id=%s" % new_pset.id)
            p_name = os.path.basename(pp_k)
            logger.debug("p_name=%s" % p_name)
            new_name = None
            try:
                # could cache this value for speed
                new_name = models.ParameterName.objects.get(
                    schema=schema,
                    name=p_name)
            except models.Schema.DoesNotExist:
                return HttpResponseNotFound(p_name)

            logger.debug("new_name=%s" % new_name)
            try:
                models.PresetParameter.objects.create(
                    name=new_name,
                    paramset=new_pset,
                    value=pp_v)
            except Exception, e:
                logger.error(e)
                return HttpResponseBadRequest()
            # logger.debug("new_p=%s" % new_p)
            logger.debug("done")
            ranking += 1

        # TODO: return id of new preset
        response = HttpResponse()
        response['location'] = reverse('preset_detail', args=[ps.pk])
        response.status_code = 201
        return response

    def post_preset(request):
        """
            Create a new Preset using POST
            e.g., /coreapi/preset/   {name:"presetname", directive="name of directive",
                data:'dictionary of full  schema/name strings and values'}
            returns location
        """

        name = request.POST['name']
        data = request.POST['data']
        direct_name = request.POST['directive']
        return _post_pset_by_data(request, {
            'name': name,
            'data': data,
            'direct_name': direct_name})

    # def put_preset(request):
    #     response = delete_preset(request, pk)
    #     logger.debug("response=%s" % response.status_code)
    #     if response.status_code != 200:
    #         return HttpResponseBadRequest()
    #     logger.debug("response=%s" % response)

    #     _fix_put(request)
    #     logger.debug("put=%s" % request.PUT)
    #     name = request.PUT['name']
    #     data = request.PUT['data']
    #     direct_name = request.PUT['directive']
    #     response = _put_pset_by_data(request, {
    #                 'name': name,
    #                 'data': data,
    #                 'direct_name': direct_name})
    #     if response.status_code == 201:
    #         response = HttpResponse()
    #         response.status_code = 200
    #         return response
    #     return HttpResponseBadRequest()

    # def delete_preset(request, pk):
    #     user_profile = models.UserProfile.objects.get(user=request.user)
    #     try:
    #         ps = models.Preset.objects.get(id=pk, user_profile=user_profile)
    #     except models.Preset.DoesNotExist:
    #         return HttpResponseNotFound()
    #     except MultipleObjectsReturned:
    #         return HttpResponseBadRequest()
    #     ps.delete()
    #     response = HttpResponse()
    #     response.status_code = 200
    #     return response

    def put_preset(request):
        """
            Updates a specific preset with new values based on "name" key
            e.g., /core/api/preset  {name:"...", directive:"...","data":"..."}
            deletes preset record which matches
            "location" contains uri of new record
        """
        _fix_put(request)
        name = request.PUT['name']
        data = request.PUT['data']
        direct_name = request.PUT['directive']

        try:
            ps = models.Preset.objects.get(name=name)
        except models.Preset.DoesNotExist:
            logger.info("preset not found")
        else:
            response = _delete_preset(request, ps.pk)
            logger.debug("response=%s" % response.status_code)
            # TODO: if object not there, not an error
            if response.status_code != 200:
                return HttpResponseBadRequest()
            logger.debug("response=%s" % response)

        logger.debug("put=%s" % request.PUT)
        response = _put_pset_by_data(request, {
                    'name': name,
                    'data': data,
                    'direct_name': direct_name})
        if response.status_code == 201:
            response = HttpResponse()
            response.status_code = 200
            return response
        return HttpResponseBadRequest()

    def get_preset(request):
        """
        Retrieve current preset
        e.g.,   /coreapi/preset/
                returns set of all presets
                /coreapi/preset/?name=foo
                returns preset with name field equals 'foo'
        """
        try:
            user_profile = models.UserProfile.objects.get(user=request.user)
        except models.UserProfile.DoesNotExist:
            return HttpResponseNotFound()
        name = request.GET.get('name', '')
        if name:
            # return by preset name
            try:
                ps = models.Preset.objects.get(
                    name=name,
                    user_profile=user_profile)
            except models.Preset.DoesNotExist:
                return HttpResponseNotFound()
            data = {}
            data['id'] = ps.id
            data['name'] = ps.name
            data['directive'] = ps.directive.name
            data['user'] = user_profile.user.username
            data['parameters'] = _preset_as_dict(request, ps)
        else:
            # return complete list
            user = user_profile.user.username
            data = []
            ps = models.Preset.objects.filter(
                    user_profile=user_profile)
            for p in ps:
                p_data = {}
                logger.debug("p=%s" % p)
                p_data['id'] = p.id
                p_data['name'] = p.name
                p_data['directive'] = p.directive.name
                p_data['user'] = user
                p_data['parameters'] = _preset_as_dict(request, p)
                data.append(p_data)

        logger.debug("data=%s" % data)
        return HttpResponse(json.dumps(data),
                        mimetype='application/json')

    for m, f in {'GET': get_preset, 'POST': post_preset, 'PUT': put_preset}.items():
        if request.method == m:
            response = f(request)
            logger.debug("response=%s" % response.status_code)
            return response
    return HttpResponseNotAllowed(['GET', 'POST', 'PUT'])


@has_session_key
@logged_in_or_basicauth()
def preset_detail(request, pk):

    def get_preset(request, pk):
        """
            Returns details for specific preset via GET
            e.g., /coreapi/preset/5/
        """

        user_profile = models.UserProfile.objects.get(user=request.user)
        try:
            ps = models.Preset.objects.get(id=pk, user_profile=user_profile)
        except models.Preset.DoesNotExist:
            return HttpResponseNotFound()
        except MultipleObjectsReturned:
            return HttpResponseBadRequest()
        data = {}
        data['id'] = ps.id
        data['name'] = ps.name
        data['directive'] = ps.directive.name
        data['user'] = user_profile.user.username
        data['parameters'] = _preset_as_dict(request, pk)
        return HttpResponse(json.dumps(data),
                        mimetype='application/json')

    def put_preset(request, pk):
        """
            Updates a specific preset with new values
            e.g., /core/api/preset/5  {name:"...", directive:"...","data":"..."}
            deletes preset/5 record
            "location" contains uri of new record
        """
        response = _delete_preset(request, pk)
        logger.debug("response=%s" % response.status_code)
        # TODO: if object not there, not an error
        if response.status_code != 200:
            return HttpResponseBadRequest()
        logger.debug("response=%s" % response)

        _fix_put(request)
        logger.debug("put=%s" % request.PUT)
        name = request.PUT['name']
        data = request.PUT['data']
        direct_name = request.PUT['directive']
        response = _put_pset_by_data(request, {
                    'name': name,
                    'data': data,
                    'direct_name': direct_name})
        if response.status_code == 201:
            response.status_code = 200
            # TODO: return id of new item
            return response
        return HttpResponseBadRequest()

    for m, f in {'GET': get_preset, 'PUT': put_preset,
            'DELETE': _delete_preset}.items():
        if request.method == m:
            return f(request, pk)
    return HttpResponseNotAllowed(['GET', 'POST', 'DELETE'])
