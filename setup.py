from distutils.core import setup
from setuptools import find_packages

setup(
    name='django-two-factor-auth',
    version='0.1.2',
    author='Bouke Haarsma',
    author_email='bouke@webatoom.nl',
    packages=find_packages(exclude='demo'),
    package_data={'two_factor': ['templates/two_factor/*.html',],},
    url='http://github.com/Bouke/django-two-factor-auth',
    description='Complete Two-Factor Authentication for Django',
    license='MIT',
    long_description=open('README.rst').read(),
    install_requires=[
        'oath == 1.1'
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Security',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
)
