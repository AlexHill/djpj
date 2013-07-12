import functools

from types import MethodType

from django.views.generic.base import TemplateResponseMixin
from django.template.response import TemplateResponse
from django.template import Template, NodeList, TemplateSyntaxError
from django.template.loader_tags import BlockNode


class SingleBlockTemplateResponse(TemplateResponse):

    @property
    def rendered_content(self):
        """
        Patch the template's node tree, replacing the render method on the
        target block node with one that captures its contents, and on each
        leaf node outside of the target node's subtree with a method that
        returns an empty string.
        """
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)

        target_block_content = []
        title = []
        if self.title_variable:
            title.append(context[self.title_variable])

        def return_empty_string(node, _): return ""

        def patch_tree(nodelist):
            for node in nodelist:
                if isinstance(node, BlockNode):
                    if node.name == self.block_name:
                        # Replace the target block's render method with one
                        # that captures the its content in target_block_content.
                        old_render_func = node.render
                        def render_target_block(node, context):
                            content = old_render_func(context)
                            target_block_content.append(content)
                            return content
                        node.render = MethodType(render_target_block, node)
                    elif node.name == self.title_block:
                        title_render_func = node.render
                        def render_title_block(node, context):
                            title_content = title_render_func(context)
                            title.append(title_content)
                            return title_content
                        node.render = MethodType(render_title_block, node)
                else:
                    if hasattr(node, "nodelist"):
                        patch_tree(node.nodelist)
                    else:
                        # Don't waste time rendering irrelevant leaf nodes.
                        node.render = MethodType(return_empty_string, node)
        patch_tree(template.nodelist)

        # Render the template, but ignore its output. We will return the
        # captured output from the target and optionally the title blocks.
        _ = template.render(context)

        if not target_block_content:
            raise TemplateSyntaxError("Target PJAX block does not exist")
        if not title:
            if self.title_block:
                raise TemplateSyntaxError(
                    "Named PJAX target block '%s' does not exist" % self.title_block)
            elif self.title_variable:
                raise ValueError(
                    "PJAX title variable '%s' not found in context" % self.title_variable)
            title_html = ""
        else:
            title_html = "<title>%s</title>\n" % title[0] if title else ""
        return title_html + target_block_content[0]


def pjax_block(block, title_variable=None, title_block=None):
    if title_variable and title_block:
        raise TypeError("Only one of 'title_variable' and 'title_block' "
                        "may be passed to pjax decorator.")
    def pjax_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            if request.META.get('HTTP_X_PJAX', False):
                from django.template.defaulttags import WithNode
                resp.__class__ = SingleBlockTemplateResponse
                resp.block_name = block
                resp.title_variable = title_variable
                resp.title_block = title_block
            return resp
        return _view
    return pjax_decorator

def pjax(pjax_template=None):
    def pjax_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            # this is lame. what else though?
            # if not hasattr(resp, "is_rendered"):
            #     warnings.warn("@pjax used with non-template-response view")
            #     return resp
            if request.META.get('HTTP_X_PJAX', False):
                if pjax_template:
                    resp.template_name = pjax_template
                else:
                    resp.template_name = _pjaxify_template_var(resp.template_name)
            return resp
        return _view
    return pjax_decorator

def pjaxtend(parent='base.html', pjax_parent='pjax.html', context_var='parent'):
    def pjaxtend_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            # this is lame. what else though?
            # if not hasattr(resp, "is_rendered"):
            #     warnings.warn("@pjax used with non-template-response view")
            #     return resp
            if request.META.get('HTTP_X_PJAX', False):
                resp.context_data[context_var] = pjax_parent
            elif parent:
                resp.context_data[context_var] = parent
            return resp
        return _view
    return pjaxtend_decorator

class PJAXResponseMixin(TemplateResponseMixin):

    pjax_template_name = None

    def get_template_names(self):
        names = super(PJAXResponseMixin, self).get_template_names()
        if self.request.META.get('HTTP_X_PJAX', False):
            if self.pjax_template_name:
                names = [self.pjax_template_name]
            else:
                names = _pjaxify_template_var(names)
        return names


def _pjaxify_template_var(template_var):
    if isinstance(template_var, (list, tuple)):
        template_var = type(template_var)(_pjaxify_template_name(name) for name in template_var)
    elif isinstance(template_var, basestring):
        template_var = _pjaxify_template_name(template_var)
    return template_var


def _pjaxify_template_name(name):
    if "." in name:
        name = "%s-pjax.%s" % tuple(name.rsplit('.', 1))
    else:
        name += "-pjax"
    return name
