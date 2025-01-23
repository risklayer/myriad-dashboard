#!/bin/bash

ruff check --fix

ruff format --config ruff.toml
