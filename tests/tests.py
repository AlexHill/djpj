import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect, HttpResponse
from django.template import Template, TemplateSyntaxError
from django.template.response import TemplateResponse

import pytest

import djpj.template
from djpj.decorator import pjax_block, pjax_template
from djpj.middleware import DjangoPJAXMiddleware
from djpj.template import PJAXTemplateResponse
from djpj.utils import *

settings.configure()

# This import has to go after settings.configure() in Django < 1.7
from django.test.client import RequestFactory  # noqa

if django.VERSION >= (1, 7):
    django.setup()

# Do a bit of wrangling to make old Django look like new Django,
# to avoid conditional branches in our tests themselves.
if django.VERSION >= (1, 8):
    from django.template import engines
    from django.template.backends.django import Template as DjangoTemplate

    settings.TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
                           'DIRS': ['tests/', '.']}]

    template_backend = engines['django']

    # The template API was refined in Django 1.9.
    if django.VERSION < (1, 9):
        class DjangoTemplate(DjangoTemplate):
            def __init__(self, template, _):
                super(DjangoTemplate, self).__init__(template)
else:
    # Fake the DjangoTemplate class entirely, and set the template.attribute
    # purely for call to DjPjTemplate.patch() in test_pjax_normal_request().
    # noinspection PyPep8Naming
    def DjangoTemplate(template, _):
        template.template = template
        return template
    template_backend = None

    settings.TEMPLATE_DIRS = ['tests/', '.']


# A couple of request objects - one PJAX, one not.
rf = RequestFactory()
regular_request = rf.get('/')
pjax_request = rf.get('/?_pjax=%23secondary',
                      HTTP_X_PJAX=True,
                      HTTP_X_PJAX_CONTAINER="#secondary")

file_template = 'test_template.html'

# A template to test the pjax_block decorator.
test_template = DjangoTemplate(Template(
    "{% block title %}Block Title{% endblock %}"
    "Some text outside the main block."
    "{% with footwear='galoshes' %}"
    "{% block main %}I'm wearing {{ colour }} {{ footwear }}{% endblock %}"
    "{% endwith %}"
    "{% block secondary %}Some secondary content.{% endblock %}"
    "More text outside the main block."), template_backend)

base_template = DjangoTemplate(Template(
    "{% block main %}base block content{% endblock %}\n"
    "{% block secondary %}secondary block content{% endblock %}"), template_backend)

extends_template = DjangoTemplate(Template(
    "{% extends base_template %}\n"
    "{% block secondary %}overridden {{ block.super }}{% endblock %}"), template_backend)


# Tests.

def test_pjax_block_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet_bloc")
    assert pjax_container(req) == "soviet_bloc"


def test_pjax_block_invalid_from_header():
    req = rf.get('/', HTTP_X_PJAX=True, HTTP_X_PJAX_CONTAINER="#soviet .bloc")
    with pytest.raises(ValueError):
        _ = pjax_container(req)


def test_pjax_block_no_pjax_container():
    request = rf.get('/', HTTP_X_PJAX=True)
    with pytest.raises(KeyError):
        _ = view_pjax_block_auto(request, None)


def test_pjax_block_none_arg():
    with pytest.raises(ValueError):
        pjax_block(None)


def test_pjax_template_none_arg():
    with pytest.raises(ValueError):
        pjax_template(None)


def test_pjax_template_no_result():
    with pytest.raises(ValueError):
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

    djpj.template.DjPjTemplate.patch(test_template.template)

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


def test_pjax_block_error():
    view = pjax_block("main_missing")(base_view)
    resp = view(pjax_request, test_template)
    with pytest.raises(TemplateSyntaxError):
        _ = resp.rendered_content


def test_pjax_block_title_variable():
    view = pjax_block("main", title_variable="title")(base_view)
    resp = view(pjax_request, test_template, {'title': 'Variable Title'})
    result = resp.rendered_content
    assert result == "<title>Variable Title</title>\nI'm wearing orange galoshes"


def test_pjax_block_title_variable_error():
    view = pjax_block("main", title_variable="title_missing")(base_view)
    resp = view(pjax_request, test_template, {'title': 'Variable Title'})
    with pytest.raises(KeyError):
        _ = resp.rendered_content


def test_pjax_block_title_block():
    view = pjax_block("main", title_block="title")(base_view)
    resp = view(pjax_request, test_template)
    result = resp.rendered_content
    assert result == "<title>Block Title</title>\nI'm wearing orange galoshes"


def test_pjax_block_title_block_error():
    view = pjax_block("main", title_block="title_missing")(base_view)
    resp = view(pjax_request, test_template)
    with pytest.raises(TemplateSyntaxError):
        _ = resp.rendered_content


def test_pjax_block_title_conflict():
    with pytest.raises(ValueError):
        pjax_block("main", title_variable="title", title_block="title")(None)


def test_pjax_block_in_base_template():
    response = view_pjax_block(pjax_request, extends_template,
                               {'base_template': base_template})
    assert response.rendered_content == "base block content"


def test_pjax_block_in_base_file_template():
    response = view_pjax_block(pjax_request, extends_template,
                               {'base_template': file_template})
    assert response.rendered_content == "file base block content"


def test_pjax_overridden_block():
    view_secondary_block = pjax_block("secondary")(base_view)
    response = view_secondary_block(pjax_request, extends_template,
                                    {'base_template': base_template})
    assert response.rendered_content == "overridden secondary block content"


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
        with pytest.raises(ImproperlyConfigured):
            DjangoPJAXMiddleware.parse_decorator(decorator)


def test_strip_pjax_qs_parameter():
    strip_fn = strip_pjax_qs_parameter
    assert strip_fn('_pjax=%23container') == ''
    assert strip_fn('_pjax=%23container&second=2') == 'second=2'
    assert strip_fn('first=1&_pjax=%23container') == 'first=1'
    assert strip_fn('first=1&_pjax=%23container&second=2') == 'first=1&second=2'


def test_exception_on_non_deferred_response():
    with pytest.raises(TypeError):
        _ = view_pjax_block_not_deferred(pjax_request)


def test_pjaxify_instance_error():
    with pytest.raises(ValueError):
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
    wrapped_classes = sorted(cls.__name__ for cls in djpj.template._wrapped_class_registry)
    assert wrapped_classes == ['ExtendsNode', 'NodeList', 'Template', 'TemplateResponse']


def test_object_wrapping_direct_instantiation():
    response = base_view(pjax_request, test_template)
    with pytest.raises(NotImplementedError):
        PJAXTemplateResponse(response, None, None)


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
