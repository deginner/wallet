import sys
from setuptools import setup

requires = [
    "supervisor", "gunicorn", "gevent",
    "flask-restful", "flask-login", "flask-cors", "sqlalchemy>=1.0.9",
    "bitjws==0.6.3.1", "entropy"
]
if sys.version_info < (3, 5):
    requires.append('enum34')

classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 2",
    "Topic :: Software Development :: Libraries",
    "Topic :: Security :: Cryptography"
]


setup(
    name="wallet",
    version="0.0.1",
    description='Wallet',
    author='Guilherme Polo',
    author_email='gp@deginner.com',
    url='https://github.com/g-p-g/wallet',
    classifiers=classifiers,
    include_package_data=True,
    packages=['sw', 'sw/handler'],
    setup_requires=['pytest-runner'],
    install_requires=requires,
    tests_require=['pytest', 'pytest-cov']
)
