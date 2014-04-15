import functools
from django.http import HttpResponseRedirect
from djpjax.template import PJAXBlockTemplateResponse
from djpjax.utils import (strip_pjax_parameter, is_pjax,
                          pjax_block_from_request, pjaxify_template_name)


def pjax_block(block=None, title_var=None, title_block=None, template=None):

    # Import this here to avoid import issues when running tests.
    from django.views.decorators.vary import vary_on_headers

    if title_var and title_block:
        raise TypeError("Only one of 'title_variable' and 'title_block' "
                        "may be passed to pjax decorator.")

    def pjax_decorator(view):
        @functools.wraps(view)
        def wrapped_view(request, *args, **kwargs):
            strip_pjax_parameter(request)
            response = view(request, *args, **kwargs)
            if is_pjax(request):
                response['X-PJAX-URL'] = (response.get('Location')
                                          or request.get_full_path())
                # Test if response supports deferred rendering, approach copied
                # from django.core.handlers.base.BaseHandler.get_response()
                if hasattr(response, 'render') and callable(response.render):
                    _block = block or pjax_block_from_request
                    block_name = _block(request) if callable(_block) else _block
                    template_arg = template or pjaxify_template_name
                    if not block_name:
                        raise ValueError(
                            "A PJAX block name must be supplied, "
                            "either by the  `block` argument "
                            "or the X-PJAX-Container HTTP header.")
                    PJAXBlockTemplateResponse.add_to(response,
                                                     block_name,
                                                     title_block,
                                                     title_var,
                                                     template_arg)
                elif not isinstance(response, HttpResponseRedirect):
                    raise TypeError("PJAX views must return either redirects, "
                                    "or responses with a render() method.")
            return response
        return vary_on_headers('X-PJAX-Container')(wrapped_view)
    return pjax_decorator
