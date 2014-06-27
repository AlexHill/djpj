from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

settings.configure()
settings.TEMPLATE_DIRS = ('tests/', '.')

from django.http import HttpResponseRedirect, HttpResponse
from django.template import Template, TemplateSyntaxError
from django.template.response import TemplateResponse
from django.test.client import RequestFactory

from djpjax.decorator import pjax_block, pjax_template
from djpjax.middleware import DjangoPJAXMiddleware
from djpjax.utils import *
from djpjax.template import PJAXBlockTemplateResponse

import djpjax.template

from nose.tools import raises, assert_raises

# A couple of request objects - one PJAX, one not.
rf = RequestFactory()
regular_request = rf.get('/')
pjax_request = rf.get('/?_pjax=%23secondary',
                      HTTP_X_PJAX=True,
                      HTTP_X_PJAX_CONTAINER="#secondary")

file_template = 'test_template.html'

# A template to test the pjax_block decorator.
test_template = Template(
    "{% block title %}Block Title{% endblock %}"
    "Some text outside the main block."
    "{% with footwear='galoshes' %}"
    "{% block main %}I'm wearing {{ colour }} {{ footwear }}{% endblock %}"
    "{% endwith %}"
    "{% block secondary %}Some secondary content.{% endblock %}"
    "More text outside the main block.")

base_template = Template("{% block main %}base block content{% endblock %}")
extends_template = Template("{% extends base_template %}")


# Tests.

def test_pjax_block_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet_bloc")
    assert pjax_container(req) == "soviet_bloc"


@raises(ValueError)
def test_pjax_block_invalid_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet .bloc")
    _ = pjax_container(req)


@raises(KeyError)
def test_pjax_block_no_pjax_container():
    request = rf.get('/', HTTP_X_PJAX=True)
    _ = view_pjax_block_auto(request, None)


@raises(ValueError)
def test_pjax_block_none_arg():
    pjax_block(None)


@raises(ValueError)
def test_pjax_template_none_arg():
    pjax_template(None)


@raises(ValueError)
def test_pjax_template_no_result():
    _ = pjax_template(lambda *a, **kw: None)(base_view)(pjax_request, test_template)


def test_pjax_template_auto():
    view = pjax_template()(base_view)
    resp = view(pjax_request, 'test_template.html')
    assert resp.template_name == ('test_template-pjax=secondary.html', 'test_template.html')


def test_pjax_block_no_result():
    resp = pjax_block(lambda *a, **kw: None)(base_view)(pjax_request, test_template)
    result = resp.rendered_content
    assert result == ("Block Title"
                      "Some text outside the main block."
                      "I'm wearing orange galoshes"
                      "Some secondary content."
                      "More text outside the main block.")


def test_pjax_normal_request():
    resp = view_pjax_block(regular_request, test_template)
    result = resp.rendered_content
    assert result == ("Block Title"
                      "Some text outside the main block."
                      "I'm wearing orange galoshes"
                      "Some secondary content."
                      "More text outside the main block.")


def test_pjax_block_auto():
    resp = view_pjax_block_auto(pjax_request, test_template)
    result = resp.rendered_content
    assert result == "Some secondary content."


def test_pjax_block_auto_title():
    view = pjax_block(title_block="title")(base_view)
    resp = view(pjax_request, test_template)
    result = resp.rendered_content
    assert result == ("<title>Block Title</title>\n"
                      "Some secondary content.")


def test_pjax_block():
    resp = view_pjax_block(pjax_request, test_template)
    result = resp.rendered_content
    assert result == "I'm wearing orange galoshes"


@raises(TemplateSyntaxError)
def test_pjax_block_error():
    view = pjax_block("main_missing")(base_view)
    resp = view(pjax_request, test_template)
    _ = resp.rendered_content


def test_pjax_block_title_variable():
    view = pjax_block("main", title_variable="title")(base_view)
    resp = view(pjax_request, test_template, {'title': 'Variable Title'})
    result = resp.rendered_content
    assert result == "<title>Variable Title</title>\nI'm wearing orange galoshes"


@raises(KeyError)
def test_pjax_block_title_variable_error():
    view = pjax_block("main", title_variable="title_missing")(base_view)
    resp = view(pjax_request, test_template, {'title': 'Variable Title'})
    _ = resp.rendered_content


def test_pjax_block_title_block():
    view = pjax_block("main", title_block="title")(base_view)
    resp = view(pjax_request, test_template)
    result = resp.rendered_content
    assert result == "<title>Block Title</title>\nI'm wearing orange galoshes"


@raises(TemplateSyntaxError)
def test_pjax_block_title_block_error():
    view = pjax_block("main", title_block="title_missing")(base_view)
    resp = view(pjax_request, test_template)
    _ = resp.rendered_content


@raises(ValueError)
def test_pjax_block_title_conflict():
    pjax_block("main", title_variable="title", title_block="title")(None)


