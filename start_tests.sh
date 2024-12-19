#!/bin/bash

export GOOGLE_APPLICATION_CREDENTIALS="gcp_conf.json"
pytest tests/test_nlq_api_edge_cases.py
# pytest tests/test_nlq_api_edge_cases.py -v --log-cli-level=DEBUG
# pytest tests/test_nlq_api.py
# pytest tests/test_nlq_api.py -v --log-cli-level=DEBUG
