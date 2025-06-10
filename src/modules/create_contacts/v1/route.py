import json
from typing import Dict, Any, List

from flask import  request as flask_request
from workflows_cdk import Response, Request, ManagedError
from main import router


@router.route("/content", methods=["POST"])
def content():
    """
    Provide dynamic content for the module UI.
    Fetches available object types and fields based on the CRM connection.
    """
    try:
        # Parse the request
        request = Request(flask_request)
        data = request.data

        if not data:
            return Response(data={"message": "Missing request data"}, status_code=400)
            
        form_data = data.get("form_data", {})
        content_object_names = data.get("content_object_names", [])
        
        # Extract content object names from objects if needed
        if isinstance(content_object_names, list) and content_object_names and isinstance(content_object_names[0], dict):
            content_object_names = [obj.get("id") for obj in content_object_names if "id" in obj]
        
        # Get connection type
        credentials = request.credentials
        connection_data = credentials.get("connection_data", {})
        connection_type = connection_data.get("connection_app_type", "").lower()
        
        # Process content objects
        content_objects = []
        
        for content_name in content_object_names:
            # Object types (Contact, Lead, etc.)
            if content_name == "object_types":
                # Simple mock data - in a real implementation, this would query the CRM API
                if connection_type == "salesforce":
                    object_types = [
                        {"value": {"id": "Contact", "label": "Contact"}, "label": "Contact"},
                        {"value": {"id": "Lead", "label": "Lead"}, "label": "Lead"}
                    ]
                else:
                    object_types = [
                        {"value": {"id": "Contact", "label": "Contact"}, "label": "Contact"},
                        {"value": {"id": "Lead", "label": "Lead"}, "label": "Lead"}
                    ]
                
                content_objects.append({
                    "content_object_name": "object_types",
                    "data": object_types
                })
                
            # Fields for the selected object type
            elif content_name == "fields":
                # Get the selected object type from form data
                object_type = form_data.get("object_type", {})
                if isinstance(object_type, dict):
                    object_type = object_type.get("id", "Contact")
                else:
                    object_type = "Contact"
                
                # Simple mock field data
                fields = [
                    {"id": "FirstName", "label": "First Name", "type": "string", "required": True},
                    {"id": "LastName", "label": "Last Name", "type": "string", "required": True},
                    {"id": "Email", "label": "Email", "type": "string", "required": True},
                    {"id": "Phone", "label": "Phone", "type": "string", "required": False}
                ]
                
                content_objects.append({
                    "content_object_name": "fields",
                    "data": fields
                })
        
        return Response(data={"content_objects": content_objects})
        
    except Exception as e:
        return Response.error(str(e))

@router.route("/execute", methods=["POST"])
def execute():
    """
    Execute the create contacts operation based on provided parameters.
    """
    try:
        # Parse the request
        request = Request(flask_request)
      
        data = request.data
    
        # Validate required parameters
        if not data:
            raise ManagedError("Missing request parameters")
        
        if not data.get("crm_connection"):
            raise ManagedError("Missing CRM connection parameter")
        
        # Parse contacts data
        contacts_data = data.get("contacts_data", "[]")
        try:
            contacts = json.loads(contacts_data) if isinstance(contacts_data, str) else contacts_data
        except json.JSONDecodeError:
            raise ManagedError("Invalid JSON format in contacts_data")
            
        if not isinstance(contacts, list) or not contacts:
            raise ManagedError("No valid contacts provided for creation")
        
        # Prepare results
        successful_creations = []
        failed_creations = []
        
        # Process contacts
        for i, contact in enumerate(contacts):
            # Basic validation - ensure email is present
            if not contact.get("Email"):
                failed_creations.append({
                    "contact_data": contact,
                    "error": "Missing Email field"
                })
                continue
                
            # Simple duplicate check for example.com emails
            if "@example.com" in contact.get("Email", ""):
                failed_creations.append({
                    "contact_data": contact,
                    "error": "Duplicate contact found",
                    "existing_record": {
                        "Id": f"EXISTING{i}",
                        "Email": contact["Email"]
                    }
                })
                continue
            
            # Simulate contact creation - alternating success/failure
            if i % 2 == 0:
                successful_creations.append({
                    "contact_data": contact,
                    "created_id": f"ID{i:0>8}",
                    "status": "success"
                })
            else:
                failed_creations.append({
                    "contact_data": contact,
                    "error": "Simulated API error",
                    "status": "error"
                })
        successful_creations = [{"ciao": "ciao"}]
        # Return results
        return Response(
            data=successful_creations,
            metadata={
                "affected_records": len(successful_creations),
                "message": f"Created {len(successful_creations)} contacts, {len(failed_creations)} failed",
                "failed_creations": failed_creations
            }
        )
        
    except ManagedError as e:
        return Response.error(str(e))
    except Exception as e:
        return Response.error(str(e)) 