def test_pjax_block_in_base_template():
    response = view_pjax_block(pjax_request, extends_template,
                               {'base_template': base_template})
    assert response.rendered_content == "base block content"


def test_pjax_block_in_base_file_template():
    response = view_pjax_block(pjax_request, extends_template,
                               {'base_template': file_template})
    assert response.rendered_content == "file base block content"


def test_pjax_url_header():
    response = view_pjax_block_auto(pjax_request, test_template)
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
    DjangoPJAXMiddleware().process_request(request)
    assert '_pjax' not in request.GET
    assert '_pjax' not in request.META['QUERY_STRING']


def test_middleware_configuration():

    configuration = (
        ('^/prefix/one', ('@pjax_template()',
                          '@pjax_block()')),
        ('^/prefix/two', '@pjax_block(block="secondary", title_block="title")'),
    )

    middleware = DjangoPJAXMiddleware(configuration)

    assert ((re.compile('^/prefix/two'), re.compile('^/prefix/one'))
            == tuple(url_re for url_re, _ in middleware.decorated_urls))

    request_one = rf.get('/prefix/one?_pjax=%23secondary',
                         HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#secondary")
    response_one = base_view(request_one, 'test_template.html')
    pjax_one = middleware.process_template_response(request_one, response_one)
    assert pjax_one.template_name == ('test_template-pjax=secondary.html',
                                      'test_template.html')

    request_two = rf.get('/prefix/two?_pjax=%23secondary',
                         HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#secondary")
    response_two = base_view(request_two, test_template)
    pjax_two = middleware.process_template_response(request_two, response_two)
    assert pjax_two.rendered_content == ('<title>Block Title</title>\n'
                                         'Some secondary content.')


def test_middleware_invalid_decorator():

    decorator_mistakes = (
        'pjax_block()',  # Missing @
        '@pjax_block',  # Not a function call
        '@pjax_blerk()',  # Not a known function
        '@pjax_block(*["main"])',  # Using star args
        '@pjax_block(**{block: "main"})',  # Using kwargs
        '@pjax_block("main_"[:-1])',  # Not a string
        '@pjax_block(block="main_"[:-1])'  # Not a string
    )

    for decorator in decorator_mistakes:
        assert_raises(ImproperlyConfigured,
                      DjangoPJAXMiddleware.parse_decorator,
                      decorator)


def test_strip_pjax_qs_parameter():
    strip_fn = strip_pjax_qs_parameter
    assert strip_fn('_pjax=%23container') == ''
    assert strip_fn('_pjax=%23container&second=2') == 'second=2'
    assert strip_fn('first=1&_pjax=%23container') == 'first=1'
    assert strip_fn('first=1&_pjax=%23container&second=2') == 'first=1&second=2'


@raises(TypeError)
def test_exception_on_non_deferred_response():
    _ = view_pjax_block_not_deferred(pjax_request)


@raises(ValueError)
def test_pjaxify_instance_error():
    pjaxify_template_path(test_template, None)


def test_pjaxify_template_var():
    pjaxify = pjaxify_template_var
    template_seq = ("test1.html", "test2")
    pjaxed_seq = ("test1-pjax.html", "test1.html",
                  "test2-pjax", "test2")
    assert pjaxify(pjax_request, template_seq[0]) == pjaxed_seq[:2]
    assert pjaxify(pjax_request, template_seq) == pjaxed_seq


def test_pjaxify_template_var_request():

    pjaxify = pjaxify_template_var_with_container
    assert pjaxify(pjax_request, "test.html") == ("test-pjax=secondary.html",
                                                  "test.html")
    template_seq = ("test1.html", "test2")
    pjaxed_seq = ("test1-pjax=secondary.html", "test1.html",
                  "test2-pjax=secondary", "test2")
    assert pjaxify(pjax_request, template_seq) == pjaxed_seq


def test_pjax_static_template():
    view = pjax_template('static_template.html')(base_view)
    resp = view(pjax_request, test_template)
    print(resp.template_name)
    assert resp.template_name == "static_template.html"


def test_registry():
    wrapped_classes = sorted([cls.__name__ for cls
                              in djpjax.template._wrapped_class_registry])
    assert wrapped_classes == ['ExtendsNode', 'NodeList', 'TemplateResponse']


@raises(NotImplementedError)
def test_object_wrapping_direct_instantiation():
    response = base_view(pjax_request, test_template)
    PJAXBlockTemplateResponse(response, None, None)


# The test "views" themselves.

def base_view(request, template, extra_context=None):
    extra_context = extra_context or dict()
    extra_context.update({"colour": "orange"})
    return TemplateResponse(request, template, extra_context)

view_pjax_block = pjax_block("main")(base_view)
view_pjax_block_auto = pjax_block()(base_view)


@pjax_block()
def view_pjax_block_redirect(_):
    return HttpResponseRedirect('/redirected/')


@pjax_block()
def view_pjax_block_not_deferred(_):
    return HttpResponse("Some text!")