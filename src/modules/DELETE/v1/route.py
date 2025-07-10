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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Service account configuration
SERVICE_ACCOUNT_FILE = "/usr/src/app/quail-asset-7c70b02f0362.json"

# Create router instance
router = Router()


def parse_row_numbers(row_numbers_str):
    """
    Parse row numbers string into a list of row numbers to delete.
    Supports formats like: "5", "5-10", "5,7,10-12"
    """
    try:
        if not row_numbers_str or not row_numbers_str.strip():
            raise ValueError("Row numbers string is empty")
        row_numbers = []
        parts = row_numbers_str.strip().split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start_row = int(start.strip())
                    end_row = int(end.strip())
                    if start_row > end_row:
                        raise ValueError(f"Invalid range: {part} (start > end)")
                    if start_row < 1:
                        raise ValueError(f"Invalid row number: {start_row} (must be >= 1)")
                    row_numbers.extend(range(start_row, end_row + 1))
                except ValueError as e:
                    raise ValueError(f"Invalid range format: {part}. Use format like '5-10'")
            else:
                try:
                    row_num = int(part)
                    if row_num < 1:
                        raise ValueError(f"Invalid row number: {row_num} (must be >= 1)")
                    row_numbers.append(row_num)
                except ValueError as e:
                    raise ValueError(f"Invalid row number: {part}. Must be a valid integer")
        row_numbers = sorted(list(set(row_numbers)))
        if not row_numbers:
            raise ValueError("No valid row numbers found")
        return row_numbers
    except Exception as e:
        logger.error(f"Error parsing row numbers: {e}")
        raise

def delete_rows_from_sheet(service, spreadsheet_id, sheet_name, row_numbers):
    """
    Delete specific rows from a Google Sheet
    """
    try:
        # First, get the sheet ID
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = None
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                sheet_id = sheet['properties']['sheetId']
                break
        if sheet_id is None:
            raise ValueError(f"Sheet '{sheet_name}' not found in spreadsheet")
        row_numbers_desc = sorted(row_numbers, reverse=True)
        requests = []
        for row_num in row_numbers_desc:
            row_index = row_num - 1
            request = {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_index,
                        "endIndex": row_index + 1
                    }
                }
            }
            requests.append(request)
        body = {
            "requests": requests
        }
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        return result
    except Exception as e:
        logger.error(f"Error deleting rows: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@router.route("/execute", methods=["GET", "POST"])
def execute():
    """
    Delete rows from a Google Sheet
    """
    logger.info("=== DELETE ROWS EXECUTE START ===")
    try:
        request = Request(flask_request)
        data = request.data
        form_data = data.get("form_data", data)
        spreadsheet_id = form_data.get("spreadsheet_id")
        sheet_name = form_data.get("sheet_name")
        row_numbers_str = form_data.get("row_numbers", "")
        confirm_deletion = form_data.get("confirm_deletion", False)
        # Validate required fields
        if not spreadsheet_id:
            logger.error("Spreadsheet ID is missing")
            return Response(
                data={"error": "Spreadsheet ID is required"},
                metadata={"status": "error"}
            )
        if not sheet_name:
            logger.error("Sheet name is missing")
            return Response(
                data={"error": "Sheet name is required"},
                metadata={"status": "error"}
            )
        if not row_numbers_str:
            logger.error("Row numbers are missing")
            return Response(
                data={"error": "Row numbers are required"},
                metadata={"status": "error"}
            )
        if not confirm_deletion:
            logger.error("Deletion not confirmed")
            return Response(
                data={"error": "You must confirm the deletion by checking the confirmation box"},
                metadata={"status": "error"}
            )
        try:
            row_numbers = parse_row_numbers(row_numbers_str)
        except ValueError as e:
            logger.error(f"Invalid row numbers format: {e}")
            return Response(
                data={"error": f"Invalid row numbers format: {str(e)}"},
                metadata={"status": "error"}
            )
        try:
            service = get_google_sheets_service()
        except Exception as service_error:
            logger.error(f"Failed to create Google Sheets service: {service_error}")
            error_str = str(service_error).lower()
            if "permission" in error_str or "unauthorized" in error_str or "403" in error_str:
                logger.error("✗ ERROR TYPE: Permission/Authorization issue")
            elif "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.error("✗ ERROR TYPE: API quota/rate limit exceeded")
            elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
                logger.error("✗ ERROR TYPE: Network connectivity issue")
            elif "invalid" in error_str and "key" in error_str:
                logger.error("✗ ERROR TYPE: Invalid service account credentials")
            else:
                logger.error("✗ ERROR TYPE: Unknown service creation error")
            return Response(
                data={"error": f"Failed to create Google Sheets service: {str(service_error)}"},
                metadata={"status": "error"}
            )
        try:
            result = delete_rows_from_sheet(service, spreadsheet_id, sheet_name, row_numbers)
        except Exception as delete_error:
            logger.error(f"Error deleting rows: {delete_error}")
            error_str = str(delete_error).lower()
            if "permission" in error_str or "unauthorized" in error_str or "403" in error_str:
                logger.error("✗ ERROR TYPE: Spreadsheet permission issue")
            elif "not found" in error_str or "404" in error_str:
                logger.error("✗ ERROR TYPE: Spreadsheet or sheet not found")
            elif "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.error("✗ ERROR TYPE: API quota/rate limit exceeded")
            elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
                logger.error("✗ ERROR TYPE: Network connectivity issue")
            else:
                logger.error("✗ ERROR TYPE: Unknown delete error")
            return Response(
                data={"error": f"Failed to delete rows from Google Sheet: {str(delete_error)}"},
                metadata={"status": "error"}
            )
        logger.info("=== DELETE ROWS SUCCESS ===")
        return Response(
            data={
                "message": f"Successfully deleted {len(row_numbers)} rows",
                "deleted_rows": row_numbers,
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name
            },
            metadata={
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "deleted_rows_count": len(row_numbers)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in execute function: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            data={"error": f"Unexpected error: {str(e)}"},
            metadata={"status": "error"}
        )

@router.route("/content", methods=["GET", "POST"])
def content():
    """
    Return content for the module (not used for DELETE module)
    """
    try:
        return Response(
            data={
                "message": "DELETE module content endpoint",
                "description": "This endpoint is not used for the DELETE module"
            },
            metadata={"status": "success"}
        )
    except Exception as e:
        logger.error(f"Error in content function: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            data={"error": f"Error in content function: {str(e)}"},
            metadata={"status": "error"}
        ) 