from contextlib import contextmanager
import re


_container_re = re.compile(r'^#\S+$')


def pjax_container(request):
    container = request.META['HTTP_X_PJAX_CONTAINER']
    if _container_re.match(container):
        return container[1:]
    else:
        raise ValueError("Invalid PJAX selector '%s' found in request: "
                         "must be a simple ID selector of the form #<id>."
                         % container)


def pjaxify_template_path(template_path, container):
    try:
        parts = template_path.rsplit('.', 1)
    except AttributeError:
        raise ValueError("template_path must be a string type")
    pjax_identifier = "=".join(filter(None, ("pjax", container)))
    return ".".join(["%s-%s" % (parts[0], pjax_identifier)] + parts[1:])


def transform_template_var(transform_fn, template_var, container=None):
    if not isinstance(template_var, (list, tuple)):
        template_var = (template_var,)
    template_pair = lambda name: (transform_fn(name, container), name)
    return type(template_var)(t for name in template_var
                              for t in template_pair(name))


def pjaxify_template_var(request, template_var):
    return transform_template_var(pjaxify_template_path, template_var)


def pjaxify_template_var_with_container(request, template_var):
    return transform_template_var(pjaxify_template_path, template_var,
                                  container=pjax_container(request))


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
