# Copyright (C) 2014, RMIT University

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
import logging
import json
import itertools
import ast
from pprint import pformat
from urllib2 import URLError, HTTPError

import requests
import dateutil.parser
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.views.generic.base import TemplateView
from django.core.urlresolvers import reverse
from django.contrib.auth import logout
from django.http import (
    HttpResponseRedirect, HttpResponsePermanentRedirect
    )
from django.template import RequestContext
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.contrib import messages
from django.utils.datastructures import SortedDict
from django.core.validators import ValidationError
from django.views.generic.edit import FormView
from django.views.generic import DetailView
from django.shortcuts import render
from django import forms
from django.http import Http404

from tastypie.models import ApiKey
from chiminey.platform import manage
from chiminey.simpleui import validators
from chiminey.simpleui.hrmc.hrmcsubmit import HRMCSubmitForm
from chiminey.simpleui.makeform import MakeSubmitForm
from chiminey.simpleui.hrmc.copy import CopyForm

from pprint import pformat



#TODO,FIXME: simpleui shouldn't refer to anything in smartconnectorscheduler
#and should be using its own models and use the REST API for all information.
from chiminey.smartconnectorscheduler import models
from chiminey.smartconnectorscheduler.errors import deprecated

logger = logging.getLogger(__name__)
from django.conf import settings as django_settings


POPPED_KEYS = ['filters', 'private_key_path', 'operation', 'vm_image_size', 'name']

api_host = django_settings.APIHOST


subtype_validation = {
    'password': ('password', validators.validate_string_not_empty, forms.PasswordInput, None),
    'hidden': ('natural number', validators.validate_hidden, None, None),
    'natural': ('natural number', validators.validate_natural_number, None, None),
    'string': ('string', validators.validate_string, None, None),
    'string_not_empty': ('string_not_empty', validators.validate_string_not_empty, None, None),
    'whole': ('whole number', validators.validate_whole_number, None, None),
    'nectar_platform': ('NeCTAR platform name', validators.validate_platform_url, None, None),
    'storage_bdpurl': ('Storage resource name with optional offset path', validators.validate_platform_url, forms.TextInput, 255),
    'output_relative_path': ('Storage resource name with optional offset path', validators.validate_output_relative_path, forms.TextInput, 255),
    'input_relative_path': ('Storage resource name with optional offset path', validators.validate_input_relative_path, forms.TextInput, 255),
    'even': ('even number', validators.validate_even_number, None, None),
    'bdpurl': ('BDP url', validators.validate_BDP_url, forms.TextInput, 255),
    'float': ('floading point number', validators.validate_float_number, None, None),
    'jsondict': ('JSON Dictionary', validators.validate_jsondict, forms.Textarea(attrs={'cols': 30, 'rows': 5}), None),
    'float': ('floating point number', validators.validate_float_number, None, None),
    'bool': ('On/Off', validators.validate_bool, None,  None),
    'platform': ('platform', validators.validate_platform_url, forms.Select(),  None),
    #'mytardis': ('MyTardis platform name', validators.validate_platform_url, forms.Select(),  None), #TODO MyTardis validation should occur only if curation is ON. Include this logic in the validation
    'mytardis': ('MyTardis name', None, forms.Select(),  None),
    'choicefield': ('choicefield', None, forms.Select(),  None),
    'timedelta': ('time delta: try 00:10:00, or 10 mins', validators.validate_timedelta, None, None),

}


def get_subtype_as_choices():
    res = [('', "NONE")]
    for k in subtype_validation:
        res.append((k, "%s (%s) " % (k, subtype_validation[k][0])))
    return res


clean_rules = {
    'addition': validators.check_addition
}


def bdp_account_settings(request):
    api_key = ApiKey.objects.get(user=request.user)
    return render(request,
                  'accountsettings/bdpaccount.html',
                  {'key': api_key.key})


def computation_platform_settings(request):
    resources_list = [('cluster_form', 'cluster/pbs_based', 'cluster', "HPC", 'true' ),\
    ('cloud_form', 'cloud/ec2-based', 'cloud', 'Cloud', 'true'),\
    ('jenkins_form','testing/jenkins_based', 'jenkins', 'Continuous Integration', 'false' ),\
    ('bigdata_form', 'bigdata/hadoop', 'bigdata', 'Analytics', 'true')]

    resource_namespace_prefix = "%s/platform/computation" % django_settings.SCHEMA_PREFIX
    post_response_redirect = 'computation-platform-settings'
    resources_overall_id = 'computation_platforms'

    return manage_platforms(request, resources_list=resources_list, resource_namespace_prefix=resource_namespace_prefix,\
    post_response_redirect=post_response_redirect, resources_overall_id=resources_overall_id, resource_type='compute')


def storage_platform_settings(request):
    resources_list = [('unix_form', 'filesystem/rfs', 'filesystem', "File System", 'true' ), \
    ('mytardis_form', 'curation/mytardis', 'curation', 'Data Curation Service', 'true')]

    resource_namespace_prefix = "%s/platform/storage" % django_settings.SCHEMA_PREFIX
    post_response_redirect = 'storage-platform-settings'
    resources_overall_id = 'storage_platforms'

    return manage_platforms(request, resources_list=resources_list, resource_namespace_prefix=resource_namespace_prefix,\
    post_response_redirect=post_response_redirect, resources_overall_id=resources_overall_id, resource_type='storage')



