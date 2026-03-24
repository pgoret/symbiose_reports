from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().strip().splitlines()

from pathlib import Path
version = {}
exec((Path('symbiose_reports') / '__init__.py').read_text(), version)

setup(
    name='symbiose_reports',
    version=version['__version__'],
    description='Custom Symbiose reports for ERPNext',
    author='CAC Consultants',
    author_email='support@caconsultants.be',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
