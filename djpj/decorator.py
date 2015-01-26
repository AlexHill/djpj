import functools

from django.http import HttpResponseRedirect, HttpRequest
from djpj.template import PJAXTemplateResponse
from djpj.utils import (strip_pjax_parameter, is_pjax,
                        pjax_container, pjaxify_template_var_with_container)


def _make_decorator(partition_fn, process_fn):
    """
    Produce a DjPj decorator function suitable for decorating a Django view
    that returns TemplateResponse. Used by pjax_block and pjax_template.

    The behaviour of the resultant decorator is this: wherever
    partition_fn(request) is True and the decorated view returned a
    TemplateResponse, process_fn will be called with the request and response
    as its arguments and the result returned in place of the original response.
    """

    # Import this here to avoid import issues when running tests.
    from django.views.decorators.vary import vary_on_headers

    def djpj_decorator(view):
        @functools.wraps(view)
        def wrapped_view(request, *args, **kwargs):
            response = view(request, *args, **kwargs)
            if partition_fn(request):
                # Before generating a response, strip the "_pjax" GET parameter
                # that jquery-pjax adds as a browser cache-busting measure.
                strip_pjax_parameter(request)

                # This header helps jquery-pjax correctly handle redirects.
                response['X-PJAX-URL'] = (response.get('Location')
                                          or request.get_full_path())
                # Test if response supports deferred rendering, approach copied
                # from django.core.handlers.base.BaseHandler.get_response()
                if hasattr(response, 'render') and callable(response.render):
                    process_fn(request, response)
                elif not isinstance(response, HttpResponseRedirect):
                    raise TypeError("PJAX views must return either a response "
                                    "with a render() method, or a redirect.")
            return response
        return vary_on_headers('X-PJAX-Container')(wrapped_view)

    return djpj_decorator

_make_pjax_decorator = functools.partial(_make_decorator, is_pjax)

# So far unused
_make_ajax_decorator = functools.partial(_make_decorator, HttpRequest.is_ajax)


def pjax_template(template=pjaxify_template_var_with_container):
    """
    A view decorator that, for PJAX requests, can search for PJAX-specific
    templates to render. The template argument should be a function that
    takes a request and a TemplateResponse's template_name attribute, and
    returns a value that will replace the response's template_name.

    By default, with a template like "product.html" and a PJAX request for the
    container "content", "product-pjax=content.html" will be prepended to the
    list of templates to search for.
    """

    if not template:
        raise ValueError("The template argument to pjax_template "
                         "may not be None.")

    def process_response(request, response):
        _template = (template(request, response.template_name)
                     if callable(template) else template)
        if not _template:
            raise ValueError("Tried to set PJAX response's template to %s. "
                             "You must provide a template!" % _template)
        response.template_name = _template

    return _make_pjax_decorator(process_response)


def pjax_block(block=pjax_container, title_variable=None, title_block=None):
    """
    A view decorator that, for PJAX requests, can return the contents of a
    single template block to the client instead of the whole page.

    If the block argument is a string, the block with that name will always be
    returned. If it's a callable, the result of calling block(request) will be
    the name of the rendered block.

    title_variable and title_block can't both be passed, and determine the
    contents of the response's <title> tag.
    """
    if not block:
        raise ValueError("The block argument to pjax_block may not be None.")

    if title_variable and title_block:
        raise ValueError("Only one of 'title_variable' and 'title_block' "
                         "may be passed to pjax decorator.")

    def process_response(request, response):
        _block = block(request) if callable(block) else block
        PJAXTemplateResponse.patch(response, _block,
                                  title_block, title_variable)

    return _make_pjax_decorator(process_response)
