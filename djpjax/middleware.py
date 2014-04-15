from djpjax.utils import strip_pjax_parameter


class DjangoPJAXMiddleware(object):

    def process_request(self, request):
        strip_pjax_parameter(request)