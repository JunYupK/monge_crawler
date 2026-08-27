#!/usr/bin/env bash
cd "$(dirname "$0")"
PYTHONPATH=src python3 -m monge_crawler.cli "$@"
