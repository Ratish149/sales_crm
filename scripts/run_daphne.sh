#!/bin/bash
# Script to run Daphne with recommended settings for production

# Ensure we are in the project root (optional check)
# cd /path/to/project

# Run Daphne with increased application close timeout (60 seconds)
# Adjust -p 8000 and sales_crm.asgi:application as needed for your setup
daphne -p 8000 sales_crm.asgi:application --application-close-timeout 60
