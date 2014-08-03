from django.template import TemplateSyntaxError, NodeList, Template

# TODO: Find out why Django raises InvalidTemplateLibrary without this import.
from django.template.loader import get_template

from django.template.loader_tags import BlockNode, ExtendsNode
from django.template.response import SimpleTemplateResponse

from djpj.compat import queue

_wrapped_class_registry = {}


class StopRendering(Exception):
    """
    Thrown in DjPjNodeList.render() when all template blocks have been found
    and rendered, to stop rendering the rest of the page, which saves a bit of
    template rendering time.
    """
    pass


class DjPjObject(object):
    """
    Base class used for wrapping various Django template structures. This
    works by dynamically changing the type of various objects, so beware!

    Use by defining a subclass of DjPjObject which overrides a method in the
    class you want to wrap, then passing an object to cast().
    """

    def __new__(cls, *args, **kwargs):
        raise NotImplementedError("%s cannot be instantiated directly. "
                                  "Use the cast() method instead." % cls)

    def __init__(self, *args, **kwargs):
        """
        If you override __init__, it will be called when you call cast(). This
        is safe; the wrapped class' __init__ won't be called again.
        """
        pass

    @classmethod
    def cast(cls, obj, *args, **kwargs):
        if not isinstance(obj, cls):
            try:
                new_class = _wrapped_class_registry[obj.__class__]
            except KeyError:
                new_class = type("DjPj" + obj.__class__.__name__,
                                 (cls, obj.__class__), {})
                _wrapped_class_registry[obj.__class__] = new_class
            obj.__class__ = new_class
            obj.__init__(*args, **kwargs)
        return obj


class DjPjNodeList(DjPjObject, NodeList):
    """
    When using the pjax_block decorator, the nodelists of matching BlockNodes
    are set to this class. We override the NodeList instead of BlockNode
    because during the rendering process, an entirely new BlockNode is created
    and rendered (see BlockNode.render() in django/template/loader_tags.py),
    bypassing any overridden behaviour in our subclass.
    """

    def __init__(self, block_name):
        self._djpj_block_name = block_name

    def render(self, context):
        result = super(DjPjNodeList, self).render(context)
        try:
            if self._djpj_block_name in context.djpj_blocks:
                context.djpj_blocks[self._djpj_block_name] = result
                if None not in context.djpj_blocks.values():
                    raise StopRendering
        except AttributeError:
            pass
        return result


class DjPjExtendsNode(DjPjObject, ExtendsNode):
    def get_parent(self, *args, **kwargs):
        compiled_parent = super(DjPjExtendsNode, self).get_parent(*args, **kwargs)
        DjPjTemplate.cast(compiled_parent)
        return compiled_parent


class DjPjTemplate(DjPjObject, Template):
    """
    Use this by casting your template with DjPjTemplate.cast(template), and
    then calling template.render_blocks(context, blocks), where blocks is a
    sequence of block names you wish to render.
    """

    def __init__(self):
        self._djpj_initialised_blocks = set()
        self._initialise_blocks()

    def _initialise_blocks(self):
        """
        Walk the template tree and convert all necessary objects into their
        DjPj equivalents. This includes ExtendsNodes and BlockNodes' NodeLists
        (but not BlockNodes themselves as they're not actually rendered from
        the template tree - see the source for BlockNode.render().
        """
        node_queue = queue.Queue()
        node_queue.put(self)
        while True:
            try:
                node = node_queue.get(False)
            except queue.Empty:
                break
            if hasattr(node, 'nodelist'):
                if isinstance(node, BlockNode):
                    DjPjNodeList.cast(node.nodelist, node.name)
                    self._djpj_initialised_blocks.add(node.name)
                for child_node in node.nodelist:
                    node_queue.put(child_node)
            if isinstance(node, ExtendsNode):
                DjPjExtendsNode.cast(node)
        del node_queue

    def render_blocks(self, context, blocks):
        """
        Return a dict mapping block names to their rendered contents. If a
        block is not rendered, its name will map to None.
        """
        context.djpj_blocks = dict((b, None) for b in blocks if b)
        try:
            self.render(context)
        except StopRendering:
            pass
        return context.djpj_blocks


class PJAXTemplateResponse(DjPjObject, SimpleTemplateResponse):
    """
    When a view decorated with pjax_block is called, its TemplateResponses are
    set to this class.
    """

    def __init__(self, block_name, title_block_name, title_variable):
        self._djpj_block_name = block_name
        self._djpj_title_block_name = title_block_name
        self._djpj_title_variable = title_variable

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

        # just for convenience
        block = self._djpj_block_name
        title_block = self._djpj_title_block_name
        title_var = self._djpj_title_variable

        # If no block name is specified, assume we're rendering a PJAX-specific
        # template and just return the rendered output.
        if not block:
            return template.render(context)

        # Otherwise, proceed to capture the output from the pjax block and,
        # if specified, the title block or variable.
        target_blocks = filter(None, (block, title_block))
        DjPjTemplate.cast(template)
        rendered_blocks = template.render_blocks(context, target_blocks)

        # Get all our error handling out of the way before generating
        # our PJAX-friendly output
        if None in rendered_blocks.values():
            raise TemplateSyntaxError("Template block '%s' does not exist or was not rendered" % block)
        if title_var and title_var not in context:
            raise KeyError("PJAX title variable '%s' not found in context" % title_var)

        # Return our PJAX response including a <title> tag if necessary
        block_contents = rendered_blocks[block]
        title_contents = rendered_blocks.get(title_block, None) or context.get(title_var)
        title_html = "<title>%s</title>\n" % title_contents if title_contents else ""

        return title_html + block_contents