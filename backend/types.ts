/**
 * TypeScript type definitions for Visionaree API
 */

// Request types
export interface PresignedUrlRequest {
  filename: string;
  contentType?: string;
}

// Response types
export interface PresignedUrlResponse {
  presignedUrl: string;
  key: string;
  bucket: string;
  expiresIn: number;
}

export interface ApiErrorResponse {
  error: string;
  message: string;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
}

// Lambda event types
export interface LambdaEvent {
  httpMethod: string;
  body?: string;
  headers?: Record<string, string>;
  queryStringParameters?: Record<string, string>;
  pathParameters?: Record<string, string>;
}

export interface LambdaContext {
  functionName: string;
  functionVersion: string;
  invokedFunctionArn: string;
  memoryLimitInMB: string;
  awsRequestId: string;
  logGroupName: string;
  logStreamName: string;
  getRemainingTimeInMillis(): number;
}

export interface LambdaResponse {
  statusCode: number;
  headers?: Record<string, string>;
  body: string;
}

// S3 configuration
export interface S3Config {
  bucketName: string;
  region: string;
  allowedFileTypes: string[];
  maxFileSize: number;
  presignedUrlExpiration: number;
}

// API configuration
export interface ApiConfig {
  baseUrl: string;
  endpoints: {
    presignedUrl: string;
    health: string;
  };
}

// Error types
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class S3Error extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'S3Error';
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorCode?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}