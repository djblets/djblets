from cia.apps.images import models
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from cStringIO import StringIO
import Image


def upload(request):
    error = False
    image = None

    if request.POST.get('remove'):
        # User requested that we remove the currently posted image
        pass

    elif request.GET.get('image-id'):
        # Preload with a supplied image ID
        try:
            image = models.ImageSource.objects.get(id=request.GET['image-id'])
        except models.ImageSource.DoesNotExist:
            raise Http404

    elif request.FILES and request.user.is_authenticated():
        # Upload a new image
        try:
            im = Image.open(StringIO(request.FILES['file']['content']))
            im.load()
        except IOError:
            error = True
        else:
            image = models.ImageInstance.objects.create_original(im, request.user)

    return render_to_response('image_upload.html', RequestContext(request, {
        'image': image,
        'error': error,
        }))