def manage_platforms(request, resources_list=[], resource_namespace_prefix='',post_response_redirect='', resources_overall_id='', resource_type=''):
    new_form_data = {}
    resources = {}
    for k, v in new_form_data.items():
        resources[k] = {k: {'form': v[0], 'data': v[1], 'advanced_ops': 'false'}}
    for field_name, ns_suffix, group, group_name, ops in resources_list:
        namespace = "%s/%s" % (resource_namespace_prefix, ns_suffix)
        params = _get_platform_params(request, namespace)

        form, form_data= make_directive_form(
            platform_params=params,
            username=request.user.username)

        new_form_data[field_name] = (form, form_data)
        resources[group] = {'form': form, 'data': form_data, 'advanced_ops': ops, 'group_name': group_name}

        if request.method == 'POST':

            form, form_data= make_directive_form(
                request=request.POST,
                platform_params=params,
                username=request.user.username)
            new_form_data[field_name] = (form, form_data)
            if form.is_valid():
                post_platform(namespace, form.cleaned_data, request)
                return HttpResponsePermanentRedirect(reverse(post_response_redirect))

    #FIXME: consider using non-locahost URL for api_host
    url = "%s/api/v1/platformparameter/?format=json&limit=0&schema=%s" % (api_host, resource_namespace_prefix)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    headers = {'content-type': 'application/json'}
    try:
        r = requests.get(url, headers=headers, cookies=cookies)
    except HTTPError as e:
        logger.debug('The server couldn\'t fulfill the request. %s' % e)
        logger.debug('Error code: ', e.code)
    except URLError as e:
        logger.debug('We failed to reach a server. %s' % e)
        logger.debug('Reason: ', e.reason)
    else:
        logger.debug('everything is fine')
        GET_data = r.json()
        storage_platforms, all_headers = filter_computation_platforms(GET_data)
        logger.debug(storage_platforms)
    logger.debug("new_form_data=%s" % pformat(new_form_data))
    # logger.debug("cloud_form_get=%s" % cloudform)
    # logger.debug("cloud_data_get=%s" % form_data)
    # logger.debug("nci_form_get=%s" % cluster_form)
    res = {resources_overall_id: storage_platforms,
                    'all_headers': all_headers}
    res.update(dict([(x,y[0]) for x,y in new_form_data.items()]))
    logger.debug("res=%s" % pformat(res))
    logger.debug('resources_overall_id=%s' % res[resources_overall_id])
    hide_resource_fields(res[resources_overall_id], POPPED_KEYS)
    hide_resource_header_fields(res['all_headers'], POPPED_KEYS)

    logger.debug("new res=%s" % pformat(res))

    #return render(request, 'accountsettings/computationplatform.html',res)

    # new_form_data[field_name] = (form, form_data)


    return render(request, 'accountsettings/resources.html',
                  {'all_headers': all_headers,
                   'resources': resources,
                   'formtypes': {'create':'Register', 'update': 'Update', 'delete': 'Remove'},
                    'resourcetype': resource_type
                   })



def hide_resource_fields(dictionary, popped_keys):
    if isinstance(dictionary, dict):
       for a, b in dictionary.items():
           if isinstance(b, dict):
                hide_resource_fields(b, popped_keys)
           else:
               if a in popped_keys:
                    dictionary.pop(a)
               elif 'ec2_secret_key' in a:
                    dictionary[a] = '*****'

def hide_resource_header_fields(dictionary, popped_keys):
    logger.debug('hide_resource_done=%s' % dictionary)
    for a, b in dictionary.items():
        new_dic = {}
        for k, v in b.items():
            if isinstance(k, tuple):
                temp_list = list(k)
                z= [x for x in temp_list if x not in popped_keys]
                new_dic[tuple(z)] = v
            else:
                 new_dic[k] = v
        dictionary[a] = new_dic
    return dictionary




def _get_platform_params(request, namespace):
    schema_id = get_schema_id(request, namespace)
    platform_params = []
    schema_info = get_schema_info(request, schema_id)
    parameters = get_parameters(request, schema_id)
    platform_params.append((schema_info, parameters))
    platform_params = add_form_fields(request, platform_params)
    logger.debug('schema_id=%s, platform_params=%s' % (schema_id,platform_params))
    return platform_params



def post_platform(schema, form_data, request, type=None):
    logger.debug('operation=%s' % form_data['operation'])
    url = "%s/api/v1/platformparamset/?format=json" % api_host
    # pass the sessionid cookie through to the internal API
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    headers = {'content-type': 'application/json'}
    platform_name = form_data['platform_name']

    if form_data['operation'] == 'update':
        platform_name = form_data['filters']
        form_data['filters'] = ''
    data = json.dumps({'operation': form_data['operation'],
                       'parameters': form_data,
                       'schema': schema,
                       'platform_name': platform_name})
    logger.debug("post info: url %s, data %s, headers %s" % (url, data, headers))
    r = requests.post(url,
        data=data,
        headers=headers,
        cookies=cookies)
    if r.status_code != 201:
        logger.debug(r.text)
        if r.status_code == 409:
            messages.error(request, "%s" % r.headers['message'])
        else:
            messages.error(request, "Task Failed with status code %s: %s"
                % (r.status_code, r.text))
        return False
    else:
        messages.success(request, "%s" % r.headers['message'])
    # TODO: need to check for status_code and handle failures.


#fixme revise this method ---again
def filter_computation_platforms(GET_json_data):
    platform_parameters_objects = GET_json_data['objects']
    computation_platforms = {}
    for i in platform_parameters_objects:
        schema = i['paramset']['schema']['namespace']
        computation_platforms[schema] = {}

    for i in platform_parameters_objects:
        schema = i['paramset']['schema']['namespace']
        paramset_id = i['paramset']['id']
        computation_platforms[schema][paramset_id] = {}
        computation_platforms[schema][paramset_id]['name'] = str(
            i['paramset']['name'])

    for i in platform_parameters_objects:
        schema = i['paramset']['schema']['namespace']
        paramset_id = i['paramset']['id']
        name = i['name']['name']

        if name == 'password':
            value = ''
        else:
            value = i['value']

        #value = i['value']
        computation_platforms[schema][paramset_id][str(name)] = str(value)
    headers = {}
    all_headers = {}
    logger.debug('computation=%s' % computation_platforms)
    for i, j in computation_platforms.items():
        headers[i] = []
        logger.debug('j=%s' % j)
        platform_type = j.itervalues().next()['platform_type']
        logger.debug('this_platform_type=%s' % platform_type)

        params = []
        for a, b in j.items():
            for c, d in b.items():
                params.append(c)
            break
        headers[i] = params
        all_headers[platform_type] = {tuple(params): j}
        logger.debug(platform_type)
    logger.debug(all_headers)
    return computation_platforms, all_headers


# TODO: Remove UserProfile access in the API, as most of data
# represented in schema
@deprecated
class UserProfileParameterListView(ListView):
    model = models.UserProfileParameter
    template_name = "list_userprofileparameter.html"

    def get_queryset(self):
            return models.UserProfileParameter.objects.filter(
                paramset__user_profile__user=self.request.user)


class AboutView(TemplateView):
    template_name = "home.html"


class CreateUserProfileParameterView(CreateView):
    model = models.UserProfileParameter
    template_name = "edit_userprofileparameter.html"

    def get_success_url(self):
        return reverse('userprofileparameter-list')

    def get_context_data(self, **kwargs):
        context = super(CreateUserProfileParameterView,
                        self).get_context_data(**kwargs)
        context['action'] = reverse('userprofileparameter-new')
        return context


@deprecated
class UpdateUserProfileParameterView(UpdateView):
    model = models.UserProfileParameter
    template_name = "edit_userprofileparameter.html"

    def get_success_url(self):
        return reverse('userprofileparameter-list')

    def get_context_data(self, **kwargs):
        context = super(UpdateUserProfileParameterView,
            self).get_context_data(**kwargs)
        context['action'] = reverse('userprofileparameter-edit',
                                    kwargs={'pk': self.get_object().id})
        return context

    def get_object(self):
        object = super(UpdateUserProfileParameterView, self).get_object()
        if object.paramset.user_profile.user == self.request.user:
            return object
        else:
            raise Http404


