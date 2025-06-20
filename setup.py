from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="waproprint",
    version="1.0.0",
    author="Tom Sapletta",
    author_email="info@softreck.dev",
    description="A tool for generating and printing documents from database queries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/text2doc/waproprint",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        line.strip() for line in open('requirements.txt').readlines() 
        if line.strip() and not line.startswith('#')
    ],
    entry_points={
        'console_scripts': [
            'waproprint=sql2html:main',
        ],
    },
    include_package_data=True,
)
