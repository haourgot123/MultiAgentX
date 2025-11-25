#!/usr/bin/env bash
 
ENV_FILE=".env"
 
echo "Loading environment variables from $ENV_FILE..."
 
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found!"
  exit 1
fi
 
set -o allexport
 
source "$ENV_FILE"
 
set +o allexport
 
echo "Environment variables loaded."

echo "S3_ACCESS_KEY_ID = $S3_ACCESS_KEY_ID"
echo "DB_HOST = $DB_HOST"
echo "DB_PORT = $DB_PORT"
echo "DB_USER = $DB_USER"
echo "DB_PASS = $DB_PASS"
echo "DB_DATABASE = $DB_DATABASE"
echo "DB_NAME = $DB_NAME"
echo "QDRANT_HOST = $QDRANT_HOST"
echo "QDRANT_PORT = $QDRANT_PORT"
echo "OPENAI_API_KEY = $OPENAI_API_KEY"
echo "OPENROUTER_API_KEY = $OPENROUTER_API_KEY"
echo "AZURE_DOCUMENT_INTELLIGENCE_KEY = $AZURE_DOCUMENT_INTELLIGENCE_KEY"
echo "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = $AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
echo "WAIT_FOR_DB = $WAIT_FOR_DB"
echo "PRINT_ENV_ON_LOAD = $PRINT_ENV_ON_LOAD"
echo "IMAGE_NAME = $IMAGE_NAME"
echo "IMAGE_TAG = $IMAGE_TAG"
echo "REDIS_URL = $REDIS_URL"
echo "REDIS_PORT = $REDIS_PORT"
echo "BE_CALLBACK_API_URL = $BE_CALLBACK_API_URL"
echo "FLOWER_PORT = $FLOWER_PORT"
echo "TAVILY_API_KEY = $TAVILY_API_KEY"
 
 
 
echo "Running development server..."
 
python -m main