# Set environment variables BEFORE any imports to prevent PyO3 conflicts
import os
os.environ['CRYPTOGRAPHY_DONT_BUILD_RUST'] = '1'
os.environ['CRYPTOGRAPHY_USE_PURE_PYTHON'] = '1'

# Import Google API libraries first to prevent PyO3 conflicts
from google.oauth2 import service_account
from googleapiclient.discovery import build

import google_auth_httplib2

# Then import other dependencies
from workflows_cdk import Response, Request, Router
from flask import request as flask_request
import requests
import json
import logging
import traceback
import re
from src.utils.google_sheets import get_google_sheets_service

# Set up logging
logging.basicConfig(level=logging.ERROR)  # Only log errors by default
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Service account configuration - Update these paths as needed
SERVICE_ACCOUNT_FILE = "/usr/src/app/quail-asset-7c70b02f0362.json"

# Create router instance
router = Router()


@router.route("/execute", methods=["GET", "POST"])
def execute():
    try:
        request_obj = Request(flask_request)
        data = request_obj.data
        form_data = data.get("form_data", data)
        spreadsheet_id = form_data.get("spreadsheet_id")
        sheet_name = form_data.get("sheet_name")
        data_to_insert_raw = form_data.get("data_to_insert", "[]")
        include_headers = form_data.get("include_headers", False)

        # Validation
        if not spreadsheet_id:
            return Response(
                data={"error": "Spreadsheet ID is required"},
                metadata={"status": "error"}
            )
        if not sheet_name:
            return Response(
                data={"error": "Sheet name is required"},
                metadata={"status": "error"}
            )

        # Parse JSON input
        try:
            if isinstance(data_to_insert_raw, str):
                data_objects = json.loads(data_to_insert_raw)
            else:
                data_objects = data_to_insert_raw
            if not isinstance(data_objects, list):
                raise ValueError("data_to_insert must be a list/array")
            if not all(isinstance(row, dict) for row in data_objects):
                raise ValueError("Each element in data_to_insert must be an object")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON in data_to_insert: {e}")
            return Response(
                data={"error": "Invalid JSON format for 'data_to_insert'. Please enter a valid JSON array of objects."},
                metadata={"status": "error"}
            )
        except ValueError as e:
            logger.error(f"Validation error in data_to_insert: {e}")
            return Response(
                data={"error": f"Invalid format for 'data_to_insert': {str(e)}. Please enter a valid JSON array of objects."},
                metadata={"status": "error"}
            )
        except Exception as e:
            logger.error(f"Failed to parse data_to_insert: {e}")
            return Response(
                data={"error": "Invalid format for 'data_to_insert'. Please enter a valid JSON array of objects."},
                metadata={"status": "error"}
            )

        if not data_objects:
            return Response(
                data={"error": "Parsed data_to_insert is empty"},
                metadata={"status": "error"}
            )

        # Create Google Sheets service
        try:
            service = get_google_sheets_service()
        except Exception as service_error:
            logger.error(f"Failed to create Google Sheets service: {service_error}")
            return Response(
                data={"error": f"Failed to create Google Sheets service: {str(service_error)}"},
                metadata={"status": "error"}
            )

        # Extract headers and convert data to rows
        headers = list(data_objects[0].keys())
        rows = [[row.get(h, "") for h in headers] for row in data_objects]
        final_data = [headers] + rows if include_headers else rows

        # Insert data using the Google Sheets API
        try:
            range_param = f"{sheet_name}!A1"
            body = {"values": final_data}
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_param,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
        except Exception as api_error:
            logger.error(f"API error while inserting data: {api_error}")
            return Response(
                data={"error": f"Failed to insert data into Google Sheet: {str(api_error)}"},
                metadata={"status": "error"}
            )

        return Response(
            data={
                "message": f"Successfully appended {len(rows)} rows",
                "updated_range": result.get("updates", {}).get("updatedRange", ""),
                "inserted_data": data_objects
            },
            metadata={
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "rows_inserted": len(rows)
            }
        )

    except Exception as e:
        logger.error(f"INSERT SHEET DATA EXECUTE ERROR: {e}")
        logger.error(traceback.format_exc())
        return Response(
            data={"error": f"Failed to insert data into Google Sheet: {str(e)}"},
            metadata={"status": "error"}
        )

@router.route("/content", methods=["GET", "POST"])
def content():
    """
    Fetch available spreadsheets and sheets for dynamic form fields
    """
    try:
        request = Request(flask_request)
        data = request.data
        form_data = data.get("form_data", data)
        output = {
            "message": "Google Sheets INSERT module is available",
            "available_operations": [
                "insert - Insert data into Google Sheet"
            ],
            "required_fields": {
                "spreadsheet_id": "The ID of the Google Sheet (from URL)",
                "sheet_name": "The name of the sheet tab",
                "data_to_insert": "JSON array of objects to insert"
            },
            "optional_fields": {
                "include_headers": "Boolean - whether to include headers (defaults to false)"
            },
            "data_format_example": [
                {"Name": "John Doe", "Email": "john@example.com", "Phone": "123-456-7890"},
                {"Name": "Jane Smith", "Email": "jane@example.com", "Phone": "098-765-4321"}
            ],
            "setup_instructions": {
                "step_1": "Create a service account in Google Cloud Console",
                "step_2": "Download the JSON key file",
                "step_3": "Share your Google Sheet with the service account email",
                "step_4": "Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable or place JSON file in project directory"
            }
        }
        return Response(
            data=output,
            metadata={"status": "success"}
        )
    except Exception as e:
        logger.error(f"INSERT SHEET DATA CONTENT ERROR: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            data={"error": f"Failed to get content: {str(e)}"},
            metadata={"status": "error"}
        )
