import json
import boto3
import base64
import os
from datetime import datetime
import uuid  # To generate unique feedback IDs

# Configurable variables with defaults from environment variables
TABLE_NAME = os.environ.get('TABLE_NAME', 'Feedback-Kobina')  # DynamoDB Table name for storing feedback
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'feedback-images-kobbyjust')  # S3 bucket name for storing feedback attachments
# ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'sagarinokoeaws1@gmail.com')  # Admin email to receive notifications
REGION = os.environ.get('REGION', 'us-east-1')  # AWS region for resources

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)  # DynamoDB client to interact with the database
s3 = boto3.client('s3', region_name=REGION)  # S3 client to interact with the bucket for file uploads
# ses = boto3.client('ses', region_name=REGION)  # SES client to send emails

def lambda_handler(event, context):
    # Log the incoming event for debugging purposes
    print("Event received:", json.dumps(event))

    # CORS support for OPTIONS pre-flight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            }
        }

    try:
        # Check if the event has a 'body' field (standard API Gateway payload)
        if 'body' in event:
            body = json.loads(event['body'])  # Parse the incoming body
        # If not, check if the event has fields directly (for custom events)
        elif 'name' in event and 'email' in event:
            body = event  # Use the event data as body
        else:
            return {
                'statusCode': 400,
                'headers': { 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps({ 'message': 'Invalid request format.' })
            }

        # Extract individual fields from the parsed body
        feedback_id = str(uuid.uuid4())  # Generate a unique ID for the feedback
        name = body.get('name')  # Extract name
        email = body.get('email')  # Extract email
        message = body.get('message')  # Extract message
        file_base64 = body.get('file_base64')  # Extract base64 encoded image (optional)

        file_url = None  # Default to None in case no file is provided
        if file_base64:
            # Generate a unique key for the file based on feedback ID
            key = f"{feedback_id}.pdf"

            # Decode the base64-encoded file data
            pdf_data = base64.b64decode(file_base64.split(',')[-1])

            # Upload the decoded file to S3
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=pdf_data,
                ContentType='application/pdf'
            )

            # Generate a pre-signed URL for the uploaded file to be accessed for 24 hours
            file_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': key},
                ExpiresIn=86400  # URL expires in 24 hours
            )
            
        # Store the feedback data in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            'feedback_id': feedback_id,  # Unique feedback ID
            'name': name,  # User's name
            'email': email,  # User's email
            'message': message,  # User's feedback message
            'file_url': file_url,  # Link to the uploaded file (if any)
            'timestamp': datetime.utcnow().isoformat()  # Timestamp of the feedback submission
        })

     return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({'message': 'Feedback submitted successfully'})
        }

    except Exception as e:
        # Log the error for debugging
        print("Error occurred:", str(e))
        # Return an error response
        return {
            'statusCode': 500,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({ 'message': 'Internal server error', 'error': str(e) })
        }
