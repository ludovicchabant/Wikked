from invoke import task, run


@task
def makerelease(ctx, version, local_only=False):
    if not version:
        raise Exception("You must specify a version!")

    # FoodTruck assets.
    print("Update node modules")
    run("npm install")
    print("Generating Wikked assets")
    run("gulp")

    if not local_only:
        # Tag in Mercurial, which will then be used for PyPi version.
        run("hg tag %s" % version)

        # PyPi upload.
        run("python setup.py sdist upload")
    else:
        print("Would tag repo with %s..." % version)
        print("Would upload to PyPi...")
