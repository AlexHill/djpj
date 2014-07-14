
Usage
=====

PJAX requires cooperation between your front-end (the Javascript that runs in
your visitors' web browsers) and your Django backend.


Setting up the front-end with jquery-pjax
-----------------------------------------

The front end is handled by the jquery-pjax library, so first of all, read about
`how to use jQuery-PJAX`__ and pick one of the techniques there.

__ https://github.com/defunkt/jquery-pjax


Setting up the back-end with DjPj
---------------------------------

First, make sure the views you're PJAXing return TemplateResponse__. You
can't use DjPj with a normal ``HttpResponse``; only
``TemplateResponse``.

__ https://docs.djangoproject.com/en/dev/ref/template-response/


Returning a single template block
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Decorate your views with ``pjax_block`` to return the contents of a single
Django template block to PJAX requests.

Say you want to use PJAX to load different blog posts. Your template might look
like this::

    <header>...</header>

    <article>
    {% block blog_post %}
    ...
    {% endblock %}
    </article>

    <footer>...</footer>

Then you could write the following view::

    from djpj import pjax_block

    @pjax_block("blog_post")
    def my_view(request)
        context = ...
        return TemplateResponse(request, "template.html", context)

Now this view will respond to PJAX requests with only the content of the
``blog_post`` block.


Including a page title in the PJAX response
```````````````````````````````````````````

A nice feature of the PJAX library is that it correctly updates the page title
when new content is loaded. It achieves this by looking for a ``<title>`` tag
in the HTML response. Of course, it's unlikely that your standard template's
``<title>`` tag is going to be inside the block that you want to return - if it
is, you should probably rethink the way you're using PJAX!

The ``pjax_block`` decorator solves this problem by allowing you to specify either
a context variable or a template block containing your page's title text, using
the ``title_variable`` or ``title_block`` arguments. If you pass both arguments to
``pjax_block`` at the same time, you'll get an exception.

Say you assigned your title to a context variable called ``post_title``, and you
want the contents of that context variable to be used by PJAX as the page title.
Your view would look like this::

    from djpj import pjax_block

    @pjax_block("blog_post", title_variable="post_title")
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)

The way ``title_block`` works is very similar. If your template has a block named
"page_title" containing your title text, your decorator line should look like this::

    @pjax_block("blog_post", title_block="page_title")

This is useful if your page titles are rendered using template tags or multiple
context variables.


Using a different template for PJAX requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also use a specific template for PJAX requests, instead of returning a
specific block. To do this, use the ``pjax_template`` decorator, and pass your
PJAX template's name as the first argument::

    from djpj import pjax_template

    @pjax_template("pjax_template.html")
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)

Your template should include a ``<title>`` tag if you want the title to be
updated in the user's web browser.


Automatically selecting blocks or templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In PJAX terms, the "container" is the DOM element whose contents are to be
replaced by the HTML fragment you return from your view. When you enable PJAX
for your links or forms, `you specify the container as a CSS selector`__. That
CSS selector is passed to your server with every PJAX request.
DjPj can use that information to automatically select blocks or templates.

__ https://github.com/defunkt/jquery-pjax#usage


Automatically selecting blocks
``````````````````````````````

To automatically select a template block to return, the following must be true:

* The container must be specified with a simple CSS ID selector, e.g. ``#main_content``.
* Your block names must be identical to their containers' IDs.

To demonstrate, this means your templates should look like this::

    ...

    <article id="blog_post">
    {% block blog_post %}
    ...
    {% endblock %}
    </article>

    ...


So, with your templates set up, how do you make your views automatically select
the right template block? Just omit the initial ``block`` argument when
decorating your view with ``pjax_block``::

    from djpj import pjax_block

    @pjax_block(title_variable="post_title")
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)


If no container name is sent with the request, if a block with the given name
doesn't exist or isn't rendered (e.g. as an effect of conditional logic in your
template), or if a CSS selector other than a simple ``#<id>`` selector is found
in the request when no block name has been passed to ``pjax_block``, an
exception will be raised.

Automatically selecting templates
`````````````````````````````````

Similarly, DjPj can automatically select a template to use when responding to
PJAX requests, according to the container name sent with the request.

Simply omit the initial ``template`` argument when decorating your view with
``pjax_template``, and DjPj will "pjaxify" your response's normal template_name
variable::

    from djpj import pjax_template

    @pjax_template()
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)

