# Visionaree

AI-powered video understanding with a Nuxt 3 frontend and a fully serverless AWS backend (API Gateway, Lambda, S3, DynamoDB, Bedrock).

## What’s in this repo

- `frontend/` — Nuxt 3 application (upload UI, video player, Q&A chat)
- `backend/` — Lambda handlers (S3 event processing, video query, job status, presigned URL)
- `infra/` — AWS CDK TypeScript stack (API, Lambdas, S3 buckets, DynamoDB tables, permissions)
- `API_DOCUMENTATION.md` — Detailed API reference (routes, bodies, examples)

An architecture diagram is available in `backend/architecture.drawio`.

## High-level architecture

1. User uploads a video from the web UI. The app requests a presigned URL, then uploads directly to S3.
2. An S3 event triggers a Lambda that segments the video with FFmpeg (via a Lambda layer), summarizes segments with Amazon Bedrock, and stores captions/results in DynamoDB. Segments are written to a dedicated segments bucket.
3. The UI can query insights for a video job via API. A job status endpoint is exposed to allow polling until processing is complete.

Key services:
- Amazon S3: uploads bucket + separate segments bucket
- AWS Lambda: presigned URL handler, S3 event processor, video query handler, job status handler
- Amazon DynamoDB: analysis table and job status table
- Amazon Bedrock: model invocation for segment captioning and query insights

## Prerequisites

- Node.js 18+ and `pnpm` (or npm/yarn)
- AWS account and credentials configured locally
- AWS CDK v2 (`npm i -g aws-cdk`)
- Python 3.11 for Lambda packaging (managed by CDK; no local server needed)

## Deploy the backend (CDK)

1) Install dependencies

```bash
cd infra
npm install
```

2) Bootstrap your AWS environment (first time per account/region)

```bash
npx cdk bootstrap
```

3) Build and deploy

```bash
npm run build
npx cdk deploy
```

After deploy, note the stack outputs (API URL, uploads/segments bucket names, etc.).

## Configure and run the frontend

1) Set the API URL used by the frontend requests. Currently this is a constant in `frontend/app/lib/video-service.ts`:

- Update `API_BASE_URL` to your deployed API Gateway URL (e.g. `https://xxxx.execute-api.us-east-1.amazonaws.com/prod`).

2) Install and run

```bash
cd ../frontend
pnpm install
pnpm dev
```

Visit `http://localhost:3000`.

## Core features

- Upload to S3 via presigned URL
- Serverless video segmentation using FFmpeg in Lambda
- Segment captioning and insights powered by Amazon Bedrock
- Separate segments S3 bucket for generated parts
- Job status tracking in DynamoDB with a simple GET status endpoint
- Nuxt 3 UI for uploading, viewing, and querying videos

## API summary

See `API_DOCUMENTATION.md` for full details. Main routes:

- `POST /presigned-url` — Request a presigned URL to upload a video
- `GET /video/{jobId}/status` — Poll job status: `{ "status": "pending|processing|done|error" }`
- `POST /video/{jobId}/ask` — Ask a question about the analyzed video; returns AI insights and filtered segments
- `GET /health` — Health check

Note: The query endpoint reads the prompt from the JSON body as `{ "query": "..." }` and returns only AI analysis data (insights and relevant segments).

## Implementation notes

- FFmpeg is provided via a Lambda layer (configured in the CDK stack).
- The S3 event processor limits Bedrock concurrency (ThreadPoolExecutor) for reliability.
- A dedicated segments S3 bucket stores generated segment files (bucket name is passed to the processor Lambda via `SEGMENTS_BUCKET_NAME`).
- DynamoDB serialization uses a custom encoder to handle Decimals where needed.
- IAM permissions for `bedrock:InvokeModel` are granted to the query handler Lambda via the CDK stack.

## Troubleshooting

- Bedrock AccessDenied: ensure the Lambda role includes `bedrock:InvokeModel` for the target model/region.
- 403/CORS issues in the browser: verify API Gateway CORS settings and allowed origins.
- Processing appears stuck: check CloudWatch logs for the S3 event processor Lambda; verify S3 event notifications are correctly wired.
- Large files: Lambda timeouts or memory may need tuning; segmenting is done in parts to keep within limits.

## Development tips

- Frontend: Nuxt 3 with `pnpm dev` for hot reload. UI components are under `frontend/app/components`.
- Backend: Lambdas live in `backend/`. They are packaged/deployed by the CDK stack in `infra/`.
- Infra: The CDK app is in `infra/lib/backend-stack.ts`. Update environment variables, permissions, and wiring here.
