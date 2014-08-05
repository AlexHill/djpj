Overview of DjPj (formerly Django-PJAX-Blocks)
==============================================

DjPj is a simple, flexible way to add PJAX support to your Django project and
deliver a faster browsing experience to users of your website.

If you don't know what PJAX is, `read about how it works`__ below. In a
nutshell, it makes navigating between pages on your website faster by loading
only the part of the page that needs to change, rather than the whole thing.
It's is a well-established technique; if you're reading this on GitHub, you
probably loaded this content via PJAX.

__ #how-does-pjax-work

In a nutshell, your DjPj-enabled website will respond to PJAX requests with
the contents of a single template block of your choosing. It requires no
changes to your views, which means it's easy to add PJAX support to
third-party Django apps.

Getting started
===============

PJAX requires cooperation between your front end (the Javascript that runs in
your visitors' web browsers) and your Django back end.

1. Set up the front end with jquery-pjax
----------------------------------------

The front end is handled by the jquery-pjax library, so first of all, read about
`how to use jQuery-PJAX`__ and pick one of the techniques there.

__ https://github.com/defunkt/jquery-pjax

2. Install DjPj on your server
------------------------------

First, make sure the views you're PJAXing return TemplateResponse__. DjPj works
by changing the way your templates are rendered, so it won't work with a
pre-rendered ``HttpResponse``.

__ https://docs.djangoproject.com/en/dev/ref/template-response/

Install DjPj from PyPI::

    > pip install djpj

3. Start using PJAX - basic usage examples
------------------------------------------

Imagine you have a template, ``blog_post.html`` that looks like this::

    <head>
        <title>{{ blog_post_title }}</title>
    </head>

    ...

    <div id="blog_post">
    {% block blog_post %}
        ...
    {% endblock %}
    </article>

Respond to PJAX requests to ``blog_post_view`` with the contents of the
"blog_post" template block::

    @pjax_block("blog_post")
    def blog_post_view(request, ...)
        ...
        return TemplateResponse(request, "blog_post.html", context)

If you want PJAX to correctly update the title of your page, include a
``title_block`` or ``title_variable`` argument to ``pjax_block``::

    @pjax_block("blog_post", title_variable="blog_post_title")
    def blog_post_view(request, ...)
        ...

The "container" in PJAX parlance is the HTML element the contains the content
you want to swap out. In the example above, the name of the block is the same
as the id of the container element - they're both "blog_post". In these cases
you can just omit the first argument entirely, and DjPj will look for a block
whose name is the same as the container's id::

    @pjax_block(title_variable-"blog_post_title")
    def blog_post_view(request, ...)
        ...

Use DjPj's middleware to enable PJAX without modifying your views
-----------------------------------------------------------------

If your site uses third-party views that you can't modify - for example, views
defined by an ecommerce or CMS package - you can use DjPj's middleware instead
of decorating views directly. This can also be handy when you have a number of
views that you want to PJAXify which all share a common URL pattern.

Here's what it looks like::

    # DjangoPJAXMiddleware should appear last in MIDDLEWARE_CLASSES
    MIDDLEWARE_CLASSES = (
        ...,
        "djpj.middleware.DjangoPJAXMiddleware",
    )

    DJPJ_PJAX_URLS = (
        ('^/blog/', '@pjax_block("blog_post", title_variable="blog_post_title")'),
    )

Each entry in ``DJPJ_PJAX_URLS`` is a 2-tuple with the first element a regular
expression matching the URLs you want to PJAXify, and the second a string
containing Python code defining the decorator, just as it would be done in
views.py.

Using a different template for PJAX requests
--------------------------------------------

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

Customising the behaviour of DjPj
=================================

You can customise how DjPj selects blocks and templates by supplying your own
functions to the ``pjax_block`` and ``pjax_template`` decorators. `Read more
about that on GitHub.`__

__ https://github.com/AlexHill/django-pjax-blocks/blob/master/DOCS.rst


How does PJAX work?
===================

Normally, when you click a link, your browser has to set up everything from
scratch: HTML has to be parsed, scripts have to be compiled and executed,
stylesheets interpreted and applied. It's a lot of work, and when you're
browsing between different pages on the same website, much of this work is
duplicated. It's like heating up a new skillet for every pancake.

When a user clicks a link on your PJAX-enabled website, the server sends only
the content that needs to change to display the new page. The fresh dollop of
content drops into place in your page, and the browser doesn't have to do all
the work associated with a full page load. To complete the trick, we manipulate
the browser history to make the back and forward buttons work normally.


Acknowledgements
================

DjPj relies on defunkt's `jquery-pjax`__ – the canonical
client-side PJAX library and the same one used by GitHub.

__ https://github.com/defunkt/jquery-pjax

DjPj was originally adapted from Jacob Kaplan-Moss' `Django-PJAX`__.

__ https://github.com/jacobian/django-pjax

Python and Django compatibility
===============================

This package is tested in Django 1.4+ and Python 2.6, 2.7, 3.3+ and PyPy.

Testing
=======

Tests are run using nose. To install::

    pip install nose

And to run the tests::

    nosetests tests.py
