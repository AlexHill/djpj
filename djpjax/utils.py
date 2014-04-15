from contextlib import contextmanager
import re

from djpjax.compat import string_types


_container_re = re.compile(r'^#\S+$')


def pjax_container_from_header(request):
    return request.META.get("HTTP_X_PJAX_CONTAINER", None)


def pjax_block_from_request(request):
    container = pjax_container_from_header(request)
    if container:
        if _container_re.match(container):
            return container[1:]
        else:
            raise ValueError("Invalid PJAX selector '%s' found in request: "
                             "must be a simple ID selector of the form #<id>."
                             % container)
    else:
        return None


def pjaxify_template_name(name, block_name):
    parts = name.rsplit('.', 1)
    if len(parts) == 2:
        name = "%s.pjax:%s.%s" % (parts[0], block_name, parts[1])
    else:
        name = "%s.pjax:%s" % (parts[0], block_name)
    return name


def pjaxify_template_var(transform_fn, template_var, block_name):
    if isinstance(template_var, string_types):
        template_var = (template_var,)
    if isinstance(template_var, (list, tuple)):
        def template_pair(name):
            return transform_fn(name, block_name), name
        template_var = type(template_var)(t for name in template_var for t in
                                          template_pair(name))
    return template_var


def is_pjax(request):
    return 'HTTP_X_PJAX' in request.META


@contextmanager
def mutable_querydict(querydict):
    initially_mutable = querydict._mutable
    querydict._mutable = True
    yield querydict
    querydict._mutable = initially_mutable


def strip_pjax_qs_parameter(url):
        return re.sub(r'_pjax=[^&]+&?', '', url).rstrip('&')


def strip_pjax_parameter(request):
    """
    The _pjax GET parameter helps browsers with caching, but is
    unnecessary with the presence of the X-PJAX-Container header,
    and can cause trouble with code that doesn't expect it, so let's
    just pretend it never existed.
    """
    if is_pjax(request):
        if '_pjax' in request.GET:
            with mutable_querydict(request.GET) as get:
                del get['_pjax']
            request.META['QUERY_STRING'] = \
                strip_pjax_qs_parameter(request.META['QUERY_STRING'])