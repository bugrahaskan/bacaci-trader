from setuptools import setup, find_packages

setup(
    name='bacaci-trader',
    version='1.5',
    description="Algorithmic Backtesting and Trading for Python",
    author='Fevzi Buğra Haskan',
    author_email='bugrahaskan@outlook.com',
    url='https://github.com/bugrahaskan',
    package_dir = {"": "src"},
    packages=find_packages(exclude=["__pycache__"]),
    entry_points={
        'console_scripts': [
            'bacaci = trader:main',
        ]
    },
    install_requires=[
        'cython',
        'numpy',
        'pandas',
        'pandas-ta',
        'matplotlib',
        'plotly',
        'scipy',
        'scikit-learn',
        'schedule',
        'asyncio',
        'python-binance',
        'configparser',
        'ibapi',
        'blpapi',
        'alpaca',
        'flask',
        'openpyxl'
    ],
    python_requires='>=3.8',
    license='The MIT License (MIT)'
)