from distutils.core import setup
from setuptools import find_packages

setup(
    name='django-two-factor-auth',
    version='0.3.0-dev',
    author='Bouke Haarsma',
    author_email='bouke@webatoom.nl',
    packages=find_packages(exclude=('example', 'tests',)),
    package_data={'two_factor': ['templates/*.html', ], },
    url='http://github.com/Bouke/django-two-factor-auth',
    description='Complete Two-Factor Authentication for Django',
    license='MIT',
    long_description=open('README.rst').read(),
    install_requires=['Django>=1.4,<1.7', 'django_otp>=0.2.0,<0.3.0'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Security',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
)
