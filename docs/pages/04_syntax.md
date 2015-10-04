---
title: Syntax
icon: pencil
---

## Formatting

By default, Wikked will use [Markdown][] syntax, so that things like these:

    Ring around the rosie, a pocket full of *spears*! Thought you were pretty 
    foxy, didn't you? **Well!** The last to go will see the first three go 
    before her! _And your mangy little dog, too!_

...turn into this:

> Ring around the rosie, a pocket full of *spears*! Thought you were pretty 
> foxy, didn't you? **Well!** The last to go will see the first three go 
> before her! _And your mangy little dog, too!_

[markdown]: http://daringfireball.net/projects/markdown/

Page files that have a `.md` extension will be formatted using Markdown. Other
formats can be used, like Textile, by using other extensions.


## Links

Wikked uses a simple wiki link syntax:

* Links are made with double square brackets: `[[Flying monkeys]]` will link to a
  page called `Flying monkeys.md`.

* Linking respects the "current directory", _i.e._ the directory of the current
  page. Linking to `Flying monkeys` from `Villains/Wicked Witch` will lead
  you to `Villains/Flying monkeys`.

* To link using an "absolute" path, start with a slash: `[[/Villains/Flying
  monkeys]]` will work regardless of the page you're currently writing it into.
  This is for instance useful for templates.

* To link to a page in the parent directory, use `..` like so:
  `[[../Munchkins]]`.

* You can quickly link to "child" pages by using `./`. For example, if you have
  a page called `/Munchkins` that links to `[[./Lollipop Guild]]`, it will lead
  to the page `/Munchkins/Lollipop Guild`.

* To give a different display name, write it before a vertical bar: `[[click
  here|Flying monkeys]]`.


## Metadata

To assign metadata to a page, use `{%raw%}{{name: value}}{%endraw%}`. For instance:

    {%raw%}
    {{category: Witches}}
    {%endraw%}

You may need to assign a long value, like the summary of the page, which you may
not want to write all in one single line. In that case, you can use multiple
lines, but you need to put the closing double curly braces by themselves on the
last line:

    {%raw%}
    {{summary: This page is about flying monkeys, who serve
        the wicked witch of the west. They're not very bright
        but they are extremely loyal.
    }}
    {%endraw%}

> Note that the carriage return to get to the closing braces won't be included
> in the metadata. If you want the metadata value to end with a carriage return,
> you'll need to add one, effectively leaving an empty line before the closing
> braces.

Finally, you can also set a metadata without any value if the point is just to
metaphorically flip a switch on the page. Just leave the value empty:

    {%raw%}
    {{is_villain: }}
    {%endraw%}


### Well-know metadata

Although most metadata you'll use will be for you only, some of it is used to
tell Wikked to do something special.

* `category`: Adds the current page to the given category. You can specify this
  metadata multiple times to make the page part of multiple categories. The
  Wikked UI will show the categories of a page at the bottom.

* `notitle`: If specified, the Wikked UI won't show the title of this page. This
  lets you use a banner graphic or some other way to present the page to
  a visitor.

* `redirect`: Redirects to another page.

* `readers`: Specifies the users who can read this page. When not present, the
  default readers for the wiki will be able to read the page. See the
  [configuration page][1] for more information.

* `writers`: Similar to the previous metadata, but for the ability to edit
  a page.



## Includes

The metadata syntax is also used for including and querying pages. For instance,
to include the `Warning` page in another page:

    {%raw%}
    {{include: Warning}}
    {%endraw%}

You can supply a relative or absolute page name to the `include` meta. For
convenience, however, Wikked will first look in the `/Templates` folder for a
page of that name to include. If it doesn't find one, it will resolve the path
as usual.

> You can make Wikked look into a different folder than `/Templates` by changing
> the `templates_dir` option in the configuration file. See the [configuration
> documentation][1] for more information.

The `include` metadata accepts arguments. For example, the `City of Oz`
page may have this at the top:

    {%raw%}
    {{include: Warning
        |a work in progress
        |adding references
    }}
    {%endraw%}

Those arguments can then be used by the included `/Templates/Warning` page:

    {%raw%}
    WARNING! This page is {{__args[0]}}.
    You can help by {{__args[1]}}.
    {%endraw%}

This will make `City of Oz` print the following warning:

    WARNING! This page is a work in progress.
    You can help by adding references.

As you can see, arguments are passed as an array named `__args`, and this can be
inserted using double curly brackets. So {%raw%}`{{__args[0]}}`{%endraw%}
inserts the first passed argument, {%raw%}`{{__args[1]}}`{%endraw%} inserts the
second, and so on.

You can also pass arguments by name:

    {%raw%}
    {{include: Presentation
        |what=dog
        |nickname=Toto
    }}
    {%endraw%}

And use them by name in the included template:

    {%raw%}
    My {{what}} is called {{nickname}}.
    {%endraw%}

In reality, when included, a page's text will be processed through [Jinja2][]
templating so you can also use all kinds of fancy logic. For example, if you
want to support a default warning message, and an optional information message,
you can rewrite the `/Template/Warning` page like so:

    {%raw%}
    WARNING! This page is {{__args[0]|default('not ready')}}.
    {%if __args[1]%}You can help by {{__args[1]}}.{%endif%}
    {%endraw%}

For more information about what you can do, refer to the [Jinja2 templating
documentation][jinja2_tpl].

  [jinja2]: http://jinja.pocoo.org/
  [jinja2_tpl]: http://jinja.pocoo.org/docs/templates/

Pages with other pages included in them inherit the meta properties of the
included pages. You can tweak that behaviour:

* Meta properties that start with `__` (double underscore) will be "local" or
  "private" to that page, _i.e._ they won't be inherited by pages including the
  current one.
* Meta properties that start with `+` (plus sign) will only be "added" or
  "given" to pages including the current one, _i.e._ the current page won't have
  that property, but pages including it will.


## Queries

The query metadata takes the name and value of another metadata to query on
pages.  So for instance you can display a list of pages in the "_Witches_"
category like so:

    {%raw%}
    {{query: category=Witches}}
    {%endraw%}

This will print a bullet list of the matching pages' titles, with a link to
each.

You can customize how the list looks like by setting the following arguments:

* `__header`: The text to print before the list. The default is an empty line.
* `__item`: The text to print for each matching page. It defaults to: `*
  {%raw%}[[{{title}}|{{url}}]]{%endraw%}` (which means, as per Markdown
  formatting, that it will print a bulleted list of titles linking to each
  page).
* `__footer`: The text to print after the list. The default is an empty line.
* `__empty`: The text to show when no pages match the query. It defaults to a
  simple text saying that no page matched the query.

So for example, to display a description of each page next to its link, where
the description is taken from a `description` metadata on each matching page,
you would do:

    {%raw%}
    {{query: category=Witches
        |__item=* [[{{title}}|{{url}}]]: {{description}}

    }}
    {%endraw%}

Note the extra empty line so that each item has a line return at the end...
otherwise, they would be all printed on the same line!

When a query parameter gets too complicated, you can store it in a separate
metadata property, as long as that property starts with a double underscore:

    {%raw%}
    {{__queryitem: * [[{{title}}|{{url}}]]: {{description}} }}

    {{query: category=Witches|__item=__queryitem}}
    {%endraw%}

For extra long item templates, you can use a dedicated page. For example, here's
how you use the text in `/Templates/Witches Item` as the query item template:

    {%raw%}
    {{query: category=Witches|__item=[[/Templates/Witches Item]]}}
    {%endraw%}


[1]: {{pcurl('configuration')}}