class DeleteUserProfileParameterView(DeleteView):
    model = models.UserProfileParameter
    template_name = 'delete_userprofileparameter.html'

    def get_success_url(self):
        return reverse('userprofileparameter-list')

    def get_object(self):
        object = super(DeleteUserProfileParameterView, self).get_object()
        if object.paramset.user_profile.user == self.request.user:
            return object
        else:
            raise Http404


def logout_page(request):
    """
    Log users out and re-direct them to the main page.
    """
    logout(request, next_page="/")
    return HttpResponseRedirect('/')


class ContextList(ListView):
    model = models.Context
    template_name = "list_jobs.html"

    def get_queryset(self):
        return models.Context.objects.filter(owner__user=self.request.user).order_by('-id')


class AccountSettingsView(FormView):
    template_name = "accountsettings/computationplatform.html"
    #success_url = '/accountsettings/computationplatform.html'

    def get_success_url(self):
        return reverse('hrmcjob-list')


@deprecated
# Replaced by button in job_list
class FinishedContextUpdateView(UpdateView):
    model = models.Context
    template_name = "edit_context.html"

    def get_success_url(self):
        return reverse('hrmcjob-list')

    # def get_context_data(self, **kwargs):
    #     context = super(UpdateUserProfileParameterView, self).get_context_data(**kwargs)
    #     context['action'] = reverse('userprofileparameter-edit', kwargs={'pk': self.get_object().id})
    #     return context

    def get_object(self):
        object = super(FinishedContextUpdateView, self).get_object()
        if object.owner.user == self.request.user:
            return object
        else:
            raise Http404

# @deprecated
# class ListDirList(TemplateView):

#     template_name = "listdir.html"

#     def get_context_data(self, **kwargs):
#         context = super(ListDirList, self).get_context_data(**kwargs)

#         url = smartconnectorscheduler.get_url_with_credentials({}, ".", is_relative_path=True)
#         file_paths = [x[1:] for x in hrmcstages.list_all_files(url)]
#         context['paths'] = file_paths
#         return context


class ContextView(DetailView):
    model = models.Context
    template_name = 'view_context.html'

    def get_context_data(self, **kwargs):
        context = super(ContextView, self).get_context_data(**kwargs)

        INPUT_SCHEMA_PREFIX = django_settings.SCHEMA_PREFIX + "/input"
        context_ps = models.ContextParameterSet.objects.filter(context=self.object)
        cpset = list(itertools.chain(
               context_ps.filter(
                   schema__namespace__startswith=INPUT_SCHEMA_PREFIX).order_by('-ranking'),
               context_ps.exclude(
                   schema__namespace__startswith=INPUT_SCHEMA_PREFIX)))
        res = []
        context['stage'] = self.object.current_stage.name
        for cps in cpset:
            res2 = {}
            for cp in models.ContextParameter.objects.filter(paramset=cps):
                res2[cp.name.name] = [cp.value, cp.name.help_text, cp.name.subtype]
            if cps.schema.name:
                res.append(("%s (%s) " % (cps.schema.name, cps.schema.namespace), res2))
            else:
                res.append((cps.schema.namespace, res2))
        context['settings'] = res
        return context

    def get_object(self):
            object = super(ContextView, self).get_object()
            if object.owner.user == self.request.user:
                return object
            else:
                raise Http404


class ContextList(ListView):
    model = models.Context
    template_name = "list_jobs.html"

    def get_queryset(self):
        return models.Context.objects.filter(
            owner__user=self.request.user).order_by('-id')


@deprecated
class HRMCSubmitFormView(FormView):
    template_name = 'hrmc.html'
    form_class = HRMCSubmitForm
    success_url = '/jobs'
    hrmc_schema = django_settings.SCHEMA_PREFIX + "/hrmc/"
    system_schema = django_settings.SCHEMA_PREFIX + "/system/misc/"

    initial = {'number_vm_instances': 1,
        'minimum_number_vm_instances': 1,
        'iseed': 42,
        'input_location': 'file://172.16.231.130/myfiles/input',
        'optimisation_scheme': "MC",
        'threshold': "[2]",
        'error_threshold': "0.03",
        'max_iteration': 10,
        'pottype': 1,
        'experiment_id': 0,
        'output_location': 'file://local@172.16.231.130/hrmcrun'
        }

    # This method is called when valid form data has been POSTed.
    # It should return an HttpResponse.
    def form_valid(self, form):
        # An example of using the REST API to control the system, rather than
        # talking directly to the models in smartconnectorscheduler.
        # TODO: do the same for other parts of UI, e.g., user settings form
        # should call user_setttings API endpoint.
        #FIXME: consider using non-locahost URL for api_host
        url = "%s/api/v1/context/?format=json" % api_host

        logger.debug("self.request.user.username=%s" % self.request.user.username)
        logger.debug("self.request.user.username=%s" % self.request.user.password)

        # pass the sessionid cookie through to the internal API
        cookies = dict(self.request.COOKIES)
        logger.debug("cookies=%s" % cookies)
        headers = {'content-type': 'application/json'}
        data = json.dumps({'smart_connector': 'hrmc',
                    self.hrmc_schema + 'number_vm_instances': form.cleaned_data['number_vm_instances'],
                    self.hrmc_schema + 'minimum_number_vm_instances': form.cleaned_data['minimum_number_vm_instances'],
                    self.hrmc_schema + u'iseed': form.cleaned_data['iseed'],
                    self.hrmc_schema + 'input_location':  form.cleaned_data['input_location'],
                    self.hrmc_schema + 'optimisation_scheme': form.cleaned_data['optimisation_scheme'],
                    self.hrmc_schema + 'threshold': str(form.cleaned_data['threshold']),
                    self.hrmc_schema + 'error_threshold': str(form.cleaned_data['error_threshold']),
                    self.hrmc_schema + 'max_iteration': form.cleaned_data['max_iteration'],
                    self.hrmc_schema + 'pottype': form.cleaned_data['pottype'],
                    self.hrmc_schema + 'experiment_id': form.cleaned_data['experiment_id'],
                    self.system_schema + 'output_location': form.cleaned_data['output_location']})
        r = requests.post(url,
            data=data,
            headers=headers,
            cookies=cookies)

        # TODO: need to check for status_code and handle failures.

        logger.debug("r.json=%s" % r.json)
        logger.debug("r.text=%s" % r.text)
        logger.debug("r.headers=%s" % r.headers)
        header_location = r.headers['location']
        logger.debug("header_location=%s" % header_location)
        new_context_uri = header_location[len(api_host):]
        logger.debug("new_context_uri=%s" % new_context_uri)

        return super(HRMCSubmitFormView, self).form_valid(form)


