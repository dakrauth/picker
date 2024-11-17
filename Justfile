set export
set positional-arguments

DEV := "./.dev"
DIST := DEV / "dist"
VENV := DEV / "venv"
BIN := VENV / "bin"
PIP := BIN / "python -m pip --require-venv"


# Display recipe listing
help:
    @just --list

# Show all recipe variables
info:
    @echo dev = {{DEV}}
    @echo dist = {{DIST}}
    @echo venv = {{VENV}}
    @echo bin = {{BIN}}
    @echo pip = {{PIP}}

# Update all dev dependencies
update:
    @echo Installing picker ...
    {{PIP}} install -U -e .

    @echo Installing demo ...
    {{PIP}} install -U -e demo/

    @echo Installing dev dependencies ...
    {{PIP}} install -U \
        build \
        pytest \
        pytest-sugar \
        pytest-clarity \
        pytest-django \
        freezegun \
        coverage \
        tox \
        ipython \
        flake8 \
        black \
        twine

# Create a virtual environment if needed
venv:
    #!/usr/bin/env bash
    if [ ! -d {{VENV}} ]; then
        echo Creating virtual env in dir {{VENV}} ...
        python3 -m venv {{VENV}}
    fi 

# Create virtual environment and install / update all dev dependencies
init: info venv update
    @echo Initialization complete

# Run test suite
test *args='':
    {{BIN}}/pytest -vv -s --diff-width=60 "$@"

# Run test suite
retest:
    {{BIN}}/pytest -vv -s --diff-width=60 --lf

# Run all tox tests
test-all:
    {{BIN}}/tox

# Run coverage report from test suite
cov:
    -{{BIN}}/coverage run -m pytest -vv -s
    {{BIN}}/coverage report
    {{BIN}}/coverage html
    echo HTML coverage report: {{DEV}}/coverage/index.html

# Remove the virtual env dir
rmvenv:
    #!/usr/bin/env bash
    if [ -d {{VENV}} ]; then
        if [ -s $VIRTUAL_ENV ]; then
            echo You must now run `deactivate` manually
        fi
        rm -rf {{VENV}}
    fi

# Remove all *.pyc files and __pycache__ dirs
clean:
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete

# Remove the dev directory, where all generated artifacts are stored
clean-dev:
    rm -rf {{DEV}}

# Remove all build and dist artifacts
clean-build:
    rm -rf ./picker.egg-info ./demo/demo.egg-info {{DIST}}/*

# Clean all build, test, and compile artifacts and remove venv
[confirm('Remove all build, test, coverage, and compiled artifacts and delete venv?')]
purge: clean clean-dev rmvenv clean-build
    echo All artifacts purged

# Build sdist and wheel files for distribution
build:
    {{BIN}}/python -m build --outdir {{DIST}}

# Build distros and upload to PyPI
upload: clean-build build
    twine upload {{DIST}}/*

# Run linter and code formatter tools
lint:
    @echo Linting...
    -{{BIN}}/flake8 picker tests demo

    @echo Format checks...
    -{{BIN}}/black --check --diff -l 100 picker tests demo

# Build the demo Docker container
dbuild *args='':
    docker compose build "$@"

# Run the Django server in a Docker container
drun *args='':
    @echo Browse to http://127.0.0.1:8080 when Docker is up
    docker compose up "$@"

# Execute a command in a running Docker container
dexec *args='':
    docker compose exec app "$@"
