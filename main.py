import os
import uuid
from typing import List

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import local modules
import models
from database import engine, get_db, create_db_and_tables

# Create database tables on startup
create_db_and_tables()

app = FastAPI(title="GolfStatIQ Contributor API")

# --- CORS Middleware ---
# Allows the standalone HTML file to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null", "file://"], # "null" or "file://" for local HTML files
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- S3 Configuration ---
# Fetch from environment variables for security
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-golfstatiq-bucket-name")
s3_client = boto3.client("s3")


@app.post("/api/v1/contribute/upload", status_code=status.HTTP_201_CREATED)
async def create_upload_files(
    db: Session = Depends(get_db),
    files: List[UploadFile] = File(...),
    email: str = Form(...)
):
    """
    Handles the file upload and contributor registration.
    """
    # 1. Validate email (basic validation)
    if "@" not in email or "." not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required."
        )

    # 2. Handle File Uploads to S3
    for file in files:
        # Generate a unique filename to prevent collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        s3_key = f"contributor-uploads/{email}/{unique_filename}"

        try:
            # Stream the file directly to S3
            s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, s3_key)
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during file upload. Please try again."
            )
        finally:
            # Important: Close the file object
            file.file.close()

    # 3. Database Interaction
    try:
        # Check if contributor already exists
        db_contributor = db.query(models.Contributor).filter(models.Contributor.email == email).first()

        # If not, create a new entry
        if not db_contributor:
            new_contributor = models.Contributor(email=email)
            db.add(new_contributor)
            db.commit()
            db.refresh(new_contributor)
    except Exception as e:
        print(f"Database error: {e}")
        # Note: In a real app, you might want to handle the case where files were
        # uploaded but the DB write failed (e.g., add to a cleanup queue).
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save contributor information."
        )

    return {"message": f"Success! Thank you, {email}. Your files have been uploaded."}