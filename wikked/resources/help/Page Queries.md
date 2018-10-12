
Page queries let you list pages in various ways, based on various criteria. It
uses the [[Page Metadata]] syntax.


## Basic Query Syntax

The query metadata takes the name and value of another metadata to query on
pages.  So for instance you can display a list of pages in the "_Witches_"
category like so:

    {%raw%}
    {{query: category=Witches}}
    {%endraw%}

This will print a bullet list of the matching pages' titles, with a link to
each. Of course you can match any other metadata -- not just "category".


## Formatting Options

You can customize how the list looks like by setting a number of arguments to
the query. The argument syntax is similar to that of [[Page Includes]].

Supported arguments are:

* `__header`: The text to print before the list. The default is an empty line.
* `__item`: The text to print for each matching page. It defaults to: `*
  {%raw%}\[[{{title}}|{{url}}]]{%endraw%}` (which means, as per Markdown
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
        |__item=* \[[{{title}}|{{url}}]]: {{description}}

    }}
    {%endraw%}

Note the extra empty line so that each item has a line return at the end...
otherwise, they would be all printed on the same line!

When a query parameter gets too complicated, you can store it in a separate
metadata property, as long as that property starts with a double underscore:

    {%raw%}
    {{__queryitem: * \[[{{title}}|{{url}}]]: {{description}} }}

    {{query: category=Witches|__item=__queryitem}}
    {%endraw%}

For extra long item templates, you can use a dedicated page. For example, here's
how you use the text in `/Templates/Witches Item` as the query item template:

    {%raw%}
    {{query: category=Witches|__item=\[[/Templates/Witches Item]]}}
    {%endraw%}

