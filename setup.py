from setuptools import setup, find_packages

setup(
    name="tonuino-organizer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "feedparser>=6.0.10",
        "requests>=2.31.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
        "mutagen>=1.47.0",
    ],
    entry_points={
        "console_scripts": [
            "tonuino-organize=tonuino_organizer.cli:main",
        ],
    },
)

