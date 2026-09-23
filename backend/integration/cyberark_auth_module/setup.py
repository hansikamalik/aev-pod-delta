from setuptools import setup, find_packages

setup(
    name="cyberark_auth_module",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
    ],
)
