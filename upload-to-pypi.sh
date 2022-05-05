#!/bin/sh

python setup.py sdist

python3 -m twine upload  dist/*