@deprecated
def submit_sweep_job(request, form, schemas):

    #FIXME: consider using non-locahost URL for api_host
    url = "%s/api/v1/context/?format=json" % api_host

    logger.debug("request.user.username=%s" % request.user.username)
    logger.debug("request.user.username=%s" % request.user.password)

    # pass the sessionid cookie through to the internal API
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    headers = {'content-type': 'application/json'}

    data = json.dumps({'smart_connector': 'sweep',
                schemas['hrmc_schema'] + 'number_vm_instances': form.cleaned_data['number_vm_instances'],
                schemas['hrmc_schema'] + 'minimum_number_vm_instances': form.cleaned_data['minimum_number_vm_instances'],
                schemas['hrmc_schema'] + u'iseed': form.cleaned_data['iseed'],
                schemas['sweep_schema'] + 'input_location':  form.cleaned_data['input_location'],
                schemas['hrmc_schema'] + 'optimisation_scheme': form.cleaned_data['optimisation_scheme'],
                schemas['hrmc_schema'] + 'fanout_per_kept_result': form.cleaned_data['fanout_per_kept_result'],
                schemas['hrmc_schema'] + 'threshold': str(form.cleaned_data['threshold']),
                schemas['hrmc_schema'] + 'error_threshold': str(form.cleaned_data['error_threshold']),
                schemas['hrmc_schema'] + 'max_iteration': form.cleaned_data['max_iteration'],
                schemas['hrmc_schema'] + 'pottype': form.cleaned_data['pottype'],
                #'experiment_id': form.cleaned_data['experiment_id'],
                schemas['sweep_schema'] + 'sweep_map': form.cleaned_data['sweep_map'],
                schemas['sweep_schema'] + 'directive': 'hrmc',
                schemas['mytardis_schema'] + 'mytardis_platform': form.cleaned_data['mytardis_platform'],
                #'run_map': form.cleaned_data['run_map'],
                schemas['run_schema'] + 'run_map': "{}",
                schemas['system_schema'] + 'output_location': form.cleaned_data['output_location'],
                django_settings.SCHEMA_PREFIX + '/bdp_userprofile/username': request.user.username})

    logger.debug("data=%s" % data)
    r = requests.post(url,
        data=data,
        headers=headers,
        cookies=cookies)

     # TODO: need to check for status_code and handle failures.

    logger.debug("r.json=%s" % r.json)
    logger.debug("r.text=%s" % r.text)
    logger.debug("r.headers=%s" % r.headers)
    header_location = r.headers['location']
    logger.debug("header_location=%s" % header_location)
    new_context_uri = header_location[len(api_host):]
    logger.debug("new_context_uri=%s" % new_context_uri)


@deprecated
class MakeSubmitFormView(FormView):
    template_name = 'make.html'
    form_class = MakeSubmitForm
    success_url = '/jobs'
    system_schema = django_settings.SCHEMA_PREFIX + "/system/misc/"

    initial = {
        'input_location': 'file://local@172.16.231.130/myfiles/vasppayload',
        'output_location': 'file://local@172.16.231.130/myfiles/vaspoutput',
        'experiment_id': 0,
        'sweep_map': '{"num_kp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "encut": [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700]}'
    }

    # This method is called when valid form data has been POSTed.
    # It should return an HttpResponse.
    def form_valid(self, form):
        #FIXME: consider using non-locahost URL for api_host
        url = "%s/api/v1/context/?format=json" % api_host

        logger.debug("self.request.user.username=%s" % self.request.user.username)
        logger.debug("self.request.user.username=%s" % self.request.user.password)

        # pass the sessionid cookie through to the internal API
        cookies = dict(self.request.COOKIES)
        logger.debug("cookies=%s" % cookies)
        headers = {'content-type': 'application/json'}

        remotemake_schema = django_settings.SCHEMA_PREFIX + "/remotemake/"
        make_schema = django_settings.SCHEMA_PREFIX + "/stages/make/"
        data = json.dumps({'smart_connector': 'remotemake',
                    remotemake_schema + 'input_location':  form.cleaned_data['input_location'],
                    remotemake_schema + 'experiment_id': form.cleaned_data['experiment_id'],
                    make_schema + 'sweep_map': form.cleaned_data['sweep_map'],
                    self.system_schema + 'output_location': form.cleaned_data['output_location']})

        r = requests.post(url,
            data=data,
            headers=headers,
            cookies=cookies)

         # TODO: need to check for status_code and handle failures.

        logger.debug("r.json=%s" % r.json)
        logger.debug("r.text=%s" % r.text)
        logger.debug("r.headers=%s" % r.headers)
        logger.debug("data=%s" % data)
        header_location = r.headers['location']
        logger.debug("header_location=%s" % header_location)
        new_context_uri = header_location[len(api_host):]
        logger.debug("new_context_uri=%s" % new_context_uri)

        return super(MakeSubmitFormView, self).form_valid(form)


@deprecated
class CopyFormView(FormView):
    template_name = 'copy.html'
    form_class = CopyForm
    success_url = '/jobs'

    initial = {'source_bdp_url': 'file://local@172.16.231.130/myfiles/sourcedir',
        'destination_bdp_url': 'file://local@172.16.231.130/myfiles/destdir',
        }

    # This method is called when valid form data has been POSTed.
    # It should return an HttpResponse.
    def form_valid(self, form):
        #FIXME: consider using non-locahost URL for api_host
        url = "%s/api/v1/context/?format=json" % api_host

        logger.debug("self.request.user.username=%s" % self.request.user.username)
        logger.debug("self.request.user.username=%s" % self.request.user.password)

        # pass the sessionid cookie through to the internal API
        cookies = dict(self.request.COOKIES)
        logger.debug("cookies=%s" % cookies)
        headers = {'content-type': 'application/json'}

        data = json.dumps({'smart_connector': 'copydir',
                           'source_bdp_url': form.cleaned_data['source_bdp_url'],
                           'destination_bdp_url': form.cleaned_data['destination_bdp_url']
                           })

        r = requests.post(url,
            data=data,
            headers=headers,
            cookies=cookies)

         # TODO: need to check for status_code and handle failures.

        logger.debug("r.json=%s" % r.json)
        logger.debug("r.text=%s" % r.text)
        logger.debug("r.headers=%s" % r.headers)
        header_location = r.headers['location']
        logger.debug("header_location=%s" % header_location)
        new_context_uri = header_location[len(api_host):]
        logger.debug("new_context_uri=%s" % new_context_uri)

        return super(CopyFormView, self).form_valid(form)


