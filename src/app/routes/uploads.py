import uuid

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.models import Resource, User
from app.schemas import PresignedUrlRequest, PresignedUrlResponse
from app.utils.dependencies import require_admin
from config import Config

router = APIRouter()


def _s3_client():
    return boto3.client(
        "s3",
        region_name=Config.AWS_REGION,
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        config=BotocoreConfig(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
        ),
    )


@router.post(
    "/{resource_id}/image",
    response_model=PresignedUrlResponse,
    status_code=200,
    responses={
        404: {"description": "Resource not found"},
        403: {"description": "Admin access required"},
    },
)
@limiter.limit("30/hour")
async def get_image_upload_url(
    resource_id: int,
    request: Request,
    body: PresignedUrlRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Resource).filter_by(id=resource_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resource not found")

    ext = body.filename.rsplit(".", 1)[-1] if "." in body.filename else "jpg"
    key = f"resources/{resource_id}/{uuid.uuid4()}.{ext}"

    try:
        s3 = _s3_client()
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": Config.S3_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=Config.S3_PRESIGNED_URL_EXPIRY,
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL") from e

    object_url = f"https://{Config.S3_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/{key}"

    return PresignedUrlResponse(
        upload_url=upload_url,
        object_url=object_url,
        key=key,
        expires_in=Config.S3_PRESIGNED_URL_EXPIRY,
    )
