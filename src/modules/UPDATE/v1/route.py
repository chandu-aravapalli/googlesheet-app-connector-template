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


def parse_update_data(update_data_raw):
    """
    Parse update data string or list into a format suitable for Google Sheets API
    """
    try:
        # Accept both string and list types
        if isinstance(update_data_raw, str):
            if not update_data_raw.strip():
                raise ValueError("Update data is empty")
            parsed_data = json.loads(update_data_raw)
        elif isinstance(update_data_raw, list):
            parsed_data = update_data_raw
        else:
            raise ValueError("Update data must be a string or a list")
        if isinstance(parsed_data, list):
            if all(isinstance(row, list) for row in parsed_data):
                return parsed_data
            else:
                return [parsed_data]
        elif isinstance(parsed_data, (str, int, float, bool)):
            return [[parsed_data]]
        else:
            raise ValueError(f"Unsupported data format: {type(parsed_data)}")
    except Exception as e:
        logger.error(f"Error parsing update data: {e}")
        raise ValueError(f"Invalid update data format: {str(e)}")

def update_sheet_data(service, spreadsheet_id, sheet_name, range_param, update_data, value_input_option='RAW'):
    """
    Update data in a Google Sheet
    """
    try:
        if range_param and range_param.strip():
            full_range = f"{sheet_name}!{range_param.strip()}"
        else:
            full_range = sheet_name
        body = {
            "values": update_data
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        return result
    except Exception as e:
        logger.error(f"Error updating sheet data: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

@router.route("/execute", methods=["GET", "POST"])
def execute():
    """
    Update data in a Google Sheet
    """
    logger.info("=== UPDATE SHEET DATA EXECUTE START ===")
    try:
        request = Request(flask_request)
        data = request.data
        form_data = data.get("form_data", data)
        spreadsheet_id = form_data.get("spreadsheet_id")
        sheet_name = form_data.get("sheet_name")
        range_param = form_data.get("range", "")
        update_data_raw = form_data.get("update_data", "")
        value_input_option = form_data.get("value_input_option", "RAW")
        confirm_update = form_data.get("confirm_update", False)
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
        if not update_data_raw:
            logger.error("Update data is missing")
            return Response(
                data={"error": "Update data is required"},
                metadata={"status": "error"}
            )
        if not confirm_update:
            logger.error("Update not confirmed")
            return Response(
                data={"error": "You must confirm the update by checking the confirmation box"},
                metadata={"status": "error"}
            )
        try:
            update_data = parse_update_data(update_data_raw)
        except ValueError as e:
            logger.error(f"Invalid update data format: {e}")
            return Response(
                data={"error": f"Invalid update data format: {str(e)}"},
                metadata={"status": "error"}
            )
        valid_options = ['RAW', 'USER_ENTERED']
        if value_input_option not in valid_options:
            logger.error(f"Invalid value input option: {value_input_option}")
            return Response(
                data={"error": f"Invalid value input option. Must be one of: {', '.join(valid_options)}"},
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
            result = update_sheet_data(service, spreadsheet_id, sheet_name, range_param, update_data, value_input_option)
        except Exception as update_error:
            logger.error(f"Error updating data: {update_error}")
            error_str = str(update_error).lower()
            if "permission" in error_str or "unauthorized" in error_str or "403" in error_str:
                logger.error("✗ ERROR TYPE: Spreadsheet permission issue")
            elif "not found" in error_str or "404" in error_str:
                logger.error("✗ ERROR TYPE: Spreadsheet or sheet not found")
            elif "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                logger.error("✗ ERROR TYPE: API quota/rate limit exceeded")
            elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
                logger.error("✗ ERROR TYPE: Network connectivity issue")
            elif "invalid" in error_str and "range" in error_str:
                logger.error("✗ ERROR TYPE: Invalid range format")
            else:
                logger.error("✗ ERROR TYPE: Unknown update error")
            return Response(
                data={"error": f"Failed to update data in Google Sheet: {str(update_error)}"},
                metadata={"status": "error"}
            )
        logger.info("=== UPDATE SHEET DATA SUCCESS ===")
        return Response(
            data={
                "message": f"Successfully updated data",
                "updated_range": result.get("updatedRange", ""),
                "updated_rows": len(update_data),
                "updated_columns": len(update_data[0]) if update_data else 0,
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name
            },
            metadata={
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "updated_rows_count": len(update_data),
                "updated_columns_count": len(update_data[0]) if update_data else 0
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
    Return content for the module (not used for UPDATE module)
    """
    try:
        return Response(
            data={
                "message": "UPDATE module content endpoint",
                "description": "This endpoint is not used for the UPDATE module"
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