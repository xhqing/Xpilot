from setuptools import setup, find_packages

setup(
    name='xray-pilot',
    version='0.1.0',
    description='A CLI proxy toolkit with xray backend',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'click>=8.0',
        'requests>=2.28',
        'requests[socks]>=2.28',
        'pyyaml>=6.0',
    ],
    entry_points={
        'console_scripts': [
            'xray-pilot=xray_pilot.cli:cli',
            'dev-proxy=dev.dev_proxy:main',
        ],
    },
)
