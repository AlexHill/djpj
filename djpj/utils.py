from contextlib import contextmanager
from functools import partial
import re


# The container passed by pjax should be a simple id selector e.g. "#main"
_container_re = re.compile(r'^#\S+$')


def pjax_container(request):
    """Return the name of the pjax container specified by the given request."""
    container = request.META['HTTP_X_PJAX_CONTAINER']
    if _container_re.match(container):
        return container[1:]
    else:
        raise ValueError("Invalid PJAX selector '%s' found in request: "
                         "must be a simple ID selector of the form #<id>."
                         % container)


def pjaxify_template_path(template_path, container=None):
    """
    Take a template path and optionally a container, and return the path with
    "-pjax" and (if container is not None) "=<container>" inserted before the
    file extension. For example:

    >>> pjaxify_template_path('templates/product.html', None)
    'templates/product-pjax.html'

    >>> pjaxify_template_path('templates/product.html', 'details')
    'templates/product-pjax=details.html'
    """
    try:
        parts = template_path.rsplit('.', 1)
    except AttributeError:
        raise ValueError("template_path must be a string type")
    pjax_identifier = "=".join(filter(None, ("pjax", container)))
    return ".".join(["%s-%s" % (parts[0], pjax_identifier)] + parts[1:])


def transform_template_var(transform_fn, template_var):
    """
    Transform a template name or sequence of template names (as in the value of
    a TemplateResponse's "template_name" attribute) by applying transform_fn to
    each and returning an iterable containing each transformed and original
    string. The transform function should accept and return a single string.

    >>> xform = lambda s1: ".".join(reversed(s1.split(".")))
    >>> transform_template_var(xform, 'product.html')
    ('html.product', 'product.html')
    >>> transform_template_var(xform, ['first.html', 'second.html'])
    ['html.first', 'first.html', 'html.second', 'second.html']
    """
    if not isinstance(template_var, (list, tuple)):
        template_var = (template_var,)
    template_pair = lambda name: (transform_fn(name), name)
    return type(template_var)(t for name in template_var
                              for t in template_pair(name))


def pjaxify_template_var(request, template_var):
    """
    A template transform function suitable to be passed as the "template"
    argument to the pjax_template decorator. Transforms template_var using
    pjaxify_template_path with no container argument.
    """
    return transform_template_var(pjaxify_template_path, template_var)


def pjaxify_template_var_with_container(request, template_var):
    """
    A template transform function suitable to be passed as the "template"
    argument to the pjax_template decorator. Transforms template_var using
    pjaxify_template_path with its container argument determined from the
    request using pjax_container.
    """
    transform_fn = partial(pjaxify_template_path,
                           container=pjax_container(request))
    return transform_template_var(transform_fn, template_var)


def is_pjax(request):
    return 'HTTP_X_PJAX' in request.META


@contextmanager
def mutable_querydict(querydict):
    """Manage mutation of a QueryDict (such as request.POST and request.GET)"""
    initially_mutable = querydict._mutable
    querydict._mutable = True
    yield querydict
    querydict._mutable = initially_mutable


def strip_pjax_qs_parameter(url):
        return re.sub(r'_pjax=[^&]+&?', '', url).rstrip('&')


def strip_pjax_parameter(request):
    """
    The _pjax GET parameter helps browsers with caching, but is unnecessary in
    the presence of the X-PJAX-Container header, and can cause trouble with
    code that doesn't expect it, so let's just pretend it never existed.
    """
    if is_pjax(request):
        if '_pjax' in request.GET:
            with mutable_querydict(request.GET) as get:
                del get['_pjax']
            request.META['QUERY_STRING'] = \
                strip_pjax_qs_parameter(request.META['QUERY_STRING'])
