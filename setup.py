from setuptools import setup, find_packages

setup(
    name="goalkeeper-cli",
    version="1.0.0",
    description="Telegram notifications and quota reset queue manager for Claude Code, Codex, and Antigravity CLI agents.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    readme="README.md",
    author="Yuvaraj",
    author_email="yuvaraja.1997@gmail.com",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "goalkeeper=goalkeeper_cli.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
