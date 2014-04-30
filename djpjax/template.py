from django.template import TemplateSyntaxError

# TODO: Find out why Django raises InvalidTemplateLibrary without this import.
from django.template.loader import get_template

from django.template.loader_tags import BlockNode, ExtendsNode

from djpjax.compat import queue

_wrapped_class_registry = {}


class PJAXObject(object):
    """
    Base object used for wrapping various Django template structures. The
    """

    def __new__(cls, *args, **kwargs):
        raise NotImplementedError("%s cannot be instantiated directly. "
                                  "Use the cast() method instead." % cls)

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def cast(cls, obj, *args, **kwargs):
        if not isinstance(obj, cls):
            try:
                new_class = _wrapped_class_registry[obj.__class__]
            except KeyError:
                new_class = type("PJAX" + obj.__class__.__name__,
                                 (cls, obj.__class__), {})
                _wrapped_class_registry[obj.__class__] = new_class
            obj.__class__ = new_class
        obj.__init__(*args, **kwargs)
        return obj


class PJAXNodeList(PJAXObject):
    """
    When using the pjax_block decorator, the nodelists of matching BlockNodes
    are set to this class. We override the NodeList instead of BlockNode
    because sometimes in the rendering process, an entirely new BlockNode is
    created and rendered (see BlockNode.render() in template/loader_tags.py),
    bypassing any overridden behaviour in our subclass.
    """

    def __init__(self, block_name):
        self.block_name = block_name

    def render(self, context):
        result = super(PJAXNodeList, self).render(context)
        if '_pjax_captured_blocks' in context.__dict__:
            # If using the cached template loader, this method might be called
            # even for non-PJAX requests, in which case capture nothing.
            context._pjax_captured_blocks[self.block_name] = result
        return result


class PJAXExtendsNode(PJAXObject):
    def get_parent(self, context, *args, **kwargs):
        if not hasattr(context, '_pjax_cached_parents'):
            context._pjax_cached_parents = dict()
        try:
            parent = context._pjax_cached_parents[self]
            del context._pjax_cached_parents[self]
        except KeyError:
            parent = super(PJAXExtendsNode, self).get_parent(context, *args, **kwargs)
            context._pjax_cached_parents[self] = parent
        return parent


class PJAXBlockTemplateResponse(PJAXObject):
    """
    When a view decorated with pjax_block is called, its TemplateResponses are
    set to this class.
    """

    def __init__(self, block_name, title_block_name, title_variable):
        self.block_name = block_name
        self.title_block_name = title_block_name
        self.title_variable = title_variable

    @property
    def rendered_content(self):
        """
        Walk the template's node tree, casting our target blocks' nodelists to
        PJAXBlockNodeList in order to store its output in the render context.
        Then render the template as usual, but instead of returning the result,
        return the captured output from our target block(s).
        """
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)

        # If no block name is specified, assume we're rendering a PJAX-specific
        # template and just return the rendered output.
        if not self.block_name:
            return template.render(context)

        # Otherwise, proceed to capture the output from the pjax block and,
        # if specified, the title block or variable.

        captured_blocks = dict()
        context._pjax_captured_blocks = captured_blocks

        target_blocks = set(n for n in (self.block_name,
                                        self.title_block_name) if n)

        node_queue = queue.Queue()
        node_queue.put(template)
        while target_blocks:
            try:
                node = node_queue.get(False)
            except queue.Empty:
                break
            if hasattr(node, 'nodelist'):
                if isinstance(node, BlockNode) and node.name in target_blocks:
                    PJAXNodeList.cast(node.nodelist, node.name)
                    target_blocks.remove(node.name)
                for child_node in node.nodelist:
                    node_queue.put(child_node)
            if isinstance(node, ExtendsNode):
                PJAXExtendsNode.cast(node)
                for child_node in node.get_parent(context).nodelist:
                    node_queue.put(child_node)
        del node_queue

        # Render the template, but ignore its return value. We will return the
        # captured output from the target and optionally the title blocks.
        template.render(context)

        try:
            target_block_content = captured_blocks[self.block_name]
        except KeyError:
            raise TemplateSyntaxError(
                "PJAX block '%s' does not exist or was not rendered"
                % self.block_name)

        if self.title_block_name:
            try:
                title = captured_blocks[self.title_block_name]
            except KeyError:
                raise TemplateSyntaxError(
                    "PJAX title block '%s' does not exist or was not rendered"
                    % self.title_block_name)
        elif self.title_variable:
            try:
                title = context[self.title_variable]
            except KeyError:
                raise KeyError(
                    "PJAX title variable '%s' not found in context"
                    % self.title_variable)
        else:
            title = None

        title_html = "<title>%s</title>\n" % title if title else ""

        return title_html + target_block_content