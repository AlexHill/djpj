from contextlib import contextmanager
import functools
import re
from django.template.response import TemplateResponse
from django.template import TemplateSyntaxError, NodeList
from django.template.loader_tags import BlockNode
from django.views.decorators.vary import vary_on_headers


class PJAXBlockNodeList(NodeList):
    """
    When using the pjax_block decorator, matching blocks' nodelists are set
    to this class. The overridden render method stores the block's output in
    the render context for later retrieval, before returning as normal.
    """

    def render(self, context):
        result = super(PJAXBlockNodeList, self).render(context)
        context.render_context["pjax_captured_blocks"][self.block_name] = result
        return result


class PJAXBlockTemplateResponse(TemplateResponse):

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

        captured_blocks = dict()
        context.render_context["pjax_captured_blocks"] = captured_blocks

        target_blocks = [n for n in (self.block_name, self.title_block) if n]

        def patch_tree(nodelist):
            for node in nodelist:
                if isinstance(node, BlockNode) and node.name in target_blocks:
                    node.nodelist.__class__ = PJAXBlockNodeList
                    node.nodelist.block_name = node.name
                else:
                    if hasattr(node, "nodelist"):
                        patch_tree(node.nodelist)

        patch_tree(template.nodelist)

        # Render the template, but ignore its return value. We will return the
        # captured output from the target and optionally the title blocks.
        template.render(context)

        try:
            target_block_content = captured_blocks[self.block_name]
        except KeyError:
            raise TemplateSyntaxError(
                "PJAX block '%s' does not exist or was not rendered"
                % self.block_name)

        if self.title_block:
            try:
                title = captured_blocks[self.title_block]
            except KeyError:
                raise TemplateSyntaxError(
                    "PJAX title block '%s' does not exist or was not rendered"
                    % self.title_block)
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


_container_re = re.compile(r'^#\S+$')


def _pjax_container_from_get(request):
    return request.GET.get("_pjax", None)


def _pjax_container_from_header(request):
    return request.META.get("HTTP_X_PJAX_CONTAINER", None)


def _pjax_block_from_request(request):
    container = (_pjax_container_from_header(request) or
                 _pjax_container_from_get(request))
    if container:
        if _container_re.match(container):
            return container[1:]
        else:
            raise ValueError("Invalid PJAX selector '%s' found in request: "
                             "must be a simple ID selector of the form #<id>."
                             % container)
    else:
        return None


def pjax_block(block=None, title_variable=None, title_block=None):
    if title_variable and title_block:
        raise TypeError("Only one of 'title_variable' and 'title_block' "
                        "may be passed to pjax decorator.")

    def pjax_decorator(view):
        @functools.wraps(view)
        def wrapped_view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            if request.META.get('HTTP_X_PJAX', False):
                block_name = block or _pjax_block_from_request(request)
                if not block_name:
                    raise ValueError(
                        "A PJAX block name must be supplied, either by the "
                        "`block` argument, the X-PJAX-Container HTTP header "
                        "or the _pjax GET parameter.")
                resp.__class__ = PJAXBlockTemplateResponse
                resp.block_name = block_name
                resp.title_variable = title_variable
                resp.title_block = title_block
            return resp
        return vary_on_headers('X-PJAX')(wrapped_view)
    return pjax_decorator


class DjangoPJAXMiddleware(object):

    @staticmethod
    def is_pjax(request):
        return 'HTTP_X_PJAX' in request.META

    @staticmethod
    def strip_pjax_qs_parameter(url):
        return re.sub(r'_pjax=[^&]+&?', '', url).rstrip('&')

    @staticmethod
    @contextmanager
    def mutable_querydict(querydict):
        initially_mutable = querydict._mutable
        querydict._mutable = True
        yield querydict
        querydict._mutable = initially_mutable

    def process_request(self, request):
        # The _pjax GET parameter helps browsers with caching, but is
        # unnecessary with the presence of the X-PJAX-Container header,
        # and can cause trouble with code that doesn't expect it, so let's
        # just pretend it never existed.
        if self.is_pjax(request):
            if '_pjax' in request.GET:
                with self.mutable_querydict(request.GET) as get:
                    del get['_pjax']
                request.META['QUERY_STRING'] = \
                    self.strip_pjax_qs_parameter(request.META['QUERY_STRING'])

    def process_response(self, request, response):
        # Setting this header makes PJAX behave properly with redirects.
        if self.is_pjax(request):
            response['X-PJAX-URL'] = (response.get('Location')
                                      or request.get_full_path())
        return response