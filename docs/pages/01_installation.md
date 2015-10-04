---
title: Installation
icon: cloud-download
---

## From the package index

You need [Python 3.4][py3] or later to use Wikked. Then, the easiest way to
install it is to use `pip`:

    pip install wikked

If you want to use the very latest (and potentially broken) version:

    pip install git+ssh://git@github.com/ludovicchabant/Wikked.git#egg=Wikked

Check that you have Wikked correctly installed by running:

    wk --help

You should see Wikked's command line help.

## From source

You can also use Wikked from source. It's recommended that you use `virtualenv`
for this (see the [documentation][venv] for more info).  It would look something
like this:

    # Clone with either Mercurial or Git:
    hg clone ssh://hg@bitbucket.org/ludovicchabant/wikked
    git clone git@github.com:ludovicchabant/Wikked.git

    # Create and activate virtualenv, if you're on Bash
    virtualenv venv
    source venv/bin/activate

    # Install Wikked's requirements in venv
    pip install -r requirements.txt

    python wk.py --help

Just remember to activate your virtual environment every time you open a new
console.

[py3]: https://www.python.org/downloads/
[venv]: http://www.virtualenv.org/


