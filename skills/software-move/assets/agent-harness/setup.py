from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-softwaremove",
    version="1.0.0",
    description="CLI harness for SoftwareMove - move installed software between disks",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-softwaremove=cli_anything.softwaremove.softwaremove_cli:main",
        ],
    },
    package_data={
        "cli_anything.softwaremove": ["skills/*.md"],
    },
    include_package_data=True,
    python_requires=">=3.10",
)
