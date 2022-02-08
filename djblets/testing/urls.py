from django.http import HttpResponse
from django.urls import include, path


def dummy_view(request):
    return HttpResponse('')


urlpatterns = [
    path('', dummy_view, name='test-url-name'),
    path('admin/extensions/', include('djblets.extensions.urls')),
    path('auth/', include('djblets.auth.urls')),
]
