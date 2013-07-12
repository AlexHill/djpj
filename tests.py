# Django bootstrap, sigh.
from django.conf import settings; settings.configure()

import djpjax
from django.template.response import TemplateResponse
from django.test.client import RequestFactory
from django.views.generic import View
from django.template import Template, TemplateSyntaxError

from nose.tools import raises

# A couple of request objects - one PJAX, one not.
rf = RequestFactory()
regular_request = rf.get('/')
pjax_request = rf.get('/', HTTP_X_PJAX=True)

# A template to test the pjax_block decorator.
template = Template(
    "{% block title %}Block Title{% endblock %}"
    "Some text outside the main block."
    "{% with footwear='galoshes' %}"
    "{% block main %}I'm wearing {{ colour }} {{ footwear }}{% endblock %}"
    "{% endwith %}"
    "More text outside the main block.")

# Tests.

def test_pjax_block():
    resp = view_pjax_block(pjax_request)
    result = resp.rendered_content
    assert result == "I'm wearing orange galoshes"

@raises(TemplateSyntaxError)
def test_pjax_block_error():
    resp = view_pjax_block_error(pjax_request)
    result = resp.rendered_content

def test_pjax_block_title_variable():
    resp = view_pjax_block_title_variable(pjax_request)
    result = resp.rendered_content
    assert result == ("<title>Variable Title</title>\n"
                      "I'm wearing orange galoshes")

@raises(KeyError)
def test_pjax_block_title_variable_error():
    resp = view_pjax_block_title_variable_error(pjax_request)
    result = resp.rendered_content

def test_pjax_block_title_block():
    resp = view_pjax_block_title_block(pjax_request)
    result = resp.rendered_content
    assert result == ("<title>Block Title</title>\n"
                      "I'm wearing orange galoshes")

@raises(TemplateSyntaxError)
def test_pjax_block_title_block_error():
    resp = view_pjax_block_title_block_error(pjax_request)
    result = resp.rendered_content

@raises(TypeError)
def test_pjax_block_title_conflict():
    @djpjax.pjax_block("main", title_variable="title", title_block="title")
    def view_pjax_block_title_conflict(request):
        return TemplateResponse(request, template, {"colour": "orange",
                                                    "title": "Variable Title"})

def test_pjax_sans_template():
    resp = view_sans_pjax_template(regular_request)
    assert resp.template_name == "template.html"
    resp = view_sans_pjax_template(pjax_request)
    assert resp.template_name == "template-pjax.html"

def test_view_with_silly_template():
    resp = view_with_silly_template(regular_request)
    assert resp.template_name == "silly"
    resp = view_with_silly_template(pjax_request)
    assert resp.template_name == "silly-pjax"

def test_view_with_pjax_template():
    resp = view_with_pjax_template(regular_request)
    assert resp.template_name == "template.html"
    resp = view_with_pjax_template(pjax_request)
    assert resp.template_name == "pjax.html"

def test_view_with_template_tuple():
    resp = view_with_template_tuple(regular_request)
    assert resp.template_name == ("template.html", "other_template.html")
    resp = view_with_template_tuple(pjax_request)
    assert resp.template_name == ("template-pjax.html", "other_template-pjax.html")

def test_class_pjax_sans_template():
    view = NoPJAXTemplateVew.as_view()
    resp = view(regular_request)
    assert resp.template_name[0] == "template.html"
    resp = view(pjax_request)
    assert resp.template_name[0] == "template-pjax.html"

def test_class_with_silly_template():
    view = SillyTemplateNameView.as_view()
    resp = view(regular_request)
    assert resp.template_name[0] == "silly"
    resp = view(pjax_request)
    assert resp.template_name[0] == "silly-pjax"

def test_class_with_pjax_template():
    view = PJAXTemplateView.as_view()
    resp = view(regular_request)
    assert resp.template_name[0] == "template.html"
    resp = view(pjax_request)
    assert resp.template_name[0] == "pjax.html"

def test_pjaxtend_default():
    resp = view_default_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "base.html"
    resp = view_default_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "pjax.html"

def test_pjaxtend_default_parent():
    resp = view_default_parent_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "parent.html"
    resp = view_default_parent_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "pjax.html"

def test_pjaxtend_custom_parent():
    resp = view_custom_parent_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "parent.html"
    resp = view_custom_parent_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['parent'] == "parent-pjax.html"

def test_pjaxtend_custom_context():
    resp = view_custom_context_pjaxtend(regular_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['my_parent'] == "parent.html"
    resp = view_custom_context_pjaxtend(pjax_request)
    assert resp.template_name == "template.html"
    assert resp.context_data['my_parent'] == "parent-pjax.html"

# The test "views" themselves.

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

@djpjax.pjax()
def view_sans_pjax_template(request):
    return TemplateResponse(request, "template.html", {})
    
@djpjax.pjax()
def view_with_silly_template(request):
    return TemplateResponse(request, "silly", {})
    
@djpjax.pjax("pjax.html")
def view_with_pjax_template(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjax()
def view_with_template_tuple(request):
    return TemplateResponse(request, ("template.html", "other_template.html"), {})

@djpjax.pjaxtend()
def view_default_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjaxtend('parent.html')
def view_default_parent_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjaxtend('parent.html', 'parent-pjax.html')
def view_custom_parent_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

@djpjax.pjaxtend('parent.html', 'parent-pjax.html', 'my_parent')
def view_custom_context_pjaxtend(request):
    return TemplateResponse(request, "template.html", {})

class NoPJAXTemplateVew(djpjax.PJAXResponseMixin, View):
    template_name = 'template.html'

    def get(self, request):
        return self.render_to_response({})

class SillyTemplateNameView(djpjax.PJAXResponseMixin, View):
    template_name = 'silly'

    def get(self, request):
        return self.render_to_response({})

class PJAXTemplateView(djpjax.PJAXResponseMixin, View):
    template_name = 'template.html'
    pjax_template_name = 'pjax.html'
    
    def get(self, request):
        return self.render_to_response({})
