Django-PJAX-Blocks
==================

Django-PJAX-Blocks is a flexible Django helper for `defunkt's jquery-pjax`__.
PJAX is a way to update a fragment of a web page with fresh data from the
server, without performing a full page refresh. Django-PJAX-Blocks lets you
respond to each PJAX request with the contents of a specific block in your
normal template, or with an entirely separate template.

__ https://github.com/defunkt/jquery-pjax

Django-PJAX-Blocks can return different blocks or templates from a single view,
depending on the target container of each PJAX request. Read more on this below.

Django-PJAX-Blocks was originally adapted from Jacob Kaplan-Moss' `Django-PJAX`__.

__ https://github.com/jacobian/django-pjax

This package is tested in Django 1.4+ and Python 2.6, 2.7, 3.3+ and PyPy.


What's PJAX?
------------

PJAX is a method of replacing a chunk of content in a web page without requiring
a complete page reload. It uses AJAX and pushState to deliver a faster browsing
experience with real permalinks, page titles, and a working back button.

A demo makes more sense, so `check out the one defunkt put together`__

__ http://pjax.heroku.com/


Usage
=====

PJAX requires cooperation between your front-end (the Javascript that runs in
your visitors' web browsers) and your Django backend.


Setting up the front-end with jquery-pjax
-----------------------------------------

The front end is handled by the jquery-pjax library, so first of all, read about
`how to use jQuery-PJAX`__ and pick one of the techniques there.

__ https://github.com/defunkt/jquery-pjax


Setting up the back-end with Django-PJAX-Blocks
-----------------------------------------------

First, make sure the views you're PJAXing return TemplateResponse__. You
can't use Django-PJAX-Blocks with a normal ``HttpResponse``; only
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

    from djpjax import pjax_block

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

    from djpjax import pjax_block

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

    from djpjax import pjax_template

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
Django-PJAX-Blocks can use that information to automatically select blocks or templates.

__ https://github.com/defunkt/jquery-pjax#usage


.. note:: For automatic selection to work, you need to be using a version of
   jquery-pjax no older than `this April 2012 commit`__. Any 1.x version or
   higher is fine.

   __ https://github.com/defunkt/jquery-pjax/commit/7273b80e7fd12f7b87749758f97b60d6862edf88

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

    from djpjax import pjax_block

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

Similarly, Django-PJAX-Blocks can automatically select a template to use when responding to
PJAX requests, according to the container name sent with the request.

Simply omit the initial ``template`` argument when decorating your view with
``pjax_template``, and Django-PJAX-Blocks will "pjaxify" your response's normal template_name
variable::

    from djpjax import pjax_template

    @pjax_template()
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)

By default, Django-PJAX-Blocks will insert "-pjax:<container_name>" before the
file extension of your template name. In this case, if your PJAX container were
specified with "#blog_post" as in the previous examples, Django-PJAX-Blocks
would set the template_name attribute of the TemplateResponse to
``("template-pjax:blog_post.html", "template.html")``.

If you want a single template for all PJAX requests for a single view, pass the
function ``djpjax.utils.pjaxify_template_var`` as the first argument::

    from djpjax import pjax_template
    from djpjax.utils import pjaxify_template_var

    @pjax_template(pjaxify_template_var)
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)

In this example, the TemplateResponse's ``template_name`` attribute will be set
to ("template-pjax.html", "template.html").


Customising Django-PJAX-Blocks's automatic block/template selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    from djpjax import pjax_block
    from djpjax.utils import pjax_container_from_request

    container_block_map = {
        'book_metadata': 'product_detail',
        'cart_preview': 'shopping_cart',
    }

    def block_name_fn(request):

        # One of several utility functions found in Django-PJAX-Blocks.utils
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

    from djpjax import pjax_template
    from djpjax.utils import transform_template_var
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


Using django-pjax-blocks with third-party views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you're using a Django app which defines its own views, you can't easily
decorate them as you would views you write yourself.

In these cases, you can apply django-pjax-blocks' decorators to URLs matching
particular regular expressions, via the included middleware.

To enable the middleware, add this line to the end of ``MIDDLEWARE_CLASSES``
in your settings.py::

    "djpjax.middleware.DjangoPJAXMiddleware",

Configure the middleware using the the ``DJPJAX_DECORATED_URLS`` setting. This
should be a sequence of pairs, with the first element of each pair a regular
expression matching the URLs you want decorated, and the second a tuple
containing the name of the decorator you want to use and a dict of keyword
arguments to construct it with.

For example, the following configuration will return the contents of the block
"product_info", with the value of the context variable "product_name" as the
title::

    DJPJAX_DECORATED_URLS = (
        ('^/shop/product/, ('pjax_block', {'block': 'product_info',
                                           'title_variable': 'product_name'})),
    )

That configuration is equivalent to decorating a view mounted at /shop/product/
with ``@pjax_block("product_info", title_variable="product_name)``.


Considerations
==============

Any performance benefits are strictly client-side using this package;
performance on the server side will be strictly equal to or worse than simply
rendering the full template at this stage, since the full template is actually
rendered with the irrelevant parts discarded. This may change in the future.

This package doesn't support Django's class-based views, because the author
doesn't use them much; this will change in the future and contributions in this
area are welcome.


Testing
=======

Tests are run using nosetests. To install::

    pip install nose

And to run the tests::

    nosetests tests.py
