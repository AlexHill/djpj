from django.conf import settings
from django.http import HttpResponseRedirect

settings.configure()

import djpjax
from django.template.response import TemplateResponse
from django.test.client import RequestFactory
from django.template import Template, TemplateSyntaxError

from nose.tools import raises

# A couple of request objects - one PJAX, one not.
rf = RequestFactory()
regular_request = rf.get('/')
pjax_request = rf.get('/?_pjax=%23secondary',
                      HTTP_X_PJAX=True,
                      HTTP_X_PJAX_CONTAINER="#secondary")

# A template to test the pjax_block decorator.
template = Template(
    "{% block title %}Block Title{% endblock %}"
    "Some text outside the main block."
    "{% with footwear='galoshes' %}"
    "{% block main %}I'm wearing {{ colour }} {{ footwear }}{% endblock %}"
    "{% endwith %}"
    "{% block secondary %}Some secondary content.{% endblock %}"
    "More text outside the main block.")

middleware = djpjax.DjangoPJAXMiddleware()


# Tests.

def test_pjax_block_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet_bloc")
    assert djpjax._pjax_block_from_request(req) == "soviet_bloc"


@raises(ValueError)
def test_pjax_block_invalid_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet .bloc")
    _ = djpjax._pjax_block_from_request(req)


@raises(ValueError)
def test_pjax_block_not_supplied():
    request = rf.get('/', HTTP_X_PJAX=True)
    _ = view_pjax_block_auto(request)


def test_pjax_normal_request():
    resp = view_pjax_block(regular_request)
    result = resp.rendered_content
    assert result == ("Block Title"
                      "Some text outside the main block."
                      "I'm wearing orange galoshes"
                      "Some secondary content."
                      "More text outside the main block.")


def test_pjax_block_auto():
    resp = view_pjax_block_auto(pjax_request)
    result = resp.rendered_content
    assert result == "Some secondary content."


def test_pjax_block_auto_title():
    resp = view_pjax_block_auto_title(pjax_request)
    result = resp.rendered_content
    assert result == ("<title>Block Title</title>\n"
                      "Some secondary content.")


def test_pjax_block():
    resp = view_pjax_block(pjax_request)
    result = resp.rendered_content
    assert result == "I'm wearing orange galoshes"

@raises(TemplateSyntaxError)
def test_pjax_block_error():
    resp = view_pjax_block_error(pjax_request)
    _ = resp.rendered_content


def test_pjax_block_title_variable():
    resp = view_pjax_block_title_variable(pjax_request)
    result = resp.rendered_content
    assert result == "<title>Variable Title</title>\nI'm wearing orange galoshes"


@raises(KeyError)
def test_pjax_block_title_variable_error():
    resp = view_pjax_block_title_variable_error(pjax_request)
    _ = resp.rendered_content


def test_pjax_block_title_block():
    resp = view_pjax_block_title_block(pjax_request)
    result = resp.rendered_content
    assert result == "<title>Block Title</title>\nI'm wearing orange galoshes"


@raises(TemplateSyntaxError)
def test_pjax_block_title_block_error():
    resp = view_pjax_block_title_block_error(pjax_request)
    _ = resp.rendered_content


@raises(TypeError)
def test_pjax_block_title_conflict():
    djpjax.pjax_block("main", title_variable="title", title_block="title")(None)


def test_pjax_url_header():
    response = view_pjax_block_auto(pjax_request)
    assert response.has_header('X-PJAX-URL')
    assert response['X-PJAX-URL'] == pjax_request.get_full_path()


def test_pjax_redirect_header():
    response = view_pjax_block_redirect(pjax_request)
    assert response.has_header('X-PJAX-URL')
    assert response['X-PJAX-URL'] == '/redirected/'


def test_is_pjax():
    assert djpjax.is_pjax(pjax_request) is True
    assert djpjax.is_pjax(regular_request) is False


def test_pjax_middleware_strips_get_param():
    request = rf.get('/?_pjax=%23container',
                     HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#container")
    assert '_pjax' in request.GET
    assert '_pjax' in request.META['QUERY_STRING']
    middleware.process_request(request)
    assert '_pjax' not in request.GET
    assert '_pjax' not in request.META['QUERY_STRING']


def test_pjax_middleware_strip_qs_parameter():
    strip_fn = middleware.strip_pjax_qs_parameter
    assert strip_fn('_pjax=%23container') == ''
    assert strip_fn('_pjax=%23container&second=2') == 'second=2'
    assert strip_fn('first=1&_pjax=%23container') == 'first=1'
    assert strip_fn('first=1&_pjax=%23container&second=2') == 'first=1&second=2'


# The test "views" themselves.

@djpjax.pjax_block()
def view_pjax_block_auto(request):
    return TemplateResponse(request, template, {"colour": "orange"})


@djpjax.pjax_block(title_block="title")
def view_pjax_block_auto_title(request):
    return TemplateResponse(request, template, {"colour": "orange"})


@djpjax.pjax_block("main")
def view_pjax_block(request):
    return TemplateResponse(request, template, {"colour": "orange"})


@djpjax.pjax_block("main_missing")
def view_pjax_block_error(request):
    return TemplateResponse(request, template, {"colour": "orange"})


@djpjax.pjax_block("main", title_block="title")
def view_pjax_block_title_block(request):
    return TemplateResponse(request, template, {"colour": "orange"})


@djpjax.pjax_block("main", title_block="title_missing")
def view_pjax_block_title_block_error(request):
    return TemplateResponse(request, template, {"colour": "orange"})


@djpjax.pjax_block("main", title_variable="title")
def view_pjax_block_title_variable(request):
    return TemplateResponse(request, template, {"colour": "orange",
                                                "title": "Variable Title"})


@djpjax.pjax_block("main", title_variable="title_missing")
def view_pjax_block_title_variable_error(request):
    return TemplateResponse(request, template, {"colour": "orange",
                                                "title": "Variable Title"})


@djpjax.pjax_block()
def view_pjax_block_redirect(_):
    return HttpResponseRedirect('/redirected/')