#!/bin/bash

export GOOGLE_APPLICATION_CREDENTIALS="gcp_conf.json"
uvicorn app:app --reload