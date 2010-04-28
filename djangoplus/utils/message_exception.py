from django.http import HttpResponseRedirect

class HttpMessageMiddleware(object):
    def process_exception(self, request, exception):
        if request.user.is_authenticated() and exception is HttpMessage:
            request.user.message_set.create(message=unicode(exception))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

class HttpMessage(Exception):
    pass

