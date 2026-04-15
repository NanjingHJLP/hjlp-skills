from setuptools import setup, find_packages

setup(
    name="softwaremove",
    version="1.0.0",
    description="CLI harness for SoftwareMove - move installed software between disks",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "softwaremove=softwaremove.softwaremove_cli:main",
        ],
    },
    python_requires=">=3.10",
)
