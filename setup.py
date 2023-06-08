from setuptools import setup

setup(
    name="chatty",
    version="0.0.1",
    python_requires='>=3.10',
    description="A simple interface definition language",
    author="Cute Engineering",
    author_email="contact@cute.engineering",
    url="https://cute.engineering/",
    packages=["chatty"],
    install_requires=[
    ],
    entry_points={
        "console_scripts": [
            "chatty = chatty:main",
        ],
    },
    license="MIT",
    platforms="any",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
