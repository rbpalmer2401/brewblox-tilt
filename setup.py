from setuptools import find_packages, setup

setup(
    name='brewblox-tilt',
    version='1.1.1',
    long_description=open('README.md').read(),
    url='https://github.com/j616/brewblox-tilt',
    author='James Sandford',
    author_email='brewblox-tilt@j616s.co.uk',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 3.7',
        'Intended Audience :: End Users/Desktop',
        'Topic :: System :: Hardware',
    ],
    keywords='brewing brewpi brewblox embedded plugin service tilt hydrometer',
    packages=find_packages(exclude=['test', 'docker']),
    install_requires=[
        'brewblox-service',
        'bluepy',
        'pint',
        'numpy'
    ],
    python_requires='>=3.7',
    extras_require={'dev': ['pipenv']}
)
