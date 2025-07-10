# Set environment variables BEFORE any imports to prevent PyO3 conflicts
import os
os.environ['CRYPTOGRAPHY_DONT_BUILD_RUST'] = '1'
os.environ['CRYPTOGRAPHY_USE_PURE_PYTHON'] = '1'

from workflows_cdk import Response, Request, Router
from flask import request as flask_request
import requests
import json
import logging
import traceback

import google_auth_httplib2

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Service account configuration
SERVICE_ACCOUNT_FILE = "/usr/src/app/quail-asset-7c70b02f0362.json"

# Create router instance
router = Router()

# Import Google API libraries for service account authentication
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

from src.utils.google_sheets import get_google_sheets_service

@router.route("/execute", methods=["GET", "POST"])
def execute():
    logger.info("=== READ SHEET DATA EXECUTE START ===")
    try:
        request = Request(flask_request)
        form_data = request.data.get("form_data", request.data)
        spreadsheet_id = form_data.get("spreadsheet_id")
        sheet_name = form_data.get("sheet_name")
        range_str = form_data.get("range", "")
        include_headers = form_data.get("include_headers", True)

        if not spreadsheet_id:
            return Response(data={"error": "Spreadsheet ID is required"}, metadata={"status": "error"})
        if not sheet_name:
            return Response(data={"error": "Sheet name is required"}, metadata={"status": "error"})

        if range_str and range_str.strip():
            full_range = f"{sheet_name}!{range_str.strip()}"
        else:
            full_range = sheet_name

        service = get_google_sheets_service(readonly=True)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=full_range
        ).execute()
        values = result.get('values', [])

        if not include_headers and values:
            values = values[1:]

        return Response(
            data={
                "rows": values,
                "row_count": len(values),
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "range": full_range
            },
            metadata={
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "range": full_range,
                "row_count": len(values)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in execute function: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response(
            data={"error": f"Unexpected error: {str(e)}"},
            metadata={"status": "error"}
        )


@router.route("/content", methods=["GET", "POST"])
def content():
    """
    Fetch available spreadsheets and sheets for dynamic form fields
    """
    logger.info("=== READ SHEET DATA CONTENT START ===")
    
    try:
        request = Request(flask_request)
        logger.info(f"Content request received: {request}")
        
        data = request.data
        logger.info(f"Content request data: {data}")
        
        form_data = data.get("form_data", {})
        content_object_names = data.get("content_object_names", [])
        
        logger.info(f"Form data: {form_data}")
        logger.info(f"Content object names: {content_object_names}")
        
        # Extract content object names from objects if needed
        if isinstance(content_object_names, list) and content_object_names and isinstance(content_object_names[0], dict):
            content_object_names = [obj.get("id") for obj in content_object_names if "id" in obj]
            logger.info(f"Extracted content object names: {content_object_names}")
        
        content_objects = []
        
        # Get credentials from connection data
        logger.info("Getting credentials for content...")
        
        # Try different ways to access credentials
        credentials_data = {}
        if hasattr(request, 'credentials') and request.credentials:
            logger.info("Request has credentials attribute")
            credentials_data = request.credentials.get("connection_data", {})
        elif hasattr(request, 'connection_data') and request.connection_data:
            logger.info("Request has connection_data attribute")
            credentials_data = request.connection_data
        elif hasattr(request, 'data') and isinstance(request.data, dict):
            logger.info("Looking for credentials in request.data")
            credentials_data = request.data.get("credentials", {}).get("connection_data", {})
        else:
            logger.warning("No credentials found in request object")
        
        service_account_info = credentials_data.get("service_account_info")
        
        if not service_account_info:
            logger.warning("No service account info found for content request")
            return Response(
                data={"content_objects": []},
                metadata={"status": "no_credentials"}
            )
        
        # Parse service account info
        logger.info("Parsing service account info for content...")
        if isinstance(service_account_info, str):
            try:
                service_account_info = json.loads(service_account_info)
                logger.info("Successfully parsed service account info for content")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse service account info JSON for content: {e}")
                return Response(
                    data={"content_objects": []},
                    metadata={"status": "invalid_credentials"}
                )
        
        # Initialize Google Sheets service
        logger.info("Initializing Google Sheets service for content...")
        try:
            service = get_google_sheets_service()
            logger.info("Successfully created Google Sheets service for content")
        except Exception as e:
            logger.error(f"Failed to create Google Sheets service for content: {e}")
            return Response(
                data={"content_objects": []},
                metadata={"status": "authorization_error"}
            )
        
        for content_object_name in content_object_names:
            logger.info(f"Processing content object: {content_object_name}")
            
            if content_object_name == "available_spreadsheets":
                logger.info("Fetching available spreadsheets...")
                try:
                    # Note: The Google Sheets API doesn't provide a direct way to list all spreadsheets
                    # This would require the Google Drive API. For now, we'll return an empty list
                    # with a note that this requires Drive API access
                    logger.warning("Listing all spreadsheets requires Google Drive API access")
                    spreadsheet_data = []
                    
                    logger.info(f"Found {len(spreadsheet_data)} spreadsheets")
                    content_objects.append({
                        "content_object_name": "available_spreadsheets",
                        "data": spreadsheet_data
                    })
                except Exception as e:
                    logger.error(f"Failed to fetch spreadsheets: {e}")
                    content_objects.append({
                        "content_object_name": "available_spreadsheets",
                        "data": []
                    })
                    
            elif content_object_name == "available_sheets":
                logger.info("Fetching available sheets...")
                # Get sheets from a specific spreadsheet
                spreadsheet_id = form_data.get("spreadsheet_id")
                if spreadsheet_id:
                    logger.info(f"Getting sheets for spreadsheet: {spreadsheet_id}")
                    try:
                        # Use Google Sheets API to get sheet metadata
                        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                        sheets = spreadsheet.get('sheets', [])
                        
                        sheet_data = []
                        for sheet in sheets:
                            sheet_properties = sheet.get('properties', {})
                            sheet_data.append({
                                "value": sheet_properties.get('title', ''),
                                "label": sheet_properties.get('title', '')
                            })
                        
                        logger.info(f"Found {len(sheet_data)} sheets")
                        content_objects.append({
                            "content_object_name": "available_sheets",
                            "data": sheet_data
                        })
                    except Exception as e:
                        logger.error(f"Failed to fetch sheets: {e}")
                        content_objects.append({
                            "content_object_name": "available_sheets",
                            "data": []
                        })
                else:
                    logger.warning("No spreadsheet_id provided for available_sheets")
                    content_objects.append({
                        "content_object_name": "available_sheets",
                        "data": []
                    })
    
    except Exception as e:
        logger.error(f"=== READ SHEET DATA CONTENT ERROR ===")
        logger.error(f"Unexpected error in content: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info(f"=== READ SHEET DATA CONTENT SUCCESS ===")
    logger.info(f"Returning {len(content_objects)} content objects")
    return Response(data={"content_objects": content_objects})