def make_dynamic_field(parameter, **kwargs):
    help_text = ''
    if 'subtype' in parameter and parameter['subtype']:
        logger.debug('platform==%s' % parameter)
        if 'password' not in  parameter['subtype']:
            help_text = "%s (%s)" % (parameter['help_text'],
                subtype_validation[parameter['subtype']][0])
    else:
        help_text = parameter['help_text']
    # TODO: finish all types
    # TODO: requires knowledge of how ParameterNames represent types.
    field_params = {
        'required': False,
        'label': parameter['description'],
        'help_text': help_text,

    }
    if 'platform' in kwargs.keys():
        field_params = {
        'required': True,
        'label': parameter['description'],
        'help_text': help_text,

    }

    if parameter['subtype'] in ['bdpurl', 'jsondict']:
        field_params['widget'] = subtype_validation[parameter['subtype']][2]
        field_params['max_length'] = subtype_validation[parameter['subtype']][3]

    if parameter['type'] == 2:
        if parameter['initial']:
            field_params['initial'] = int(parameter['initial'])
        else:
            field_params['initial'] = 0

        if parameter['subtype'] == 'bool':
            field_params['initial'] = bool(parameter['initial'])
            field = forms.BooleanField(**field_params)
        else:
            field = forms.IntegerField(**field_params)
    elif parameter['type'] == 4:
        logger.debug("found strlist")
        # if parameter has choices in schema, than use these, otherwise use
        # dynamically generated ones from platform.
        if parameter['subtype'] == "platform" or parameter['subtype'] == 'mytardis':
            field_params['initial'] = ""
            field_params['choices'] = ""
            if parameter['choices']:
                try:
                    field_params['choices'] = ast.literal_eval(parameter['choices'])
                except Exception:
                    logger.warn("cannot parse parameter choices")
                    field_params['choices'] = ""
            else:
                # FIXME,TODO: compuation_ns value should be part of directive and
                # passed in, as some directives will only work with particular computation/*
                # categories.  Assume only nectar comp platforms ever allowed here.

                if (parameter['subtype'] == "platform" or parameter['subtype'] == 'mytardis' ) and 'directive' in kwargs.keys():
                    #directive_name = kwargs['directive']['name']
                    #logger.debug("computation platform is %s" % directive_name)
                    namespace = kwargs['namespace']
                    schema = django_settings.SCHEMA_PREFIX
                    try:
                        schema += django_settings.RESOURCE_SCHEMA_NAMESPACE[namespace]
                        logger.debug('myschema=%s' % schema)
                    except KeyError:
                        logger.warn("unknown computation platform")

                    '''

                    if namespace == django_settings.SCHEMA_PREFIX + '/input/system/compplatform/cloud':
                        schema += 'cloud/ec2-based'
                    elif namespace == django_settings.SCHEMA_PREFIX + '/input/system/compplatform/unix':
                        schema += 'cluster/pbs_based'
                    elif namespace == django_settings.SCHEMA_PREFIX + '/input/system/compplatform':
                        schema += ''
                    else:
                        logger.warn("unknown computation platform")
                    '''
                    #if parameter['subtype'] == 'mytardis':
                    #    field_params['choices'].insert(0, ('-','-'))
                #elif parameter['subtype'] == 'mytardis':
                #    schema = django_settings.SCHEMA_PREFIX + '/platform/storage/mytardis'

                if 'username' in kwargs:
                    platforms = manage.retrieve_all_platforms(kwargs['username'],
                     schema_namespace_prefix=schema)
                    if platforms:
                        field_params['initial'] = platforms[0]['platform_name']
                    else:
                        field_params['initial'] = ''
                    logger.debug("initial=%s" % field_params['initial'])
                    # TODO: retrieve_platform_paramset should be an API call
                    #platform_name_choices = [(x['platform_name'], x['platform_name'])
                    #    for x in manage.retrieve_all_platforms(
                    #        kwargs['username'], schema_namespace_prefix=schema)]
                    #
                    import os
                    platforms = [x for x in manage.retrieve_all_platforms(
                            kwargs['username'], schema_namespace_prefix=schema)]
                    if '/input/location' in namespace:
                        platform_name_choices = [(x['platform_name'], '%s:%s' % (x['platform_name'], x['root_path']))
                                                 for x in platforms]
                    else:
                        platform_name_choices = [(x['platform_name'], x['platform_name'])
                                                 for x in platforms]
                    logger.debug("platform_name_choices=%s" % platform_name_choices)
                    field_params['choices'] = platform_name_choices

        else:
            if parameter['initial']:
                field_params['initial'] = str(parameter['initial'])
            else:
                field_params['initial'] = ""
            if parameter['choices']:
                # TODO: We load the dynamic choices rather than use the choices field
                # in the model
                field_params['choices'] = ast.literal_eval(str(parameter['choices']))
            else:
                field_params['choices'] = []

        field = forms.ChoiceField(**field_params)
    else:
        logger.debug("subtype=%s" % parameter['subtype'])
        field_params['initial'] = str(parameter['initial'])
        if parameter['subtype'] == 'nectar_platform':
            schema = django_settings.SCHEMA_PREFIX + '/platform/computation/nectar'
            platforms = manage.retrieve_all_platforms(kwargs['username'],
                     schema_namespace_prefix=schema)
            if platforms:
                field_params['initial'] = platforms[0]['name']
            else:
                field_params['initial'] = ''
        elif parameter['subtype'] == 'mytardis':
            schema = django_settings.SCHEMA_PREFIX + '/platform/storage/mytardis'
            platforms = manage.retrieve_all_platforms(kwargs['username'],
                     schema_namespace_prefix=schema)
            if platforms:
                field_params['initial'] = platforms[0]['name']
            else:
                field_params['initial'] = ''
        '''
        elif parameter['subtype'] == 'storage_bdpurl':
            schema = django_settings.SCHEMA_PREFIX + '/platform/storage/unix'
            platforms = manage.retrieve_all_platforms(kwargs['username'],
                     schema_namespace_prefix=schema)
            if platforms:
                field_params['initial'] = platforms[0]['platform_name']
            else:
                field_params['initial'] = ''
        '''
        if parameter['subtype'] == 'hidden':
            field_params['widget'] = forms.HiddenInput()
            field_params['required'] = False
        elif 'platform' in kwargs.keys():
            if parameter['hidecondition'] == 'advanced':
                field_params['widget'] = forms.TextInput()
                field_params['required'] = False
            elif parameter['subtype'] == 'password':
                field_params['widget'] = forms.PasswordInput(attrs={'required': 'true'})
                field_params['required'] = True
            else:
                field_params['widget'] = forms.TextInput(attrs={'required': 'true'})
                field_params['required'] = True

        field = forms.CharField(**field_params)

    if 'subtype' in parameter and parameter['subtype']:
        if subtype_validation[parameter['subtype']][1]:
            field.validators.append(subtype_validation[parameter['subtype']][1])
        logger.debug("field_validators=%s" % field.validators)
    return field


