from functools import partial

from django.conf import settings

settings.configure()
settings.TEMPLATE_DIRS = ('tests/', '.')

from django.http import HttpResponseRedirect, HttpResponse
from django.template import Template, TemplateSyntaxError
from django.template.response import TemplateResponse
from django.test.client import RequestFactory

from djpjax.decorator import pjax_block
from djpjax.middleware import DjangoPJAXMiddleware
from djpjax.utils import *
from djpjax.template import PJAXBlockTemplateResponse

import djpjax.template

from nose.tools import raises

# A couple of request objects - one PJAX, one not.
rf = RequestFactory()
regular_request = rf.get('/')
pjax_request = rf.get('/?_pjax=%23secondary',
                      HTTP_X_PJAX=True,
                      HTTP_X_PJAX_CONTAINER="#secondary")

file_template = 'test_template.html'

# A template to test the pjax_block decorator.
est_template = Template(
    "{% block title %}Block Title{% endblock %}"
    "Some text outside the main block."
    "{% with footwear='galoshes' %}"
    "{% block main %}I'm wearing {{ colour }} {{ footwear }}{% endblock %}"
    "{% endwith %}"
    "{% block secondary %}Some secondary content.{% endblock %}"
    "More text outside the main block.")

base_template = Template("{% block main %}base block content{% endblock %}")
extends_template = Template("{% extends base_template %}")

middleware = DjangoPJAXMiddleware()


# Tests.

def test_pjax_block_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet_bloc")
    assert pjax_block_from_request(req) == "soviet_bloc"


@raises(ValueError)
def test_pjax_block_invalid_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet .bloc")
    _ = pjax_block_from_request(req)


@raises(ValueError)
def test_pjax_block_not_supplied():
    request = rf.get('/', HTTP_X_PJAX=True)
    _ = view_pjax_block_auto(request, est_template)


def test_pjax_normal_request():
    resp = view_pjax_block(regular_request, est_template)
    result = resp.rendered_content
    assert result == ("Block Title"
                      "Some text outside the main block."
                      "I'm wearing orange galoshes"
                      "Some secondary content."
                      "More text outside the main block.")


def test_pjax_block_auto():
    resp = view_pjax_block_auto(pjax_request, est_template)
    result = resp.rendered_content
    assert result == "Some secondary content."


def test_pjax_block_auto_title():
    resp = view_pjax_block_auto_title(pjax_request, est_template)
    result = resp.rendered_content
    assert result == ("<title>Block Title</title>\n"
                      "Some secondary content.")


def test_pjax_block():
    resp = view_pjax_block(pjax_request, est_template)
    result = resp.rendered_content
    assert result == "I'm wearing orange galoshes"

@raises(TemplateSyntaxError)
def test_pjax_block_error():
    resp = view_pjax_block_error(pjax_request, est_template)
    _ = resp.rendered_content


def test_pjax_block_title_variable():
    resp = view_pjax_block_title_variable(pjax_request, est_template,
                                          {'title': 'Variable Title'})
    result = resp.rendered_content
    assert result == "<title>Variable Title</title>\nI'm wearing orange galoshes"


@raises(KeyError)
def test_pjax_block_title_variable_error():
    resp = view_pjax_block_title_variable_error(pjax_request, est_template,
                                                {'title': 'Variable Title'})
    _ = resp.rendered_content


def test_pjax_block_title_block():
    resp = view_pjax_block_title_block(pjax_request, est_template)
    result = resp.rendered_content
    assert result == "<title>Block Title</title>\nI'm wearing orange galoshes"


@raises(TemplateSyntaxError)
def test_pjax_block_title_block_error():
    resp = view_pjax_block_title_block_error(pjax_request, est_template)
    _ = resp.rendered_content


@raises(TypeError)
def test_pjax_block_title_conflict():
    pjax_block("main", title_var="title", title_block="title")(None)


def test_pjax_block_in_base_template():
    response = view_pjax_block(pjax_request, extends_template,
                               {'base_template': base_template})
    assert response.rendered_content == "base block content"


def test_pjax_block_in_base_file_template():
    response = view_pjax_block(pjax_request, extends_template,
                               {'base_template': file_template})
    assert response.rendered_content == "file base block content"


