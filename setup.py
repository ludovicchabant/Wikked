import os
import os.path
from setuptools import setup, find_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fp:
        return fp.read()


setup(
        name='Wikked',
        description=("A wiki engine entirely managed with text files "
                     "stored in a revision control system."),
        author='Ludovic Chabant',
        author_email='ludovic@chabant.com',
        url="https://github.com/ludovicchabant/Wikked",
        license="Apache 2.0",
        keywords="wiki mercurial hg git",
        packages=find_packages(exclude=["tests"]),
        setup_requires=['setuptools_scm'],
        use_scm_version={
            'write_to': 'wikked/__version__.py'},
        install_requires=[
            'Flask==0.10.1',
            'Flask-Bcrypt==0.5.2',
            'Flask-Login==0.2.10',
            'Flask-Script==0.5.1',
            'Jinja2==2.7.2',
            'Markdown==2.2.1',
            'Pygments==1.6',
            'SQLAlchemy==0.9.3',
            'Whoosh==2.5.5',
            'colorama==0.2.7',
            'py-bcrypt==0.4',
            'pysqlite==2.6.3',
            'pytest==2.5.2',
            'repoze.lru==0.6',
            'python-hglib'],
        include_package_data=True,
        zip_safe=False,
        classifiers=[
            'Development Status :: 3 - Alpha',
            'License :: OSI Approved :: Apache Software License',
            'Environment :: Console',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: Unix',
            'Operating System :: POSIX',
            'Operating System :: Microsoft :: Windows',
            'Programming Language :: Python'],
        entry_points={
                'console_scripts': [
                    'wk = wikked.witch:real_main']
                },
        )

