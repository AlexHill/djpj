Django-PJAX-Blocks
==================

This is a Django helper for `defunkt's jquery-pjax`__, which allows you to
specify a template block to be served to PJAX requests for each view.

Django-PJAX-Blocks is adapted from Jacob Kaplan-Moss' `Django-PJAX`__. Use
Django-PJAX if you want to serve PJAX content from separate templates, or if
you want your PJAX responses to inherit from a separate base template.

What's PJAX?
------------

__ https://github.com/defunkt/jquery-pjax

__ https://github.com/jacobian/django-pjax

PJAX is essentially AHAH__ ("Asynchronous HTML and HTTP"), except with real
permalinks and a working back button. It lets you load just a portion of a
page (so things are faster) while still maintaining the usability of real
links.

__ http://www.xfront.com/microformats/AHAH.html

A demo makes more sense, so `check out the one defunkt put together`__

__ http://pjax.heroku.com/

Usage
=====

First, read about `how to use jQuery-PJAX`__ and pick one of the techniques there.

__ https://github.com/defunkt/jquery-pjax

Next, make sure the views you're PJAXing are using TemplateResponse__. You
can't use Django-PJAX-Blocks with a normal ``HttpResponse``; only ``TemplateResponse``.

Now decorate your views with ``pjax_block`` to specify the name of a single
block in your template to return to PJAX requests.

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
-------------------------------------------

A nice feature of the PJAX library is that it correctly updates the page title
when new content is loaded. It achieves this by looking for a ``<title>`` tag
in the HTML response. Of course, it's unlikely that your template's ``<title>``
tag is going to be inside the block that you choose to return - if it is, you
should probably rethink the way you're using PJAX!

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

Automatic block selection
-------------------------

In PJAX terms, the "container" is the DOM element whose contents are to be
replaced by the HTML fragment you return from your view. When you enable PJAX
for your links or forms, `you specify the container as a CSS selector`__. That
CSS selector is passed to your server with every PJAX request.
Django-PJAX-Blocks can use that information to automatically select a template
block to return.

__ https://github.com/defunkt/jquery-pjax#usage

Before you can do this, three things have to be true:

* You need to be using a relatively recent version of the jQuery PJAX library.
`This required feature was added in April 2012`__, so you probably are already.
* The container must be specified with a simple CSS ID selector, e.g. ``#main_content``.
* Your block names must be identical to their containers' IDs.

__ https://github.com/defunkt/jquery-pjax/commit/7273b80e7fd12f7b87749758f97b60d6862edf88

To demonstrate, this means your templates should look like this::

    ...

    <article id="blog_post">
    {% block blog_post %}
    ...
    {% endblock %}
    </article>

    ...


So, with your templates set up and your PJAX version up-to-date, how do you
make your views automatically select the right template block? Just omit the
initial ``block`` argument when decorating your views with ``pjax_block``::

    from djpjax import pjax_block

    @pjax_block(title_variable="post_title")
    def my_view(request)
        context = {"post_title": "My First Blog Post", ...}
        return TemplateResponse(request, "template.html", context)


Block name discovery precedence
-------------------------------

``pjax_block`` will look for a template block name in three places: first, it
will check its first argument, ``block``. If omitted, it will look for the
HTTP header ``X-PJAX-Container``, which is sent with each PJAX request. If
that can't be found, it will look for an HTTP GET parameter titled ``_pjax``.

If no block name can be found, if a block with the given name doesn't exist,
or if a CSS selector other than a simple ``#<id>`` selector is found in the
request when no block name has been passed to ``pjax_block``, an exception
will be raised.


Testing
=======

Tests are run using nosetests. To install::

    pip install nose

And to run the tests::

	nosetests tests.py