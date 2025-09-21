#!/bin/bash

# Visionaree Full Stack Deployment Script
# This script deploys both frontend and backend CDK stacks

set -e

echo "🚀 Deploying Visionaree Full Stack Infrastructure..."

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

# Install CDK dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing CDK dependencies..."
    npm install
fi

# Build the frontend first
echo "🏗️  Building frontend..."
cd ../frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    pnpm install
fi
echo "🔨 Generating static frontend..."
pnpm generate
cd ../infra

# Build the TypeScript CDK code
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

# Deploy the backend stack first
echo "🚀 Deploying backend stack..."
npx cdk deploy VisionareeBackendStack --require-approval never

# Deploy the frontend stack
echo "🚀 Deploying frontend stack..."
npx cdk deploy VisionareeFrontendStack --require-approval never

# Get outputs from both stacks
echo "📋 Getting stack outputs..."
API_URL=$(aws cloudformation describe-stacks \
    --stack-name VisionareeBackendStack \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name VisionareeBackendStack \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text)

WEBSITE_URL=$(aws cloudformation describe-stacks \
    --stack-name VisionareeFrontendStack \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' \
    --output text)

CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
    --stack-name VisionareeFrontendStack \
    --query 'Stacks[0].Outputs[?OutputKey==`DistributionDomainName`].OutputValue' \
    --output text)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Stack Information:"
echo "  🌐 Frontend Website URL: $WEBSITE_URL"
echo "  ☁️  CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "  🔗 API Gateway URL: $API_URL"
echo "  📦 S3 Video Bucket: $BUCKET_NAME"
echo "  🔗 Presigned URL Endpoint: ${API_URL}presigned-url"
echo "  ❤️  Health Check Endpoint: ${API_URL}health"
echo ""
echo "🧪 Test the deployment:"
echo "  Frontend: $WEBSITE_URL"
echo "  API Health: curl $API_URL/health"
echo ""
echo "📝 Frontend environment variables:"
echo "  API_BASE_URL=$API_URL"
echo "  S3_BUCKET_NAME=$BUCKET_NAME"