By default, DjPj will insert "-pjax:<container_name>" before the
file extension of your template name. In this case, if your PJAX container were
specified with "#blog_post" as in the previous examples, DjPj
would set the template_name attribute of the TemplateResponse to
``("template-pjax:blog_post.html", "template.html")``.

If you want a single template for all PJAX requests for a single view, pass the
function ``djpj.utils.pjaxify_template_var`` as the first argument::

    from djpj import pjax_template
    from djpj.utils import pjaxify_template_var

    @pjax_template(pjaxify_template_var)
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)

In this example, the TemplateResponse's ``template_name`` attribute will be set
to ("template-pjax.html", "template.html").


Customising DjPj's automatic block/template selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the ``pjax_block`` decorator with no ``block`` argument will look
for a template block with the same name as the PJAX container, and similarly,
``pjax_template`` with no ``template`` argument will look for a template based
on the PJAX container name as described above. If you want to, you can change
this behaviour by passing a function as the first argument to these decorators.


Customising pjax_block
``````````````````````
In the case of ``pjax_block``, you should pass a function which accepts a
Django HttpRequest object, and returns a template block name. The following
example maps arbitrary container names to block names, with a default fallback::

    from djpj import pjax_block
    from djpj.utils import pjax_container_from_request

    container_block_map = {
        'book_metadata': 'product_detail',
        'cart_preview': 'shopping_cart',
    }

    def block_name_fn(request):

        # One of several utility functions found in DjPj.utils
        container_name = pjax_container_from_request(request)

        # Returning None here will mean the entire template is returned
        return container_block_map.get(container_name, None)

    @pjax_block(block_name_fn)
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)


The function takes a Django HttpRequest object, and returns a template block
name in the case of ``pjax_block``, or a Django template variable in the case
of ``pjax_template``. A "template variable", in this case means anything that
Django can use as the ``template`` argument when creating a ``TemplateResponse``
object, which could be a path to a template, a sequence of such paths, or a
Template object.


Customising pjax_template
`````````````````````````
To customise pjax_template, pass it a function with two arguments. The first
is the Django HttpRequest object, and the second is the value of the returned
TemplateResponse's ``template_name`` attribute. That attribute will be replaced
with the return value of your function.

In the example below, we'll search a subdirectory for PJAX templates, ignoring
the container name::

    from djpj import pjax_template
    from djpj.utils import transform_template_var
    from os.path import split, join

    def transform_path(template_path):
        dir, file = split(template_name)
        return join(dir, 'pjax', file)

    def pjax_templates_subdir(request, template_var):
        # This function inserts transformed items before each item in list or
        # tuple, and handles the case where the template_var is a single string
        return transform_template_var(transform_path, template_var)

    @pjax_template(pjax_templates_subdir)
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)


Using DjPj with third-party views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you're using a Django app which defines its own views, you can't easily
decorate them as you would views you write yourself.

In these cases, you can apply DjPj's decorators to URLs matching
particular regular expressions, via the included middleware.

To enable the middleware, add this line to the end of ``MIDDLEWARE_CLASSES``
in your settings.py::

    "djpj.middleware.DjangoPJAXMiddleware",

Configure the middleware using the the ``DJPJ_PJAX_URLS`` setting. This
should be a sequence of pairs, with the first element of each pair a regular
expression matching the URLs you want decorated, and the second a string, or a
sequence of strings, describing one or more PJAX decorators exactly as you would
in Python code.

For example, the following configuration will return the contents of the block
"product_info", with the value of the context variable "product_name" as the
title::

    DJPJ_PJAX_URLS = (
        ('^/shop/product/', '@pjax_block("product_info", title_variable="product_name")'),
    )


Considerations
==============

Any performance benefits are strictly client-side using this package;
performance on the server side will be strictly equal to or worse than simply
rendering the full template at this stage, since the full template is actually
rendered with the irrelevant parts discarded. This may change in the future.

This package doesn't support Django's class-based views, because the author
doesn't use them much; this will change in the future and contributions in this
area are welcome.

