
A wiki is made up of pages that _link_ to each other, the same way normal web
pages also link to each other. However, linking between pages inside your wiki
(_a.k.a._ "_wikilinks_") is made a lot simpler.


## Wikilink Syntax

You can always create a normal link to a page's URL, using, say, the Markdown
syntax for hyperlinks (if you're using Markdown in your wiki... see
[[Formatting]]), but it's easier to use the wikilink syntax, which was designed
to be quicker to write. It uses double square brackets surrounding the page's
title, like so: `\[[Target Page]]`.

This syntax supports a few variants and options, which you can see in the
following table:

| Link name     | Description         | Syntax          |
| ------------- | ------------------- | --------------- |
| Relative page link | A link to a wiki page in the same folder and endpoint as the current one. | `\[[Winged Monkeys]]`<br/>&nbsp;<br/>`\[[Villains/Winged Monkeys]]` |
| Absolute page link | A link to a wiki page in the same endpoint as the current one. | `\[[/Winged Monkeys]]`<br/>&nbsp;<br/>`\[[/Villains/Winged Monkeys]]` |
| Relative endpoint/page link | A link to a wiki page in a different endpoint, but with the same relative path. | `\[[refs:Winged Monkeys]]`<br/>&nbsp;<br/>`\[[refs:Villains/Winged Monkeys]]` |
| Absolute endpoint/page link | A link to a fully-specified wiki page. | `\[[refs:/Winged Monkeys]]`<br/>&nbsp;<br/>`\[[refs:/Villains/Winged Monkeys]]` |
| Piped link    | A link to a wiki page, but with a custom text. | `\[[a link|Winged Monkeys]]` |
| Header link   | A link to a specified section in a wiki page. | `\[[Winged Monkeys#golden-cap]]` |
| Child page link | A link to a "_child page_" of the current one.  | `\[[./Winged Monkeys]]` |
| Parent page link | A link to a "_parent page_" of the current one.  | `\[[../Cities]]` |


## Endpoints

An "_endpoint_" in Wikked is a special place where you can put special pages.
The bulk of your content is going to be outside of any such endpoints, but some
pages like [[Categories]] are going to be at a given endpoint.

Endpoints are also useful for either having different "views" on a page (like
a "discussion" page to leave comments _about_ the page), or to create
a different namespace for different things, without running into page name
clashes.

On disk, while a page is just stored in the wiki's root folder (or a subfolder
of it), pages at, say, the `refs` endpoint, will be found in the `_meta/refs/`
folder.


## Relative and Absolute Wikilinks

Relative wikilinks are those that don't have a "slash" character (`/`) at the
beginning of the link. So `\[[Quadrants/Quadling Country]]` is a relative link,
whereas `\[[/Oz/Quadrants/Quadling Country]]` is an absolute link.

There are rules to relative wikilinks which are simple once you know that it
maps to the files and folders on disk:

- Absolute links are "anchored" in the current endpoint's root folder.
- Relative links are "anchored" in the current page's folder.

The term "current" means "taken from the page that contains the link we're
talking about".

### Absolute Wikilinks

There's not much to say about absolute wikilinks since, by definition, they
specify the entire path to the page, so Wikked doesn't do anything.

Of note, if you want to fully specify the path to a page in the main part of the
wiki (_i.e._ not at any endpoint), you can use an "empty endpoint" like so:
`\[[:/Villains/Winged Monkeys]]`.

### Relative Wikilinks

Although the rules for relative wikilinks are simple, they are very powerful and
a few examples are in order:

| Source endpoint | Source path        | Link           | Where it leads you |
| --------------- | ------------------ | -------------- | ------------------ |
|                 | `/Villains`        | `Witches`      | `/Witches`         |
|                 | `/Villains`        | `./Winged Monkeys` | `/Villains/Winged Monkeys` |
|                 | `/Villains/Winged Monkeys` | `/Fighting Trees` | `/Villains/Fighting Trees` |
|                 | `/Villains/Winged Monkeys` | `../Cities` | `/Cities` |
|                 | `/Villains/Winged Monkeys` | `refs:Winged Monkeys` | `refs:/Villains/Winged Monkeys` |
| `refs:`         | `/Villains/Winged Monkeys` | `Fighting Trees` | `refs:/Villains/Fighting Trees` |
| `refs:`         | `/Villains/Winged Monkeys` | `:Winged Monkeys` | `/Villains/Fighting Trees` |

Of special note:

- `./` is a short-hand for `<name of current page>/`.
- `../` gets you "up one folder".
