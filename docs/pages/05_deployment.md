---
title: Deployment
icon: server
---

Wikked runs by default with an "easy" configuration, _i.e._ something that will
"just work" when you play around locally. In this default setup, it uses
[SQLite][] for the cache, and [Whoosh][] for the full-text search, all running
in Flask's built-in server.

 [whoosh]: https://bitbucket.org/mchaput/whoosh/wiki/Home
 [sqlite]: https://sqlite.org/

This technology stack works very well for running your wiki locally, or for 
private websites. It has some limitations, however:

* The `wk runserver` command runs the Flask development server, which you
  [shouldn't use in production][flaskdeploy]. You'll probably need to run Wikked
  inside a proper server instead.
* When a page has been edited, Wikked will immediately evaluate and reformat all
  pages that have a dependency on it. You probably want to have this done in the
  background instead.

In this chapter we'll therefore look at deployment options, and follow-up with
some more advanced configurations for those with special requirements.

 [flaskdeploy]: http://flask.pocoo.org/docs/deploying/
    

## Apache and WSGI

A simple way to run Wikked on a production server is to use [Apache][] with
[`mod_wsgi`][wsgi]. For a proper introduction to the matter, you can see
[Flask's documentation on the subject][flask_wsgi]. Otherwise, you can probably
reuse the following examples.

 [apache]: https://httpd.apache.org/
 [wsgi]: http://code.google.com/p/modwsgi/
 [flask_wsgi]: http://flask.pocoo.org/docs/deploying/mod_wsgi/

The first thing is to create a `.wsgi` file somewhere on your server. You only
need to create the Wikked WSGI app in it, and optionally activate your
`virtualenv` if you're using that:

    # Activate your virtualenv
    activate_this = '/path/to/venv/bin/activate_this.py'
    execfile(activate_this, dict(__file__=activate_this))

    # Get the Wikked WSGI app
    from wikked.wsgiutil import get_wsgi_app
    application = get_wsgi_app('/path/to/your/wiki/root')

The second thing to do is to add a new virtual host to your Apache
configuration. The [Flask documentation][flask_wsgi] shows an example that you
should be able to use directly, although you'll also need to tell Apache where
to serve some static files: Wikked's static files (Javascript, CSS, icons,
etc.), and your own wiki's files (your pictures and other attachments). This
means your Apache configuration will look like this in the end:

    <VirtualHost *:80>
        ServerName yourwikidomain.com

        WSGIDaemonProcess yourwiki user=user1 group=group1 threads=5
        WSGIScriptAlias / /path/to/your/wsgi/file.wsgi

        DocumentRoot /path/to/your/wiki/_files
        Alias /static/ /path/to/wikked/static/

        <Directory /path/to/your/wiki>
            WSGIProcessGroup yourwiki
            WSGIApplicationGroup %{GLOBAL}
            Order deny,allow
            Allow from all
        </Directory>
    </VirtualHost>

> You will have to create the `_files` directory in your wiki before
> reloading Apache, otherwise it may complain about it.
> 
> Also, the path to Wikked's `static` directory is going to point directly into
> your installed Wikked package. So if you installed it with `virtualenv`, it
> would be something like:
> `/path/to/your/wiki/venv/lib/python/site-packages/wikked/static`.


## Background updates

The second thing to do is to enable background wiki updates. Good news: they're
already enabled if you used the `get_wsgi_app` function from the previous
section (you can disable it by passing `async_update=False` if you really need
to).

> If you want to use background updates locally, you can do `wk runserver
> --usetasks`.

However, you'll still need to run a separate process that, well, runs those
updates in the background. To do this:

    cd /path/to/my/wiki
    wk runtasks

> The background task handling is done with [Celery][]. By default, Wikked will
> use the [SQLAlchemy transport][celerysqlite].

 [celery]: http://www.celeryproject.org/
 [celerysqlite]: http://docs.celeryproject.org/en/latest/getting-started/brokers/sqlalchemy.html


## Backend options

**This is for advanced use only**

If you want to use a different storage than SQLite, set the `database_url`
setting in your `wikirc` to an [SQLAlchemy-supported database URL][SQLAlchemy].
For instance, if you're using MySQL with `pymsql` installed:

    [wiki]
    database_url=mysql+pymysql://username:password123@localhost/db_name

 [sqlalchemy]: http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#database-urls

> Note that you'll have to install the appropriate SQL layer. For instance: `pip
> install pymsql`. You will also obviously need to setup and configure your SQL
> server.


If Whoosh is also not suited to your needs, you can use [Elastic
Search][elastic] instead:

    [wiki]
    indexer=elastic

You'll obviously have to install and run Elastic Search.

 [elastic]: http://www.elasticsearch.org/

