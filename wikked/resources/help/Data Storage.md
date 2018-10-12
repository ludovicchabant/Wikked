
Wikked’s data is entirely stored in text files on disk. All you ever need, or
should really care about, are those text files, and the source control
repository which contains their history. Wikked may create some other files
–- cache files, indices, etc. –- but they can always be safely deleted and
re-created.

Inside the wiki root directory, you will find:

- Page files.
- Source control files.
- Configuration files.
- Cache files.


## Page Files

If you look at your wiki, you should see a file called `Main page.md`, along
with maybe other such text files that you added yourself, and sub-folders that 
contain more of them.

Each page's text is stored in a file whose name is the name of the page -- like
that `Main page.md`. That name is important, since that's what you'll use for
linking to it, and what will show up in that page's URL. A page named `Toto.md`
would be available at the URL `/read/Toto`. See [[Creating Pages]] for more
information.


## Source Control Files

Page files are also stored in a "source control management" tool (or SCM), which
is what tracks their various versions as they are edited. The SCM usually stores
files in a hidden sub-folder, like `.hg` or `.git` for [Mercurial] and [Git]
respectively.

There might also be a few other SCM files, like `.hgignore` or `.gitignore`, or
any number of things Wikked, an SCM client application, or yourself created for
a reason.

Don't touch those files, as they're important (they store your pages' history).
You can learn more about these files, and about the SCM you picked when you
created your wiki, by using the wonders of the internet.


## Configuration Files

Wikked can be configured with some configuration files like the `.wikirc` file.
There are no such files originally when you create a new wiki, but they can be
created later to customize or add something. See [[Configuration]] for more
information.


## Cache Files

There should be a `.wiki` folder in the wiki root directory. This folder is
a cache, and can generally be safely deleted and re-created with the `wk reset`
command (see [[Command Line Interface]]). You may however have some local
configuration file(s) in there (see [[Configuration]]), so watch out before
deleting that folder.





[wikked]: https://bolt80.com/wikked/
[mercurial]: https://www.mercurial-scm.org/
[git]: https://git-scm.com/
