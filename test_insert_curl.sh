#!/bin/bash

# Test script for INSERT endpoint using curl
echo "Testing Google Sheets INSERT endpoint with curl..."

# Configuration
SPREADSHEET_ID="1BZvO58ZXB2xB5LZ3mrQlszPZTjxSXSnxr_H-QsMaNVs"
SHEET_NAME="Sheet1"
BASE_URL="http://localhost:2003"

# Test data matching your configuration
TEST_DATA='[
    {
        "FileName": "test_file_1.pdf",
        "University": "MIT",
        "Decision": "Accepted"
    },
    {
        "FileName": "test_file_2.pdf", 
        "University": "Stanford",
        "Decision": "Rejected"
    },
    {
        "FileName": "test_file_3.pdf",
        "University": "Harvard",
        "Decision": "Waitlisted"
    }
]'

echo "Spreadsheet ID: $SPREADSHEET_ID"
echo "Sheet Name: $SHEET_NAME"
echo "Test Data: $TEST_DATA"
echo ""

# Test 1: Basic INSERT request
echo "=== TEST 1: Basic INSERT Request ==="
curl -X POST "$BASE_URL/INSERT/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"form_data\": {
      \"spreadsheet_id\": \"$SPREADSHEET_ID\",
      \"sheet_name\": \"$SHEET_NAME\",
      \"data_to_insert\": $TEST_DATA,
      \"include_headers\": true
    }
  }" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== TEST 2: INSERT with Headers ==="
curl -X POST "$BASE_URL/INSERT/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"form_data\": {
      \"spreadsheet_id\": \"$SPREADSHEET_ID\",
      \"sheet_name\": \"$SHEET_NAME\",
      \"data_to_insert\": $TEST_DATA,
      \"include_headers\": false
    }
  }" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== TEST 3: Content Endpoint ==="
curl -X GET "$BASE_URL/INSERT/v1/content" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== TEST 4: Single Row Insert ==="
SINGLE_ROW_DATA='[
    {
        "FileName": "single_test.pdf",
        "University": "UC Berkeley",
        "Decision": "Pending"
    }
]'

curl -X POST "$BASE_URL/INSERT/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"form_data\": {
      \"spreadsheet_id\": \"$SPREADSHEET_ID\",
      \"sheet_name\": \"$SHEET_NAME\",
      \"data_to_insert\": $SINGLE_ROW_DATA,
      \"include_headers\": true
    }
  }" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== TEST 5: Error Test (Invalid Spreadsheet ID) ==="
curl -X POST "$BASE_URL/INSERT/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"form_data\": {
      \"spreadsheet_id\": \"INVALID_SPREADSHEET_ID\",
      \"sheet_name\": \"$SHEET_NAME\",
      \"data_to_insert\": $TEST_DATA,
      \"include_headers\": true
    }
  }" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== TEST 6: Error Test (Invalid Sheet Name) ==="
curl -X POST "$BASE_URL/INSERT/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"form_data\": {
      \"spreadsheet_id\": \"$SPREADSHEET_ID\",
      \"sheet_name\": \"NonExistentSheet\",
      \"data_to_insert\": $TEST_DATA,
      \"include_headers\": true
    }
  }" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== TEST 7: Error Test (Invalid JSON Data) ==="
curl -X POST "$BASE_URL/INSERT/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"form_data\": {
      \"spreadsheet_id\": \"$SPREADSHEET_ID\",
      \"sheet_name\": \"$SHEET_NAME\",
      \"data_to_insert\": \"invalid json data\",
      \"include_headers\": true
    }
  }" \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n"

echo ""
echo "=== CURL TESTS COMPLETED ==="
echo "Check the responses above for success/error messages."
echo "Make sure your application is running on port 2003 before running these tests." 