#!/usr/bin/env python3

import logging
import os
from pathlib import Path

import clip
import psycopg
import torch
import boto3
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

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
    logger.info(f'Importing CLIP model from {LOCAL_MODEL}')
    logger.info(f'Using {DEVICE}')
    model, preprocess = clip.load(MODEL_NAME, device=DEVICE, download_root=LOCAL_MODEL.parent)
else:
    logger.info('Importing CLIP model')
    logger.info(f'Using {DEVICE}')
    model, preprocess = clip.load(MODEL_NAME, device=DEVICE)

def get_single_embedding(text):
    with torch.no_grad():
        text_input = clip.tokenize([text]).to(DEVICE)
        text_features = model.encode_text(text_input)
        text_features /= text_features.norm(dim=-1, keepdim=True)
    return text_features.cpu().numpy()[0]

def vector_to_string(embedding):
    vector_str = ", ".join(str(x) for x in embedding.tolist())
    return f'[{vector_str}]'

def search_for_matches(text):
    vector = get_single_embedding(text)
    embedding_string = vector_to_string(vector)
    try:
        with psycopg.connect(SERVICE_URI) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM pictures ORDER BY embedding <-> %s LIMIT 4;",
                    (embedding_string,),
                )
                rows = cur.fetchall()
                return [row[0] for row in rows]
    except Exception as exc:
        print(f'{exc.__class__.__name__}: {exc}')
        return []

text_input = "man jumping"  # Provide your text input here
logger.info(f'Searching for {text_input!r}')
matches = search_for_matches(text_input)

for index, filename in enumerate(matches):
    print(f'{index+1}: {filename}')
    # Generate a presigned URL for the image (valid for 1 hour)
    url = s3.generate_presigned_url('get_object',
                                    Params={'Bucket': S3_BUCKET_NAME, 'Key': filename},
                                    ExpiresIn=3600)
    print(f'   URL: {url}')
