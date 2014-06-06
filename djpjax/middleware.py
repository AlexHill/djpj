import re

from djpjax.utils import strip_pjax_parameter
from django.conf import settings
import djpjax


class DjangoPJAXMiddleware(object):

    def __init__(self):
        djpjax_setting = getattr(settings, 'DJPJAX_DECORATE_URLS', [])
        self.decorated_urls = tuple(
            (re.compile(url_regex), getattr(djpjax, decorator)(**kwargs))
            for url_regex, (decorator, kwargs) in reversed(djpjax_setting))

    def process_request(self, request):
        strip_pjax_parameter(request)

    def process_template_response(self, request, response):
        for url_regex, decorator in self.decorated_urls:
            if url_regex.match(request.path):
                fake_view = lambda _: response
                response = decorator(fake_view)(request)
        return response