def check_clean_rules(self, cleaned_data):
    for clean_rule_name, clean_rule in clean_rules.items():
        try:
            clean_rule(cleaned_data)
        except ValidationError, e:
            msg = "%s: %s" % (clean_rule_name, unicode(e))
            raise ValidationError(msg)
    return cleaned_data


def make_directive_form(**kwargs):
    fields = SortedDict()
    form_data = []
    # TODO: refactor this method
    if 'directive_params' in kwargs:
        for i, schema_data in enumerate(kwargs['directive_params']):
            logger.debug("schemadata=%s" % pformat(schema_data))
            for j, parameter in enumerate(schema_data['parameters']):
                logger.debug("parameter=%s" % parameter)
                # TODO: handle all possible types
                field_key = "%s/%s" % (schema_data['namespace'], parameter['name'])
                form_data.append((field_key, schema_data['description'] if not j else "", parameter['subtype'], parameter['hidefield'], parameter['hidecondition']))
                #FIXME: replace if else by fields[field_key] = make_dynamic_field(parameter) after unique key platform model is developed
                if 'username' in kwargs:
                    fields[field_key] = make_dynamic_field(parameter, username=kwargs['username'],
                                                           directive=kwargs['directive'],
                                                           namespace=schema_data['namespace'])
                else:
                    fields[field_key] = make_dynamic_field(parameter, directive=kwargs['directive'],
                                                           namespace=schema_data['namespace'])
                logger.debug("field=%s" % fields[field_key].validators)
    elif 'platform_params' in kwargs.keys():
        for i, schema_data in enumerate(kwargs['platform_params']):
            logger.debug("schemadata=%s" % pformat(schema_data))
            for j, parameter in enumerate(schema_data['parameters']):
                logger.debug("parameter=%s" % parameter)
                # TODO: handle all possible types
                #field_key = "%s/%s" % (schema_data['namespace'], parameter['name'])
                field_key = "%s" % (parameter['name'])
                form_data.append((field_key, schema_data['description'] if not j else "", parameter['subtype'], parameter['hidefield'], parameter['hidecondition']))
                #fixme replce if else by fields[field_key] = make_dynamic_field(parameter) after unique key platform model is developed
                if 'username' in kwargs:
                    fields[field_key] = make_dynamic_field(
                        parameter, username=kwargs['username'],
                        platform=True, namespace=schema_data['namespace'])
                else:
                    fields[field_key] = make_dynamic_field(
                        parameter, platform=True, namespace=schema_data['namespace'])
                logger.debug("field=%s" % fields[field_key].validators)

    logger.debug("fields = %s" % fields)
    ParamSetForm = type('ParamSetForm', (forms.BaseForm,),
                         {'base_fields': fields})
    #TODO: handle the initial values
    if 'request' in kwargs:
        pset_form = ParamSetForm(kwargs['request'], initial={})
    else:
        pset_form = ParamSetForm(initial={})

    def myclean(self):
        cleaned_data = super(ParamSetForm, self).clean()
        logger.debug("cleaning")
        return self.clean_rules(cleaned_data)
    import types
    pset_form.clean = types.MethodType(myclean, pset_form)
    pset_form.clean_rules = types.MethodType(check_clean_rules, pset_form)
    pset_form_data = zip(form_data, pset_form)
    logger.debug("pset_form_data = %s" % pformat(pset_form_data))
    logger.debug("custom-pset_form = %s" % pformat(pset_form))
    return (pset_form, pset_form_data)


# def get_test_schemas(direcive_id):

#     return [
#         {
#         'description': 'desc of input1',
#         'hidden': False,
#         'id': 1,
#         'name': 'input1',
#         'namespace': django_settings.SCHEMA_PREFIX + '/input1',
#         'parameters': [
#             {'pk': 1, 'name': 'arg1', 'help_text':'help for arg1', 'type': 1, 'initial': 1, 'subtype': 'natural'},
#             {'pk': 2, 'name': 'arg2', 'help_text':'help for arg2', 'type': 2, 'initial': 'a', 'subtype': 'string'},
#             {'pk': 3, 'name': 'arg3', 'help_text':'help for arg3','type': 2, 'initial': 'b', 'subtype': 'string'},
#             {'pk': 4, 'name': 'arg4', 'help_text':'help for arg4','type': 1, 'initial': 3, 'subtype': 'whole'},
#         ]},
#         {
#         'description': 'desc of input2',
#         'hidden': False,
#         'id': 2,
#         'name': 'input2',
#         'namespace': django_settings.SCHEMA_PREFIX + '/input2',
#         'parameters': [
#             {'pk': 1, 'name': 'arg1', 'help_text':'help for arg1', 'type': 1, 'initial': 1, 'subtype': 'even'},
#           {'pk': 2, 'name': 'arg2', 'help_text':'help for arg2', 'type': 1, 'initial': 2},
#           {'pk': 3, 'name': 'arg3', 'help_text':'arg1+arg2', 'type': 1, 'initial': 2},

#         ]}

#         ]


def get_schema_info(request, schema_id):
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/schema/%s/?format=json" % (api_host, schema_id)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug('r.json=%s' % r.json)
    logger.debug('r.text=%s' % r.text)
    logger.debug('r.headers=%s' % r.headers)
    return r.json()


def get_schema_id(request, namespace):
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/schema/?format=json&namespace=%s" % (api_host, namespace)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug('r.json=%s' % r.json)
    logger.debug('r.text=%s' % r.text)
    logger.debug('r.headers=%s' % r.headers)
    schema_id = ''
    if r.json()['objects']:
        schema = r.json()['objects'][0]
        schema_id = schema['id']
    return schema_id


def get_directive(request, directive_id):
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/directive/%s?format=json" % (api_host, directive_id)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug('r.json=%s' % r.json)
    logger.debug('r.text=%s' % r.text)
    logger.debug('r.headers=%s' % r.headers)
    return r.json()


def get_directives(request):
    host_ip = "172.16.231.130"
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/directive/?limit=0&format=json" % (api_host)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug("r.status_code=%s" % r.status_code)
    # logger.debug('r.json=%s' % r.json)
    # logger.debug('r.text=%s' % r.text)
    # logger.debug('r.headers=%s' % r.headers)
    return [x for x in r.json()['objects']]


