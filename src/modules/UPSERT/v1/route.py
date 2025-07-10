# Set environment variables BEFORE any imports to prevent PyO3 conflicts
import os
os.environ['CRYPTOGRAPHY_DONT_BUILD_RUST'] = '1'
os.environ['CRYPTOGRAPHY_USE_PURE_PYTHON'] = '1'

from google.oauth2 import service_account
from googleapiclient.discovery import build
import google_auth_httplib2

from workflows_cdk import Response, Request, Router
from flask import request as flask_request
import json
import logging
import traceback

from src.utils.google_sheets import get_google_sheets_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = "/usr/src/app/quail-asset-7c70b02f0362.json"
router = Router()

def parse_data_to_upsert(data_raw):
    try:
        if isinstance(data_raw, str):
            data = json.loads(data_raw)
        elif isinstance(data_raw, list):
            data = data_raw
        else:
            raise ValueError("Data to upsert must be a string or a list")
        if not isinstance(data, list) or not all(isinstance(obj, dict) for obj in data):
            raise ValueError("Data to upsert must be a list of objects")
        return data
    except Exception as e:
        logger.error(f"Error parsing data to upsert: {e}")
        raise ValueError(f"Invalid data to upsert: {str(e)}")

def get_sheet_data(service, spreadsheet_id, sheet_name):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name
        ).execute()
        values = result.get('values', [])
        return values
    except Exception as e:
        logger.error(f"Error reading sheet data: {e}")
        raise

def upsert_rows(service, spreadsheet_id, sheet_name, key_column, data_to_upsert):
    sheet_data = get_sheet_data(service, spreadsheet_id, sheet_name)
    if not sheet_data or not sheet_data[0]:
        raise ValueError("Sheet is empty or missing headers")
    headers = sheet_data[0]
    key_idx = None
    try:
        key_idx = headers.index(key_column)
    except ValueError:
        raise ValueError(f"Key column '{key_column}' not found in sheet headers: {headers}")
    key_to_row = {}
    for idx, row in enumerate(sheet_data[1:], start=2):
        if len(row) > key_idx:
            key_val = str(row[key_idx]).strip()
            if not key_val or key_val == key_column:
                continue
            key_to_row[key_val] = idx
    update_requests = []
    append_values = []
    for obj in data_to_upsert:
        key_val = str(obj.get(key_column, "")).strip()
        if key_val is None:
            continue
        row_values = [obj.get(h, "") for h in headers]
        if key_val in key_to_row:
            row_number = key_to_row[key_val]
            rng = f"{sheet_name}!A{row_number}:{chr(65+len(headers)-1)}{row_number}"
            update_requests.append({
                'range': rng,
                'values': [row_values]
            })
        else:
            append_values.append(row_values)
    for req in update_requests:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=req['range'],
            valueInputOption='RAW',
            body={'values': req['values']}
        ).execute()
    if append_values:
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': append_values}
        ).execute()
    return {
        'updated': len(update_requests),
        'inserted': len(append_values),
        'total': len(data_to_upsert)
    }

@router.route("/execute", methods=["GET", "POST"])
def execute():
    logger.info("=== UPSERT EXECUTE START ===")
    try:
        request_obj = Request(flask_request)
        data = request_obj.data
        form_data = data.get("form_data", data)
        spreadsheet_id = form_data.get("spreadsheet_id")
        sheet_name = form_data.get("sheet_name")
        key_column = form_data.get("key_column")
        data_to_upsert_raw = form_data.get("data_to_upsert", "")
        confirm_upsert = form_data.get("confirm_upsert", False)
        if not spreadsheet_id:
            return Response(data={"error": "Spreadsheet ID is required"}, metadata={"status": "error"})
        if not sheet_name:
            return Response(data={"error": "Sheet name is required"}, metadata={"status": "error"})
        if not key_column:
            return Response(data={"error": "Key column is required"}, metadata={"status": "error"})
        if not data_to_upsert_raw:
            return Response(data={"error": "Data to upsert is required"}, metadata={"status": "error"})
        if not confirm_upsert:
            return Response(data={"error": "You must confirm the upsert by checking the confirmation box"}, metadata={"status": "error"})
        try:
            data_to_upsert = parse_data_to_upsert(data_to_upsert_raw)
        except Exception as e:
            return Response(data={"error": str(e)}, metadata={"status": "error"})
        try:
            service = get_google_sheets_service()
            result = upsert_rows(service, spreadsheet_id, sheet_name, key_column, data_to_upsert)
        except Exception as e:
            logger.error(f"Upsert error: {e}")
            return Response(data={"error": str(e)}, metadata={"status": "error"})
        return Response(
            data={
                "message": f"Upsert complete: {result['updated']} updated, {result['inserted']} inserted.",
                "updated": result['updated'],
                "inserted": result['inserted'],
                "total": result['total']
            },
            metadata={"status": "success"}
        )
    except Exception as e:
        logger.error(f"Unexpected error in upsert execute: {e}")
        logger.error(traceback.format_exc())
        return Response(data={"error": f"Unexpected error: {str(e)}"}, metadata={"status": "error"})

@router.route("/content", methods=["GET", "POST"])
def content():
    return Response(
        data={
            "message": "UPSERT module content endpoint",
            "description": "This endpoint is not used for the UPSERT module"
        },
        metadata={"status": "success"}
    ) 