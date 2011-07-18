from setuptools import setup, find_packages

setup(name='deployer',
    version='1.0',
    description="It configures servers. It deploys Django sites. It's amazing!",
    long_description=open('README.rst').read(),
    author='Gabriel Hurley',
    author_email='gabriel@strikeawe.com',
    license='BSD',
    url='https://github.com/zerocoordinate/deployer',
    download_url='git://github.com/zerocoordinate/deployer.git',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'fabric>=1.1.2',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
   ],
)
