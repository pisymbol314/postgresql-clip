#!/usr/bin/env python3

import os
import io
from pathlib import Path

import clip
import psycopg
import torch
import boto3
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
SERVICE_URI = os.getenv("PG_SERVICE_URI")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize S3 client
s3 = boto3.client('s3',
                  endpoint_url=S3_ENDPOINT,
                  aws_access_key_id=S3_ACCESS_KEY,
                  aws_secret_access_key=S3_SECRET_KEY)

# Load the CLIP model (unchanged)
LOCAL_MODEL = Path('./models/ViT-B-32.pt').absolute()
MODEL_NAME = 'ViT-B/32'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if LOCAL_MODEL.exists():
    print(f'Importing CLIP model {MODEL_NAME} from {LOCAL_MODEL.parent}')
    print(f'Using {DEVICE}')
    model, preprocess = clip.load(MODEL_NAME, device=DEVICE, download_root=LOCAL_MODEL.parent)
else:
    print(f'Importing CLIP model {MODEL_NAME}')
    print(f'Using {DEVICE}')
    model, preprocess = clip.load(MODEL_NAME, device=DEVICE)

batch_size = 100

def compute_clip_features(image_objects):
    photos = [Image.open(io.BytesIO(obj['Body'].read())) for obj in image_objects]
    photos_preprocessed = torch.stack([preprocess(photo) for photo in photos]).to(DEVICE)
    with torch.no_grad():
        photos_features = model.encode_image(photos_preprocessed)
        photos_features /= photos_features.norm(dim=-1, keepdim=True)
    return photos_features.cpu().numpy()

def index_embeddings_to_postgres(data):
    try:
        with psycopg.connect(SERVICE_URI) as conn:
            with conn.cursor() as cur:
                with cur.copy('COPY pictures (filename, embedding) FROM STDIN') as copy:
                    for row in data:
                        copy.write_row(row)
    except Exception as exc:
        print(f'{exc.__class__.__name__}: {exc}')

def vector_to_string(embedding):
    vector_str = ", ".join(str(x) for x in embedding.tolist())
    return f'[{vector_str}]'

# List all objects in the S3 bucket
response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME)
all_objects = response.get('Contents', [])

data = []

for i in range(0, len(all_objects), batch_size):
    print(f'Batch {i}')
    batch_objects = all_objects[i:i+batch_size]
    
    # Get the image objects from S3
    image_objects = [s3.get_object(Bucket=S3_BUCKET_NAME, Key=obj['Key']) for obj in batch_objects]
    
    # Compute embeddings
    batch_embeddings = compute_clip_features(image_objects)
    
    # Create data for indexing
    for obj, embedding in zip(batch_objects, batch_embeddings):
        data.append((obj['Key'], vector_to_string(embedding)))
    
    # Index if we have enough data
    if len(data) >= batch_size:
        index_embeddings_to_postgres(data)
        data = []

# Index any remaining data
if data:
    print('Remaining embeddings')
    index_embeddings_to_postgres(data)

print("All embeddings indexed successfully.")