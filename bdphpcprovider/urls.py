from django.conf.urls import patterns, url, include

from django.contrib import admin
admin.autodiscover()
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from bdphpcprovider.smartconnectorscheduler import views

urlpatterns = patterns('bdphpcprovider.smartconnectorscheduler',
    (r'^index/$', 'views.index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.hello),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^output/(?P<group_id>\w+)/(?P<file_id>[\w.]+)/$', views.getoutput, name="getoutput"),
    url(r'^directive/(?P<directive_id>\d+)/$', 'views.test_directive')

)
urlpatterns += staticfiles_urlpatterns()

