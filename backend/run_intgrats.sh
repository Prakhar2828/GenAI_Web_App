#!/bin/bash

# Script to run the sample integration simulation
cd integration || { echo "Error: integration directory not found"; exit 1; }
./intgrats.exe INET_I.INET

# Capture the exit status
exit_status=$?

# Output some info for debugging
echo "Command executed in directory: $(pwd)"
echo "Exit status: $exit_status"

exit $exit_status