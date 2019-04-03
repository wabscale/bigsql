from setuptools import setup

setup(
    name='bsql',
    version='1.0.0',
    author='big_J',
    url='https://gitlab.com/b1g_J/bsql',
    description='Just another ORM',
    packages=['bsql'],
    install_requires=['flask-mysql==1.4.0', 'pymysql==0.9.3', 'scanf==1.5.2'],
)
