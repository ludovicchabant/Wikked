---
title: Overview
icon: book
---

Wikked's data is entirely stored in text files on disk. All you ever need, or
should really care about, are those text files, and the source control
repository which contains their history. Wikked may create some other files --
cache files, indices, etc. -- but they can always be safely deleted and
re-created.


## The wiki folder

If you look at your new wiki, you should see a file called `Main page.md`, along
with a few hidden files and directories.

* Each page's text is stored in a file whose name is the name of the page --
  like that `Main page.md`. That name is important, since that's what you'll use
  for linking to it, and what will show up in that page's URL. A page named
  `Toto.md` would be available at the URL `/read/Toto`.

* Sub-directories also map to sub-folders in page names and URLs, so a file
  located at `Villains/Flying monkeys.md` would be available at
  `/read/Villains/Flying monkeys.md`.

* There's a `.wiki` folder that was created in the wiki root. This folder is
  a cache, and can generally be safely deleted and re-created with the `wk
  reset` command. You may however have some [local configuration
  file(s)][config] in there, which we'll talk about later, so watch out before
  deleting that folder.

* There's also some source control related files in there, like a `.hg` folder
  and `.hgignore` file in the case of Mercurial. Don't touch those, they're
  important (they store your pages' history). You can learn about them using the
  wonders of the internet.

> There's nothing preventing you from using accented or non-latin characters for
> a new page name, except for characters that would be invalid for a file name.
> However, please note that most revision control systems are going to behave
> badly if you'll be working with your repository on mixed systems (_i.e._
> Windows, Mac, Linux).


## General features

Wikked implements the usual wiki concepts of being able to edit pages, look at
their history and revert to previous revisions, and of course easily link to
other pages.

Wikked also supports the ability to include a page into another page, to assign
metadata (like categories) to pages, and to query pages based on that metadata.
So for example you can display a list of all pages under the category "_Witches
of Oz_".


## Limitations

Wikked was written mainly for a small group of editors in mind. It's especially
well suited for a personal digital notebook, a private family documents
repository, or a wiki for a small team of people.

The main limitation of Wikked comes into play when you increase the number of
contributors -- *not* when you increase the number of visitors. Once the website
is cached, all requests are done against the SQL database, and search is done
through the indexer. This means you can scale quite well as long as you have the
appropriate backend (and as long as I don't write anything stupid in the code).

However, user accounts are stored in a text file, and must be added by hand by
an administrator, so it's impossible to scale this up to hundreds or thousands
of users. You could probably improve this by adding a different user account
backend, but when those users start editing pages, each edit must write to a
separate file on disk, and be committed to a source control repository, and this
will probably prove to be a bottleneck anyway at some point.

In summary: Wikked should be able to handle lots of visitors, but not too
many contributors.

## Support

If you need assistance with Wikked, [contact me directly][me] or report an issue
on the [GitHub bug tracker][bugs].

 [me]: http://ludovic.chabant.com
 [bugs]: https://github.com/ludovicchabant/Wikked/issues
 [config]: {{pcurl('configuration')}}

