from setuptools import setup

setup(
    name="Chore Coral",
    version="0.0.1",
    author="Adam Faulconbridge",
    author_email="afaulconbridge@googlemail.com",
    packages=["chorecoral"],
    description="Library to simplify interactions with AWS Batch by reducing it to one compute environment to one queue to one job blueprint.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/sanogenetics/chore-coral",
    install_requires=["boto3"],
    extras_require={
        "dev": [
            "pytest-cov",
            "flake8",
            "black",
            "pylint",
            "pip-tools",
            "pipdeptree",
            "pre-commit",
            "moto >= 3.0.2.dev17",  # minimum version to include fixes
            "docker",  # optional moto requirement to mock batch
        ],
    },
)