def get_directive_schemas(request, directive_id):
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/directiveargset/?limit=0&directive=%s&format=json" % (api_host,
        directive_id)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug('r.json=%s' % r.json)
    logger.debug('r.text=%s' % r.text)
    logger.debug('r.headers=%s' % r.headers)
    schemas = [x['schema'] for x in sorted(r.json()['objects'],
                            key=lambda argset: int(argset['order']))]
    logger.debug("directiveargs= %s" % schemas)
    return schemas


def get_parameters(request, schema_id):
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/parametername/?limit=0&schema=%s&format=json" % (api_host,
        schema_id)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug('r.json=%s' % r.json)
    logger.debug('r.text=%s' % pformat(r.text))
    logger.debug('r.headers=%s' % r.headers)
    schemas = [x for x in sorted(r.json()['objects'],
                                key=lambda ranking: ranking['ranking'])]
    return schemas


def get_directive_params(request, directive):
    directive_params = []
    for directive_schema in get_directive_schemas(request, directive['id']):
        logger.debug("directive_schema=%s" % directive_schema)
        schema_id = int([i for i in str(directive_schema).split('/') if i][-1])
        logger.debug("schema_id=%s" % schema_id)
        schema_info = get_schema_info(request, schema_id)
        logger.debug("schema_info=%s" % schema_info)
        parameters = get_parameters(request, schema_id)
        logger.debug("parameters=%s" % pformat(parameters))
        directive_params.append((schema_info, parameters))
    return directive_params


def get_from_api(request, resource_uri):
    headers = {'content-type': 'application/json'}
    url = "%s%s/?format=json" % (api_host, resource_uri)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug('r.json=%s' % r.json)
    logger.debug('r.text=%s' % r.text)
    logger.debug('r.headers=%s' % r.headers)
    return r.json()


def add_form_fields(request, paramnameset):
    form_field_info = []
    for schema, paramnames in paramnameset:
        s = {}
        s['description'] = schema['description']
        s['name'] = schema['name']
        s['namespace'] = schema['namespace']
        p = []
        for pname in paramnames:
            x = {}
            x['pk'] = pname['id']
            x['name'] = pname['name']
            x['description'] = pname['description']
            x['help_text'] = pname['help_text']
            x['type'] = pname['type']
            # TODO: initial values come from server initially,
            # but later may use values stored in the client to override these
            # to create different user preferences for different uses of the
            # schema
            x['initial'] = pname['initial']
            x['subtype'] = pname['subtype']
            x['choices'] = pname['choices']
            x['hidefield'] = pname['hidefield']
            x['hidecondition'] = pname['hidecondition']
            p.append(x)
        s['parameters'] = p
        form_field_info.append(s)
    return form_field_info


def submit_job(request, form, directive):

    #FIXME: consider using non-locahost URL for api_host
    url = "%s/api/v1/context/?format=json" % api_host
    logger.debug("request.user.username=%s" % request.user.username)
    logger.debug("request.user.username=%s" % request.user.password)
    # pass the sessionid cookie through to the internal API
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    headers = {'content-type': 'application/json'}
    logger.debug("all_form.cleaned_data=%s" % pformat(form.cleaned_data))
    form.cleaned_data[django_settings.SCHEMA_PREFIX + '/bdp_userprofile/username'] = request.user.username
    data = dict(form.cleaned_data.items()
        + [('smart_connector', directive)])

    logger.debug('mydata=%s' % data)
    import traceback
    import os
    try:
        input_storage =  [(k, v) for k, v in data.items() if 'input_storage' in k]
        input_location = [(k, v) for k, v in data.items() if 'input_location' in k]
        logger.debug('tuples input storage=%s location=%s' % (input_storage, input_location))
        if input_storage and input_location:
            input_storage = input_storage[0]
            input_location = input_location[0]
            logger.debug('AFTER tuples input storage=%s location=%s' % (input_storage, input_location))
            storage_name = input_storage[1].split(':')[0]
            relative_path = input_location[1]
            data[input_location[0]] = os.path.join(storage_name, relative_path)
            logger.debug('input=%s' % data[input_location[0]])
    except Exception, e:
        logger.error('input=%s' % e )
        traceback.print_exc(e)
        raise

    try:
        output_location = [(k, v) for k, v in data.items() if 'output_location' in k]
        output_storage =  [(k, v) for k, v in data.items() if 'output_storage' in k]
        if output_storage and output_location:
            output_storage = output_storage[0]
            output_location = output_location[0]
            storage_name = output_storage[1].split(':')[0]
            relative_path = output_location[1]
            if relative_path == '.' or relative_path == './' or not relative_path.strip():
                data[output_location[0]] = storage_name
            else:
                data[output_location[0]] = os.path.join(storage_name, relative_path)
            logger.debug('output=%s' % data[output_location[0]] )
    except Exception, e:
        logger.error('output=%s' % e)
        traceback.print_exc(e)
        raise

    data = json.dumps(data)
    logger.debug("submitteddata=%s" % data)
    r = requests.post(url,
        data=data,
        headers=headers,
        cookies=cookies)
    logger.debug("r.status_code=%s" % r.status_code)
    logger.debug("r.text=%s" % r.text)
    logger.debug("r.headers=%s" % r.headers)
    if r.status_code != 201:
        try:
            if r.json()['error_message']:
                messages.error(request, r.json()['error_message'])
            else:
                messages.error(request, "Task Failed with status code %s: %s"
                    % (r.status_code, r.text))
        except ValueError,e:
                messages.error(request, "Task Failed with status code %s: %s"
                    % (r.status_code, r.text))
        return False
    logger.debug("r.status_code=%s" % r.status_code)
    logger.debug("r.text=%s" % r.text)
    logger.debug("r.headers=%s" % r.headers)
    if 'location' in r.headers:
        header_location = r.headers['location']
        logger.debug("header_location=%s" % header_location)
        new_context_uri = header_location[len(api_host):]
        logger.debug("new_context_uri=%s" % new_context_uri)
        if str(new_context_uri)[-1] == '/':
            job_id = str(new_context_uri).split('/')[-2:-1][0]
        else:
            job_id = str(new_context_uri).split('/')[-1]
        logger.debug("job_id=%s" % job_id)
        messages.success(request, 'Job %s Created' % job_id)
    else:
        messages.success(request, 'Job Created')
    return True


