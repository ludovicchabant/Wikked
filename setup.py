import os
import os.path
from setuptools import setup, find_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fp:
        return fp.read()


setup(
        name='Wikked',
        version='0.1.0.3',
        description=("A wiki engine entirely managed with text files "
            "stored in a revision control system."),
        author='Ludovic Chabant',
        author_email='ludovic@chabant.com',
        url="http://bolt80.com/wikked/",
        license="Apache 2.0",
        keywords="wiki mercurial hg git",
        packages=find_packages(exclude=["tests"]),
        install_requires=[
            'Flask>=0.10',
            'Flask-Login>=0.1.3',
            'Flask-SQLAlchemy>=1.0',
            'Flask-Script>=0.5.1',
            'Jinja2>=2.6',
            'Markdown>=2.2.1',
            'PyYAML>=3.10',
            'Pygments>=1.5',
            'SQLAlchemy>=0.8.3',
            'Werkzeug>=0.8.3',
            'Whoosh>=2.4.1',
            'argparse>=1.2.1',
            'pybars>=0.0.4',
            'python-hglib',
            'twill>=0.9',
            'wsgiref>=0.1.2'
            ],
        scripts=['wk.py'],
        include_package_data=True,
        package_data={
            'wikked': [
                'resources/*',
                'templates/*.html',
                'static/css/wikked.min.css',
                'static/img/*.png',
                'static/js/require.js',
                'static/js/wikked.min.js',
                'static/js/pagedown/*.js'
                ]
            },
        zip_safe=False,
        classifiers=[
                'Development Status :: 3 - Alpha',
                'License :: OSI Approved :: Apache Software License',
                'Environment :: Console',
                'Operating System :: MacOS :: MacOS X',
                'Operating System :: Unix',
                'Operating System :: POSIX',
                'Operating System :: Microsoft :: Windows',
                'Programming Language :: Python',
            ],
        entry_points={
                'console_scripts': [
                    'wk = wk:main'
                ]
            },
        )

