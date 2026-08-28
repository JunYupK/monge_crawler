@echo off
cd /d %~dp0
set PYTHONPATH=src
python -m monge_crawler.cli %*
