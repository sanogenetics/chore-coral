Chore Coral
===========

[![PyPI version](https://badge.fury.io/py/chorecoral.svg)](https://badge.fury.io/py/chorecoral)

Library to simplify interactions with AWS Batch by reducing each job blueprint to have:
 - one environment
 - one queue
 - run docker image via Fargate
 - be named after the docker image

Also allows monitoring of job completion without needing to have an always-on server running. Instead the job statuses can
be polled on demand.

development
-----------

Commands to setup for development from a blank slate
```sh
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev]'  # Install using pip including development extras
pip-sync requirements.txt requirements.dev.txt # Install exact dependency versions
pre-commit install  # Enable pre-commit hooks
pre-commit run --all-files  # Run pre-commit hooks without committing
# Note pre-commit is configured to use:
# - seed-isort-config to better categorise third party imports
# - isort to sort imports
# - black to format code
```

Commands that are useful day-to-day
```sh
pytest  # Run tests
coverage run --source=chorecoral -m chorecoral && coverage report -m  # Run tests, print coverage
mypy .  # Type checking
pip-compile && pip-compile --extra dev --output-file requirements.dev.txt # Freeze dependencies
pipdeptree  # Print dependencies
```

Useful Docker commands
```sh
docker system prune --volumes # remove all stopped containers, volumes, dangling images, etc
```

Global git ignores per https://help.github.com/en/github/using-git/ignoring-files#configuring-ignored-files-for-all-repositories-on-your-computer

For release to PyPI see https://packaging.python.org/tutorials/packaging-projects/
