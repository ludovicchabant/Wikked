import os
import os.path
from setuptools import setup, find_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fp:
        return fp.read()


install_requires = [
    'Flask>=0.12.2',
    'Flask-Bcrypt>=0.7.1',
    'Flask-Login>=0.2.10',
    'Jinja2>=2.10',
    'Markdown>=3',
    'Pygments>=2.2.0',
    'SQLAlchemy>=1.2.0',
    'Whoosh>=2.7.4',
    'colorama>=0.3.9',
    'python-hglib>=1.8',
    'repoze.lru>=0.6'
]
tests_require = [
    'invoke>=0.22.0'
    'pytest>=3.3.1'
]


setup(
        name='Wikked',
        description=("A wiki engine entirely managed with text files "
                     "stored in a revision control system."),
        author='Ludovic Chabant',
        author_email='ludovic@chabant.com',
        url="https://github.com/ludovicchabant/Wikked",
        license="Apache 2.0",
        keywords="wiki mercurial hg git",
        packages=find_packages(exclude=["monkeys", "tests"]),
        setup_requires=['setuptools_scm'],
        use_scm_version={
            'write_to': 'wikked/__version__.py'},
        install_requires=install_requires,
        tests_require=tests_require,
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
