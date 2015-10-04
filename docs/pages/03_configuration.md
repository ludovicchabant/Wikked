---
title: Configuration
icon: cog
---

Wikked can be configured with a few files:

* `.wikirc`: this file, located at the root of your wiki, can be submitted into
  revision control, so that various clones of the wiki have the same options
  where it makes sense.

* `.wiki/wikirc`: some options, however, don't have to be the same depending on
  where you run the wiki. This file is contained in the ignored-by-default
  `.wiki` folder, and as such is meant to store options valid only for a local
  installation.

* `.wiki/app.cfg`: Wikked runs on top of [Flask][]. This file, if it exists,
  will be passed on to Flask for more advanced configuration scenarios. See the
  [Flask configuration documentation][1] for more information.
  
 [flask]: http://flask.pocoo.org/
 [1]: http://flask.pocoo.org/docs/0.10/config/


The `wikirc` file is meant to be written with an INI-style format:

```
[section1]
foo=bar
something=some other value

[section2]
blah=whatever
```


## Main options

The main Wikked options should be defined in a `[wiki]` section. Here are the
supported options:

* `main_page` (defaults to `Main page`): the name of the page that should be
  displayed when people visit the root URL of your wiki. Page names are case
  sensitive so watch out for the capitalization. 

* `default_extension` (defaults to `md`): the file extension (and therefore
  formatting engine) to use by default when creating a new page. The default
  values is `md` for [Markdown][].

* `templates_dir` (defaults to `Templates`): by default, the `include` statement
  (see the [syntax page][2]) will first look into a templates directory for
  a template of the given name. This is the name of that folder.

* `indexer` (defaults to `whoosh`): The full-text indexer to use. Only 2 indexers are currently
  supported, `whoosh` (for [Whoosh][]) and `elastic` (for [Elastic Search][elastic]).

* `database` (defaults to `sql`): The database system to use for the cache.
  Wikked currently only supports SQL, but see the next option below.

* `database_url` (defaults to `sqlite:///%(root)s/.wiki/wiki.db`): the URL to
  pass to [SQLAlchemy][] for connecting to the database. As you can see, the
  default value will read or create an [SQLite][] file in the `.wiki` folder. If
  you want to use a proper SQL server you can specify its URL and login
  information instead. See the [SQLAlchemy connection string format][3] for more
  information.

 [2]: {{pcurl('syntax')}}
 [3]: http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls 
 [SQLite]: http://sqlite.org
 [SQLAlchemy]: http://sqlalchemy.org
 [whoosh]: https://bitbucket.org/mchaput/whoosh/wiki/Home
 [elastic]: http://www.elasticsearch.org/
 [markdown]: http://daringfireball.net/projects/markdown/


## Permissions

The `wikirc` file can also be used to define user permissions. This is done with
the `[users]` section:

    [users]
    dorothy=PASSWORD_HASH

The `PASSWORD_HASH` is, well, a password hash. You can generate one by using the
`wk newuser` command:

    $ wkdev newuser dorothy
    Password: ********
    dorothy = $2a$12$7FR949jt9zq5iNwY5WAZAOzD7pK3P0f/NnrKHAys17HT1Omuk2Asu

    (copy this into your .wikirc file)

Once you have some users defined, you can give them some permissions, using the
`[permissions]` section. Supported settings are:

* `readers`: users able to read the wiki.
* `writers`: users able to edit the wiki.

Multiple usernames must be separated by a comma. You can also use `*` for "all
users", and `anonymous` for unauthenticated visitors.

The following example shows a wiki only accessible to registered users, and that
can only be edited by `dorothy` and `toto`:

    [permissions]
    readers = *
    writers = dorothy,toto

Those settings can also be overriden at the page level using the `readers` and
`writers` metadata. So you can still have a public landing page for the
previously mentioned private wiki by adding this to `Main page.md`:

    {%raw%}
    {{readers: *,anonymous}}
    {%endraw%}


## Ignored files

The optional `ignore` section lets you define files or folders for Wikked to
ignore (_i.e._ files that are not pages, or folder that don't contain pages).

Each item in this section should be `name = pattern`, where `name` is irrelevant,
and `pattern` is a glob-like pattern:

    [ignore]
    venv = venv
    temp = *~
    temp2 = *.swp

This will ignore a `venv` folder or file at the root, or any file or folder
anywhere that ends with `~` or `.swp`.


