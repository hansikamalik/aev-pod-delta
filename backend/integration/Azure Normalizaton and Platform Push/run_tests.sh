#!/usr/bin/env bash

set -e

# Ensure execution context is set to the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Export PYTHONPATH so pytest can locate 'src'
export PYTHONPATH=.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE} Starting Azure Normalization & Push Verification   ${NC}"
echo -e "${BLUE}====================================================${NC}\n"

# Step 1: Validate CAM JSON Schema Contract
echo -e "${YELLOW}[1/3] Validating Draft-07 Schema Contract Syntax...${NC}"
python3 -c "
import json, jsonschema, os
schema_path = os.path.join('$SCRIPT_DIR', 'contracts', 'azure_cam_schema.json')
if not os.path.exists(schema_path):
    raise FileNotFoundError(f'Schema file missing at: {schema_path}')
with open(schema_path) as f:
    schema = json.load(f)
jsonschema.Draft7Validator.check_schema(schema)
print('  └─ [OK] azure_cam_schema.json is a valid Draft-07 schema.')
"
if [ $? -ne 0 ]; then
    echo -e "${RED}[FAIL] Schema contract validation failed!${NC}"
    exit 1
fi
echo ""

# Step 2: Code Quality & Linting Check
echo -e "${YELLOW}[2/3] Running Flake8 Linter Check...${NC}"
flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 src tests --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics
echo -e "${GREEN}  └─ [OK] Linting passed without critical errors.${NC}\n"

# Step 3: Run Pytest Test Suite with Coverage
echo -e "${YELLOW}[3/3] Executing Pytest Suite & Coverage Threshold Check...${NC}"
pytest tests/ \
    -v \
    --doctest-modules \
    --cov=src \
    --cov-report=term-missing \
    --cov-fail-under=90

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}====================================================${NC}"
    echo -e "${GREEN} SUCCESS: All tests, linting, and coverage passed!  ${NC}"
    echo -e "${GREEN}====================================================${NC}"
else
    echo -e "\n${RED}====================================================${NC}"
    echo -e "${RED} FAILURE: Pipeline tests or coverage failed!       ${NC}"
    echo -e "${RED}====================================================${NC}"
    exit 1
fi
