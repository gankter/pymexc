from setuptools import setup, find_packages

"""
:author: gankter
:license: MIT License, see LICENSE file.
:copyright: (c) 2025 by gankter.
"""


version = "1.2.12"

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="pymexc",
    version=version,
    author="gankter",
    author_email="",
    url="https://github.com/gankter/pymexc.git",
    download_url=f"https://github.com/gankter/pymexc/archive/refs/tags/v{version}.zip",
    description="Unofficial python library for interacting with the MEXC crypto exchange",
    packages=["pymexc"],
    install_requires=[
        "aiolimiter",
        "websocket-client",
        "curl-cffi",
        "wsaccel",
        "websockets",
        "protobuf",
        "python-dotenv",
        "pydantic",
        "pytest",
        "pytest-asyncio",
        "aiohttp",
    ],
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Communications :: Email",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Intended Audience :: Developers",
        "Intended Audience :: Customer Service",
        "Intended Audience :: Financial and Insurance Industry",
    ],
    include_package_data=True,  # for MANIFEST.in
    python_requires=">=3.6.0",
    package_data={
        package: [
            "py.typed",
            "*.pyi",
            "**/*.pyi",
            "web/*",
            "_async/*",
            "models/*",
            "proto/*",
        ]
        for package in find_packages()
    },
    zip_safe=False,
    project_urls={
        "Bug Reports": "https://github.com/makarworld/pymexc/issues",
        "Source": "https://github.com/gankter/pymexc",
    },
    keywords=[
        "mexc",
        "mexc api",
        "mexc api v1",
        "mexc futures bypass",
        "mexc api v2",
        "mexc api v3",
        "mexc spot",
        "mexc futures",
        "mexc websocket",
        "mexc http",
        "mexc rest",
    ],
)
