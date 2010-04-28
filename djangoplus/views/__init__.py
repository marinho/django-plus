from django.http import HttpResponse
from django.utils import simplejson
from django.views.decorators.cache import never_cache

@never_cache
def json_list_view(request, queryset, desc_field, id_field, extra_args=False):
    if request.GET:
        kwargs = dict([(str(k),v) for k,v in request.GET.items()])
        q = queryset.filter(**kwargs)
    else:
        q = queryset.all()

    ret = q.values(id_field, desc_field)

    return HttpResponse(simplejson.dumps([x for x in ret]), mimetype='text/javascript')

