
                        .__ __    __              .___
                __  _  _|__|  | _|  | __ ____   __| _/
                \ \/ \/ /  |  |/ /  |/ // __ \ / __ | 
                 \     /|  |    <|    <\  ___// /_/ | 
                  \/\_/ |__|__|_ \__|_ \\___  >____ | 
                                \/    \/    \/     \/ 


Wikked is a wiki engine entirely managed with text files stored in a revision
control system like Mercurial or Git.

The documentation is available on the [official website][1].

[1]: http://bolt80.com/wikked/


## Quickstart

You need Python 3.4 or later. Then, you install Wikked the usual way:

    pip install wikked

Create a new wiki:

    wk init mywiki

Run it:

    cd mywiki
    wk runserver

Navigate to `http://localhost:5000`. If you see the default main page, every
works fine! Otherwise, something went wrong.

