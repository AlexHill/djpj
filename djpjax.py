import functools

from types import MethodType

from django.views.generic.base import TemplateResponseMixin
from django.template.response import TemplateResponse
from django.template import TemplateSyntaxError
from django.template.loader_tags import BlockNode


class PJAXBlockTemplateResponse(TemplateResponse):

    @property
    def rendered_content(self):
        """
        Walk the template's node tree, replacing the render method on the
        target block node (and optionally, the title block node) with one
        that captures its contents. Then we render the template as normal,
        but instead of returning the result, return the captured output
        from our target block(s).
        """
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)

        captured_blocks = dict()

        def capture_method_output(obj, method, callback):
            """
            Intercept the output of an instance method, by replacing it with
            a new method which passes the return value to a callback before
            returning it.
            """
            old_method = getattr(obj, method)
            def replacement_fn(_, *args, **kwargs):
                output = old_method(*args, **kwargs)
                callback(output)
                return output
            setattr(obj, method, MethodType(replacement_fn, obj))

        target_blocks = filter(None, (self.block_name, self.title_block))

        def patch_tree(nodelist):
            for node in nodelist:
                if isinstance(node, BlockNode) and node.name in target_blocks:
                    callback = functools.partial(captured_blocks.__setitem__,
                                                 node.name)
                    capture_method_output(node.nodelist, "render", callback)
                else:
                    if hasattr(node, "nodelist"):
                        patch_tree(node.nodelist)

        patch_tree(template.nodelist)

        # Render the template, but ignore its return value.
        # We will return the captured output from the target
        # and optionally the title blocks.
        template.render(context)

        try:
            target_block_content = captured_blocks[self.block_name]
        except KeyError:
            raise TemplateSyntaxError("Target PJAX block '%s' does not exist" % self.block_name)

        if self.title_block:
            try:
                title = captured_blocks[self.title_block]
            except KeyError:
                raise TemplateSyntaxError("Named PJAX target block '%s' does not exist" % self.title_block)
        elif self.title_variable:
            try:
                title = context[self.title_variable]
            except KeyError:
                raise KeyError("PJAX title variable '%s' not found in context" % self.title_variable)
        else:
            title = None

        title_html = "<title>%s</title>\n" % title if title else ""

        return title_html + target_block_content


def pjax_block(block, title_variable=None, title_block=None):
    if title_variable and title_block:
        raise TypeError("Only one of 'title_variable' and 'title_block' "
                        "may be passed to pjax decorator.")
    def pjax_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            if request.META.get('HTTP_X_PJAX', False):
                resp.__class__ = PJAXBlockTemplateResponse
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
