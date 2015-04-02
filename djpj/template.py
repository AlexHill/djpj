from django import VERSION as DJANGO_VERSION

from django.template import TemplateSyntaxError, NodeList, Template
if DJANGO_VERSION >= (1, 8):
    from django.template.context import make_context

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
    This is a base class used for wrapping various Django template structures.
    This works by dynamically changing the type of various objects, so beware!

    The purpose of DjPjObject is essentially to monkey-patch arbitrary objects
    in a very visible way, making use of Python's class system instead of
    overriding instance methods for transparent debugging and IDE-friendliness.

    To use, define your patched methods on a subclass of DjPjObject, then
    pass the object you want to patch to patch(). The object's type will be
    swapped to one that includes your patch class in its class hierarchy, and
    Python's method resolution machinery will call the patched methods instead
    of their original counterparts. You can use self and super in your methods
    as if you were subclassing normally.

    Optionally, you can include additional base classes. In that case, you'll
    see an error if you try to patch an object that is not an instance of
    every extra base class.
    """

    def __new__(cls, *args, **kwargs):
        raise NotImplementedError("%s cannot be instantiated directly. "
                                  "Use the patch() method instead." % cls)

    def __patch__(self, *args, **kwargs):
        """
        This is kind of like __init__, but run after an object is patched,
        rather than after it's created. Override it to provide patch-time
        behaviour.
        """
        pass

    @classmethod
    def patch(cls, obj, *args, **kwargs):
        """
        Create (or fetch from cache) a new class that inherits from both cls
        and the passed object's class.
        """
        if not isinstance(obj, cls):
            for base_class in cls.__bases__[1:]:
                if not isinstance(obj, base_class):
                    raise RuntimeError(
                        "Object to be patched by %s is not an instance of %s"
                        % (cls.__name__, base_class.__name__))
            obj_class = type(obj)
            try:
                new_class = _wrapped_class_registry[obj_class]
            except KeyError:
                new_class = type("DjPj" + obj_class.__name__,
                                 (cls, obj_class), {})
                _wrapped_class_registry[obj_class] = new_class
            obj.__class__ = new_class
            obj.__patch__(*args, **kwargs)
        return obj


class DjPjNodeList(DjPjObject, NodeList):
    """
    When using the pjax_block decorator, the nodelists of matching BlockNodes
    are set to this class. We override the NodeList instead of BlockNode
    because during the rendering process, an entirely new BlockNode is created
    and rendered (see BlockNode.render() in django/template/loader_tags.py),
    bypassing any overridden behaviour in our subclass.
    """

    def __patch__(self, block_name):
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
        parent = super(DjPjExtendsNode, self).get_parent(*args, **kwargs)
        DjPjTemplate.patch(parent)
        return parent


class DjPjTemplate(DjPjObject, Template):
    """
    Use this by casting your template with DjPjTemplate.patch(template), and
    then calling template.render_blocks(context, blocks), where blocks is a
    sequence of block names you wish to render.
    """

    def __patch__(self):
        self._djpj_initialised_blocks = self._initialise_blocks()

    def _initialise_blocks(self):
        """
        Walk the template tree and convert all necessary objects into their
        DjPj equivalents. This includes ExtendsNodes and BlockNodes' NodeLists
        (but not BlockNodes themselves as they're not actually rendered from
        the template tree - see the source for BlockNode.render().
        """
        blocks = dict()
        node_queue = queue.Queue()
        node_queue.put(self)
        while True:
            try:
                node = node_queue.get(False)
            except queue.Empty:
                break
            if hasattr(node, 'nodelist'):
                if isinstance(node, BlockNode):
                    DjPjNodeList.patch(node.nodelist, node.name)
                    blocks[node.name] = node
                for child_node in node.nodelist:
                    node_queue.put(child_node)
            if isinstance(node, ExtendsNode):
                DjPjExtendsNode.patch(node)
        del node_queue

        return blocks

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
    This is used by the PJAX decorator. Before a response is returned, this
    class is inserted into its type hierarchy, so that we can intercept calls
    to rendered_content() and instead
    it's inserted into its type hierarchy, so that when rendered_content is
    accessed, we
    """

    def __patch__(self, block_name, title_block_name, title_variable):
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

        # just for convenience
        block = self._djpj_block_name
        title_block = self._djpj_title_block_name
        title_var = self._djpj_title_variable

        # If no block name is specified, assume we're rendering a PJAX-specific
        # template and just return the rendered output.
        if not block:
            return super(PJAXTemplateResponse, self).rendered_content

        # Get a Template object
        template = self.resolve_template(self.template_name)

        # In Django 1.8, resolve_template doesn't return a django.template.Template
        # but rather a django.template.backends.django.Template which has a
        # django.template.Template as its "template" attribute. Template template.
        # Also, resolve_context returns a backend-agnostic dict, not a Context.
        if DJANGO_VERSION >= (1, 8):
            context = (make_context(self.context_data, self._request)
                       if isinstance(self.context_data, dict) else self.context_data)
            template = template.template
        else:
            context = self.resolve_context(self.context_data)

        # Otherwise, proceed to capture the output from the pjax block and,
        # if specified, the title block or variable.
        DjPjTemplate.patch(template)
        target_blocks = filter(None, (block, title_block))
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
