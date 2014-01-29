
def get_wsgi_app(wiki_root):
    import os
    os.chdir(wiki_root)

    from wikked.web import app
    from wikked.wiki import WikiParameters
    app.wiki_params = WikiParameters(wiki_root)

    return app

