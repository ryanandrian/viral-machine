#!/bin/bash
cd /home/rad4vm/viral-machine
/usr/bin/python3.11 -m src.orchestrator.pipeline --publish >> logs/cron_$(date +%Y%m%d).log 2>&1
