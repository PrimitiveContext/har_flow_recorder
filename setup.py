"""Setup script for apitool-cli package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="apitool-cli",
    version="1.0.0",
    author="API Tool CLI Contributors",
    description="Browser Recording & Security Testing CLI Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/apitool-cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pyaudio>=0.2.11",
        "openai>=1.0.0",
        "numpy>=1.24.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "apitool=scripts.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)