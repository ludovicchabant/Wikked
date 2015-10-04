---
title: Wikked
icon: home
---

**Wikked** is a [wiki][] engine that stores its data in plain text files using
a common revision control system like [Mercurial][] or [Git][]. It's mostly
suitable for an individual, family, or small team.

The source code is available on [Github][] and [BitBucket][].

## Quickstart

Install **Wikked** using Python 3.4 or later and `pip`:

    pip install wikked

Let's create a new wiki:

    wk init mywiki

This will create a new directory called `mywiki` with some basic files in it. It
will also initialize a [Mercurial][] repository in it.

Now let's get in there and run it:

    cd mywiki
    wk runserver

You should now be able to open your favorite web browser and go to
`localhost:5000`. If you see the main page of your wiki, congratulations!
Otherwise, something went wrong. If you found a bug make sure to [file a
report][1] about it.


[wiki]: https://en.wikipedia.org/wiki/Wiki
[git]: http://git-scm.com/
[mercurial]: http://mercurial.selenic.com/
[github]: https://github.com/ludovicchabant/Wikked
[bitbucket]: https://bitbucket.org/ludovicchabant/wikked
[1]: https://github.com/ludovicchabant/Wikked/issues


