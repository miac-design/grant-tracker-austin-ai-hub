#!/usr/bin/env python3
"""Setup script for Dental AI Grant Finder."""

from setuptools import setup, find_packages

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dental-ai-grant-finder",
    version="1.0.0",
    author="Dental AI Grant Finder Team",
    author_email="team@example.com",
    description="A production-ready agent that automatically discovers, scores, and tracks SBIR/Grants.gov opportunities relevant to dental AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dental-ai-grant-finder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "ruff>=0.1.0",
            "black>=23.0.0",
            "pre-commit>=3.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "grant-finder=src.pipeline:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 