def test_pjax_url_header():
    response = view_pjax_block_auto(pjax_request, est_template)
    assert response.has_header('X-PJAX-URL')
    assert response['X-PJAX-URL'] == pjax_request.get_full_path()


def test_pjax_redirect_header():
    response = view_pjax_block_redirect(pjax_request)
    assert response.has_header('X-PJAX-URL')
    assert response['X-PJAX-URL'] == '/redirected/'


def test_is_pjax():
    assert is_pjax(pjax_request) is True
    assert is_pjax(regular_request) is False


def test_strip_pjax_parameter():
    request = rf.get('/?_pjax=%23container',
                     HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#container")
    assert '_pjax' in request.GET
    assert '_pjax' in request.META['QUERY_STRING']
    strip_pjax_parameter(request)
    assert '_pjax' not in request.GET
    assert '_pjax' not in request.META['QUERY_STRING']


def test_pjax_middleware():
    request = rf.get('/?_pjax=%23container',
                     HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#container")
    assert '_pjax' in request.GET
    assert '_pjax' in request.META['QUERY_STRING']
    middleware.process_request(request)
    assert '_pjax' not in request.GET
    assert '_pjax' not in request.META['QUERY_STRING']


def test_strip_pjax_qs_parameter():
    strip_fn = strip_pjax_qs_parameter
    assert strip_fn('_pjax=%23container') == ''
    assert strip_fn('_pjax=%23container&second=2') == 'second=2'
    assert strip_fn('first=1&_pjax=%23container') == 'first=1'
    assert strip_fn('first=1&_pjax=%23container&second=2') == 'first=1&second=2'


@raises(TypeError)
def test_exception_on_non_deferred_response():
    _ = view_pjax_block_not_deferred(pjax_request)


def test_pjaxify_template_name():
    assert pjaxify_template_name("test.html", "testblock") == "test.pjax:testblock.html"
    assert pjaxify_template_name("test", "testblock") == "test.pjax:testblock"


def test_pjaxify_template_var():
    pjaxify = partial(pjaxify_template_var,
                      pjaxify_template_name)
    assert pjaxify("test.html", "testblock") == ("test.pjax:testblock.html", "test.html")
    pjaxed_seq = ["test1.pjax:testblock.html", "test1.html",
                  "test2.pjax:testblock.html", "test2.html",]
    assert pjaxify(["test1.html", "test2.html"], "testblock") == pjaxed_seq


def test_pjax_static_template():
    resp = view_pjax_block_static_template(pjax_request, est_template)
    print(resp.template_name)
    assert resp.template_name == ("static_template.html",)


def test_registry():
    wrapped_classes = sorted([cls.__name__ for cls
                              in djpjax.template._wrapped_class_registry])
    assert wrapped_classes == ['ExtendsNode', 'NodeList', 'TemplateResponse']


@raises(NotImplementedError)
def test_object_wrapping_direct_instantiation():
    response = base_view(pjax_request, est_template)
    PJAXBlockTemplateResponse(response)


# The test "views" themselves.

def base_view(request, template, extra_context=None):
    extra_context = extra_context or dict()
    extra_context.update({"colour": "orange"})
    return TemplateResponse(request, template, extra_context)

view_pjax_block = pjax_block("main")(base_view)
view_pjax_block_auto = pjax_block()(base_view)
view_pjax_block_auto_title = pjax_block(title_block="title")(base_view)
view_pjax_block_error = pjax_block("main_missing")(base_view)
view_pjax_block_title_block = pjax_block("main", title_block="title")(base_view)
view_pjax_block_title_block_error = pjax_block("main", title_block="title_missing")(base_view)
view_pjax_block_title_variable = pjax_block("main", title_var="title")(base_view)
view_pjax_block_title_variable_error = pjax_block("main", title_var="title_missing")(base_view)
view_pjax_block_static_template = pjax_block("main", template=('static_template.html',))(base_view)


@pjax_block()
def view_pjax_block_redirect(_):
    return HttpResponseRedirect('/redirected/')


@pjax_block()
def view_pjax_block_not_deferred(_):
    return HttpResponse("Some text!")