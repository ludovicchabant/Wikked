
In Wikked, "_page metadata_" is information _about_ a page. It may or may not be
visible to a reader of that page, but it does affect what Wikked can do with it.


## Syntax

To assign metadata to a page, use `{%raw%}{{name: value}}{%endraw%}`. For
instance:

    {%raw%}
    {{category: Witches}}
    {%endraw%}

You may need to assign a long value, like the summary of the page, which you may
not want to write all in one single line. In that case, you can use multiple
lines, but you need to put the closing double curly braces by themselves on the
last line:

    {%raw%}
    {{summary: This page is about winged monkeys, who serve
        the wicked witch of the west. They're not very bright
        but they are extremely loyal.
    }}
    {%endraw%}

> Note that the extra line to get to the closing braces won't be included
> in the metadata. If you want the metadata value to end with an empty line,
> you'll need to add one, effectively leaving an empty line before the closing
> braces.

Finally, you can also set a metadata without any value if the point is just to
metaphorically flip a switch on the page. Just leave the value empty:

    {%raw%}
    {{is_villain: }}
    {%endraw%}

The syntax for metadata is also used for [[Page Includes]] and [[Page Queries]].


## Well-Know Metadata

Although most metadata you'll use will be for you only, some of it is used to
tell Wikked to do something special.

* `category`: Adds the current page to the given category. You can specify this
  metadata multiple times to make the page part of multiple categories. Wikked
  will show the categories of a page at the bottom.

* `notitle`: If specified, Wikked won't show the title of this page. This
  lets you use a banner graphic or some other way to present the page to
  a visitor. This metadata doesn't need any value.

* `redirect`: Redirects to another page. The link resolution rules apply to the
  redirect target (see [[Linking]]).

* `readers`: Specifies the users who can read this page. When not present, the
  default readers for the wiki will be able to read the page. See
  [[Configuration]].

* `writers`: Similar to the previous metadata, but for the ability to edit
  a page.

