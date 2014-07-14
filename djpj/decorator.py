import functools

from django.http import HttpResponseRedirect, HttpRequest
from djpj.template import PJAXBlockTemplateResponse
from djpj.utils import (strip_pjax_parameter, is_pjax,
                        pjax_container, pjaxify_template_var_with_container)


def _make_decorator(partition_fn, process_fn):

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
_make_ajax_decorator = functools.partial(_make_decorator, HttpRequest.is_ajax)


def pjax_template(template=pjaxify_template_var_with_container):

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


def pjax_block(block=pjax_container,
               title_variable=None, title_block=None):

    if not block:
        raise ValueError("The block argument to pjax_block may not be None.")

    if title_variable and title_block:
        raise ValueError("Only one of 'title_variable' and 'title_block' "
                         "may be passed to pjax decorator.")

    def process_response(request, response):
        _block = block(request) if callable(block) else block
        PJAXBlockTemplateResponse.cast(response, _block,
                                       title_block, title_variable)

    return _make_pjax_decorator(process_response)
