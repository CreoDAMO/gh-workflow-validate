from setuptools import setup, find_packages

setup(
    name='gh-workflow-validate',
    version='1.0.0',
    description='A parser-backed, schema-validated GitHub Actions workflow validator with batch mode, JSON output, and CI annotations.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='CREODAMO',
    author_email='creodamo@example.com',  # Replace
    url='https://github.com/CREODAMO/gh-workflow-validate',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    scripts=['gh-workflow-validate'],
    install_requires=['ruamel.yaml>=0.17.0'],
    python_requires='>=3.10',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
