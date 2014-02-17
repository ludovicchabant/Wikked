
                        .__ __    __              .___
                __  _  _|__|  | _|  | __ ____   __| _/
                \ \/ \/ /  |  |/ /  |/ // __ \ / __ | 
                 \     /|  |    <|    <\  ___// /_/ | 
                  \/\_/ |__|__|_ \__|_ \\___  >____ | 
                                \/    \/    \/     \/ 


Wikked is a wiki engine entirely managed with text files stored in a revision
control system like Mercurial or Git.

It's in early alpha, and will probably not work at all except on my machine. If
you still want to try it, great! Please note that:

* On Mercurial is supported at the moment. Git support is planned.
* The command-line interface is temporary and incomplete.
* Lots of incomplete or buggy stuff. Like I said it's alpha!
* Please report any bug on [Github][gh].


## Installation

Install Wikked the usual way:

    pip install wikked

Or, if you're using `easy_install`:

    easy_install wikked

You can also install it from the source, which you can find on [BitBucket][bb]
or [Github][gh].

[bb]: https://bitbucket.org/ludovicchabant/wikked
[gh]: https://github.com/ludovicchabant/Wikked


## Setup

Until Wikked is feature complete with its command-line utility, there's a few
steps needed to setup a new wiki:

1. Create a new Mercurial repository: `hg init mywiki`
2. Go there: `cd mywiki`
3. Create a `Main Page.md` text file, put some text in it.
4. Run `wk reset` to initialize the wiki.
5. Run `wk runserver` and navigate to `localhost:5000`.

If you're using an existing repository instead in step 1, make sure that you add
the `.wiki` folder to your `.hgignore`, and that's where Wikked will cache some
stuff (which you don't want committed or showing up in `hg status`).


## Wiki Configuration

You can configure your wiki with a `.wikirc` file in the root of your website.

Optionally, you can define a `.wiki/wikirc` file, and any settings in there will
be merged with the `.wikirc`. The difference is that the one at the root is
typically committed to source control, whereas the one in the `.wiki` folder
will only be local to the current repository clone, so that makes it possible to
have local overrides.

The configuration is written in INI-style:

    [section]
    name = value
    other = whatever

    [other_section]
    name = value


### `wiki` Section

All the following configuration settings should be in a `[wiki]` section:

* `default_extension` (defaults to `md`): the default extension to use when
  creating new pages.

* `main_page` (defaults to `Main Page`): the name of the page to display by
  default in the browser.

* `templates_dir` (defaults to `Templates`): the directory to search for first
  when including pages only by name (as opposed to by fully qualified path).


### `ignore` Section

This section defines more files or folders for Wikked to ignore (_i.e._ files
that are not pages, or folder that don't contain pages).

Each item in this section should be `name = pattern`, where `name` is irrelevant,
and `pattern` is a glob-like pattern:

    [ignore]
    venv = venv
    temp = *~
    temp2 = *.swp

This will ignore a `venv` folder or file at the root, or any file or folder
anywhere that ends with `~` or `.swp`.


