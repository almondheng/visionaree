#!/bin/bash

# Visionaree Backend Deployment Script
# This script deploys the CDK stack for the video upload API

set -e

echo "🚀 Deploying Visionaree Backend Infrastructure..."

# Check if we're in the correct directory
if [ ! -f "cdk.json" ]; then
    echo "❌ Error: cdk.json not found. Please run this script from the infra directory."
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Error: AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing CDK dependencies..."
    npm install
fi

# Build the TypeScript code
echo "🔨 Building CDK code..."
npm run build

# Bootstrap CDK if needed (only run once per account/region)
echo "🏗️  Checking CDK bootstrap..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit > /dev/null 2>&1; then
    echo "🔧 Bootstrapping CDK..."
    npx cdk bootstrap
else
    echo "✅ CDK already bootstrapped"
fi

# Deploy the stack
echo "🚀 Deploying backend stack..."
npx cdk deploy VisionareeBackendStack --require-approval never

# Get outputs
echo "📋 Getting stack outputs..."
API_URL=$(aws cloudformation describe-stacks \
    --stack-name VisionareeBackendStack \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name VisionareeBackendStack \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Stack Information:"
echo "  API Gateway URL: $API_URL"
echo "  S3 Bucket Name: $BUCKET_NAME"
echo "  Presigned URL Endpoint: ${API_URL}presigned-url"
echo "  Health Check Endpoint: ${API_URL}health"
echo ""
echo "🧪 Test the API:"
echo "  curl $API_URL/health"
echo ""
echo "📝 Update your frontend configuration with:"
echo "  API_BASE_URL=$API_URL"
echo "  S3_BUCKET_NAME=$BUCKET_NAME"