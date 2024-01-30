from setuptools import find_packages, setup

setup(
    name='django-two-factor-auth',
    version='1.16',
    description='Complete Two-Factor Authentication for Django',
    long_description=open('README.rst', encoding='utf-8').read(),
    author='Bouke Haarsma',
    author_email='bouke@haarsma.eu',
    url='https://github.com/jazzband/django-two-factor-auth',
    download_url='https://pypi.python.org/project/django-two-factor-auth',
    license='MIT',
    packages=find_packages(exclude=('example', 'tests', 'tests.*')),
    install_requires=[
        'Django>=3.2',
        'django_otp>=0.8.0',
        'qrcode>=4.0.0,<7.99',
        'django-phonenumber-field<8',
        'django-formtools',
    ],
    extras_require={
        'call': ['twilio>=6.0'],
        'sms': ['twilio>=6.0'],
        'whatsapp': ['twilio>=6.0'],
        'webauthn': ['webauthn>=1.11.0,<1.99'],
        'yubikey': ['django-otp-yubikey'],
        'phonenumbers': ['phonenumbers>=7.0.9,<8.99'],
        'phonenumberslite': ['phonenumberslite>=7.0.9,<8.99'],
    },
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Framework :: Django :: 4.1',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Security',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
    ],
)
