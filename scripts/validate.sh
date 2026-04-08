#!/bin/bash

echo "Running OpenEnv validation..."

openenv validate

if [ $? -eq 0 ]; then
  echo "Validation passed ✅"
else
  echo "Validation failed ❌"
fi