def get_contexts(request):
    offset = 0
    page_size = 20
    if request.method == 'POST':
        contexts = []
        logger.debug("POST=%s" % request.POST)
        for key in request.POST:
            logger.debug("key=%s" % key)
            logger.debug("value=%s" % request.POST[key])
            if key.startswith("delete_"):
                try:
                    val = int(key.split('_')[-1])
                except ValueError, e:
                    logger.error(e)
                else:
                    contexts.append(val)
        logger.debug("contexts=%s" % contexts)
        # TODO: schedule celery tasks to delete each context, as background
        # process because corestages may already have write lock on context.
        from chiminey.smartconnectorscheduler import tasks
        for context_id in contexts:
            logger.debug("scheduling deletion of %s" % context_id)
            tasks.delete.delay(context_id)
        messages.info(request, "Deletion of contexts %s has been scheduled"
                      % ','.join([str(x) for x in contexts]))
    if 'offset' in request.GET:
        try:
            offset = int(request.GET.get('offset'))
        except ValueError:
            pass
    if offset < 0:
        offset = 0
    limit = page_size
    logger.debug("offset=%s" % offset)
    logger.debug("limit=%s" % limit)
    headers = {'content-type': 'application/json'}
    url = "%s/api/v1/contextmessage/?limit=%s&offset=%s&format=json" % (api_host, limit, offset)
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    r = requests.get(url, headers=headers, cookies=cookies)
    # FIXME: need to check for status_code and handle failures such
    # as 500 - lack of disk space at mytardis
    logger.debug('URL=%s' % url)
    logger.debug("r.status_code=%s" % r.status_code)
    # logger.debug('r.json=%s' % r.json)
    # logger.debug('r.text=%s' % r.text)
    # logger.debug('r.headers=%s' % r.headers)
    object_list = []
    logger.debug("r.json()=%s" % pformat(r.json()))
    for x in r.json()['objects']:
        logger.debug("x=%s" % pformat(x))
        contextid = contextdeleted = contextcreated = ""
        parent_id = 0
        directive_name = directive_desc = ""
        if 'context' in x and x['context']:
            if 'id' in x['context']:
                contextid = x['context']['id']
            if 'deleted' in x['context']:
                contextdeleted = x['context']['deleted']
            if 'created' in x['context']:
                    contextcreated = x['context']['created']
            if 'parent' in x['context'] and x['context']['parent']:
                    parent = x['context']['parent']
                    if str(parent)[-1] == '/':
                        parent_id = str(parent).split('/')[-2:-1][0]
                    else:
                        parent_id = str(parent).split('/')[-1]
            if 'directive' in x['context'] and x['context']['directive']:
                if 'name' in x['context']['directive']:
                    directive_name = x['context']['directive']['name']
                if 'description' in x['context']['directive']:
                    directive_desc = x['context']['directive']['description']
        obj = []
        obj.append(int(contextid))
        obj.append(contextdeleted)
        obj.append(dateutil.parser.parse(contextcreated))
        obj.append(x['message'])
        obj.append(directive_name)
        obj.append(directive_desc)
        obj.append(int(parent_id))
        obj.append(reverse('contextview', kwargs={'pk': contextid}))
        object_list.append(obj)
    meta = r.json()['meta']
    # if offset > (meta['total_count'] - limit):
    #     offset = 0
    pages = []
    number_pages = meta['total_count'] / page_size
    for off in range(0, number_pages + 1):
        pages.append(page_size * off)
    logger.debug("pages=%s" % pages)
    return render_to_response(
                       'list_jobs.html',
                       {'object_list': object_list,
                       'limit': limit,
                       'page_offsets': pages,
                       'total_count': int(meta['total_count']),
                       'offset': int(offset)},
                       context_instance=RequestContext(request))


from django.http import HttpResponse
from django.utils.encoding import iri_to_uri


class HttpResponseTemporaryRedirect(HttpResponse):
    status_code = 307

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)


def submit_directive(request, directive_id):
    try:
        directive_id = int(directive_id)
    except ValueError:
        return redirect("makedirective")
    logger.debug("directive_id=%s" % directive_id)
    directives = get_directives(request)
    logger.debug('directives=%s' % directives)
    if directive_id == 0:
        for x in directives:
            if not x['hidden']:
                directive = x
                directive_id = x[u'id']
                break
        else:
            return redirect("home")
    else:
        for x in directives:
            logger.debug(x['id'])
        try:
            directive = [x for x in directives if x[u'id'] == directive_id][0]
        except IndexError:
            return redirect("home")
            # TODO: handle
            raise
    directive_params = get_directive_params(request, directive)
    logger.debug("directive_params=%s" % pformat(directive_params))
    directive_params = add_form_fields(request, directive_params)
    logger.debug("directive_params=%s" % pformat(directive_params))
    if request.method == 'POST':
        form, form_data = make_directive_form(
            request=request.POST,
            directive_params=directive_params,
            username=request.user.username,
            directive=directive)
        logger.debug("form=%s" % pformat(form))
        logger.debug("form_data=%s" % pformat(form_data))
        if form.is_valid():
            logger.debug("form result =%s" % form.cleaned_data)
            valid = submit_job(request, form, directive['name'])
            if valid:
                return HttpResponsePermanentRedirect(reverse("hrmcjob-list"))
            else:
                messages.error(request, "Invalid Job Submission")
                logger.error("invalid job submission")
                return HttpResponsePermanentRedirect(reverse("makedirective", args=[directive_id]))
        else:
            messages.error(request, "Job Failed because of validation errors. See below")
    else:
        form, form_data = make_directive_form(directive_params=directive_params,
            username=request.user.username,
            directive=directive)
    url = "%s/coreapi/preset/?directive=%s" % (api_host, directive['name'])
    logger.debug("directive_name=%s" % directive['name'])
    cookies = dict(request.COOKIES)
    logger.debug("cookies=%s" % cookies)
    headers = {'content-type': 'application/json'}
    try:
        r = requests.get(url, headers=headers, cookies=cookies)
    except HTTPError as e:
        logger.debug('The server couldn\'t fulfill the request. %s' % e)
        logger.debug('Error code: ', e.code)
    except URLError as e:
        logger.debug('We failed to reach a server. %s' % e)
        logger.debug('Reason: ', e.reason)
    else:
        logger.debug('everything is fine')
        logger.debug(r.text)
        logger.debug(r.json())
        #GET_data = r.json()
    presets = []
    for i in r.json():
        presets.append(i['name'])
    return render_to_response(
                       'parameters.html',
                       {'directives': [x for x in directives
                                       if not x['hidden']],
                        'directive': directive,
                        'form': form,
                        'presets': presets,
                        'formdata': form_data,
                        'longfield': [x for (x, y)
                                      in subtype_validation.items()
                                      if y[2] is not None]},
                       context_instance=RequestContext(request))
