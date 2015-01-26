import ast
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Though IDEs will report these symbols unused, they're necessary
# to eval() the decorator strings used in DJPJ_PJAX_URLS.
from djpj.decorator import pjax_block, pjax_template
from djpj.utils import strip_pjax_parameter


class DjangoPJAXMiddleware(object):
    """
    Reads the DjPj configuration found at DJPJ_PJAX_URLS on instantiation, then
    looks for requests that match a configured URL pattern, and runs their
    responses through the decorators configured for that pattern.
    """

    def __init__(self, config=None):
        djpj_setting = config or getattr(settings, 'DJPJ_PJAX_URLS', [])
        self.decorated_urls = self.parse_configuration(djpj_setting)

    @staticmethod
    def parse_decorator(decorator_string):
        """
        Take a string containing Python code declaring a DjPj decorator, and
        return a corresponding decorator function. Syntax is limited to a
        single call to one of DjPj's decorators, without the use of *args or
        **kwargs, and with string arguments only.

        For example:
            "@pjax_block(block='content', title_variable='page_title')"
        """

        # Helper function for raising config errors
        error = lambda msg: ImproperlyConfigured(
            '"%s" does not define a valid PJAX decorator: %s'
            % (decorator_string, msg))

        # A "@" preceding an expression is only valid syntax if the expression
        # is followed by the definition of a function or class to be decorated.
        # Check that it starts with one, and then strip it.
        if not decorator_string.startswith('@'):
            raise error("expression should start with '@'")
        decorator_string = decorator_string[1:]

        # Parse the remainder of the decorator string as Python code, and check
        # that it meets all of the conditions of our restricted Python syntax.
        # The error messages should explain what each block does.
        expr = ast.parse(decorator_string, '<string>', mode='eval')
        if not isinstance(expr.body, ast.Call):
            raise error("decorator expression must be a single call "
                        "to pjax_block or pjax_template")

        call = expr.body
        if call.func.id not in ('pjax_block', 'pjax_template'):
            raise error("decorator expression must be a single call "
                        "to pjax_block or pjax_template")

        if not (call.starargs is None and call.kwargs is None):
            raise error("unpacking * and ** arguments is not supported")

        if not all(isinstance(arg, ast.Str) for arg
                   in call.args + [kw.value for kw in call.keywords]):
            raise error("only string arguments are allowed")

        # If the syntax checks out, return the evaluated code.
        return eval(compile(expr, '<string>', mode='eval'))

    @staticmethod
    def parse_configuration(config_seq):
        """
        Parse a sequence of (url_regex, pjax_decorators) pairs, returning a
        list of corresponding (compiled_regex, parsed_decorators) pairs. This
        is used to parse the value of settings.DJPJ_PJAX_URLS.
        """

        # For convenience, allow either a sequence of decorators or a single
        listify = lambda d: d if isinstance(d, (list, tuple)) else [d]

        parse_fn = DjangoPJAXMiddleware.parse_decorator
        return [(re.compile(url_regex),
                 [parse_fn(d) for d in reversed(listify(decorators))])
                for url_regex, decorators in reversed(config_seq)]

    def process_request(self, request):
        strip_pjax_parameter(request)

    def process_template_response(self, request, response):
        """
        If the request URL matches a decorated URL, run the response through
        the corresponding decorators before returning it.
        """
        for url_regex, decorators in self.decorated_urls:
            if url_regex.match(request.path):
                fake_view = lambda _: response
                for decorator in decorators:
                    response = decorator(fake_view)(request)
        return response
