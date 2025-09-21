import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';

export class BackendStack extends cdk.Stack {
  public readonly s3Bucket: s3.Bucket;
  public readonly presignedUrlFunction: lambda.Function;
  public readonly s3EventProcessor: lambda.Function;
  public readonly api: apigateway.RestApi;
  public readonly videoAnalysisTable: dynamodb.Table;
  public readonly jobStatusTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create S3 bucket for video uploads
    this.s3Bucket = new s3.Bucket(this, 'VisionareeBucket', {
      bucketName: `visionaree-videos-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Keep bucket on stack deletion
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.DELETE,
            s3.HttpMethods.HEAD
          ],
          allowedOrigins: ['*'], // Configure for your domain in production
          allowedHeaders: ['*'],
          exposedHeaders: ['ETag'],
          maxAge: 3000
        }
      ],
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: false,
      lifecycleRules: [
        {
          id: 'DeleteOldVideos',
          enabled: true,
          expiration: cdk.Duration.days(30), // Auto-delete videos after 30 days
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1)
        }
      ]
    });

    // Create DynamoDB table for video analysis results
    this.videoAnalysisTable = new dynamodb.Table(this, 'VideoAnalysisTable', {
      tableName: `visionaree-video-analysis-${this.account}-${this.region}`,
      partitionKey: {
        name: 'jobIdPartitionId',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'segmentStartTime',
        type: dynamodb.AttributeType.NUMBER
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Keep table on stack deletion
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // Create DynamoDB table for job status tracking
    this.jobStatusTable = new dynamodb.Table(this, 'JobStatusTable', {
      tableName: `visionaree-job-status-${this.account}-${this.region}`,
      partitionKey: {
        name: 'jobId',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'uploadTimestamp',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Keep table on stack deletion
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // Add Global Secondary Index for querying by status
    this.jobStatusTable.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: {
        name: 'status',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'uploadTimestamp',
        type: dynamodb.AttributeType.STRING
      }
    });


    // Create Lambda function for generating presigned URLs
    this.presignedUrlFunction = new lambda.Function(this, 'PresignedUrlFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend')),
      handler: 'presigned_url_handler.lambda_handler',
      environment: {
        S3_BUCKET_NAME: this.s3Bucket.bucketName
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      description: 'Generate presigned URLs for S3 video uploads'
    });

    // Create Lambda function for processing S3 upload events
    this.s3EventProcessor = new lambda.Function(this, 'S3EventProcessor', {
      runtime: lambda.Runtime.PYTHON_3_11,
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend')),
      handler: 's3_event_processor.lambda_handler',
      environment: {
        S3_BUCKET_NAME: this.s3Bucket.bucketName,
        DYNAMODB_TABLE_NAME: this.videoAnalysisTable.tableName,
        JOB_STATUS_TABLE_NAME: this.jobStatusTable.tableName
      },
      timeout: cdk.Duration.minutes(10), // Increased timeout for FFmpeg processing
      memorySize: 2048, // Increased memory for video processing with FFmpeg
      description: 'Process S3 upload events for video files using FFmpeg',
      layers: [
        // FFmpeg Lambda layer for video processing
        lambda.LayerVersion.fromLayerVersionArn(
          this,
          'FFmpegLayer',
          'arn:aws:lambda:us-east-1:319237335445:layer:ffmpeg:1'
        )
      ]
    });

    // Grant Lambda function permissions to generate presigned URLs for the S3 bucket
    this.s3Bucket.grantPut(this.presignedUrlFunction);
    this.s3Bucket.grantRead(this.presignedUrlFunction);

    // Grant S3 event processor permissions to read from S3 bucket
    this.s3Bucket.grantRead(this.s3EventProcessor);
    this.s3Bucket.grantWrite(this.s3EventProcessor); // For writing processed files back to S3

    // Grant S3 event processor permissions to write to DynamoDB table
    this.videoAnalysisTable.grantWriteData(this.s3EventProcessor);

    // Grant S3 event processor permissions to write to job status table
    this.jobStatusTable.grantWriteData(this.s3EventProcessor);

    // Additional IAM permissions for presigned URL generation
    this.presignedUrlFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:PutObject',
          's3:PutObjectAcl',
          's3:GetObject'
        ],
        resources: [
          this.s3Bucket.bucketArn,
          `${this.s3Bucket.bucketArn}/*`
        ]
      })
    );

    // Additional IAM permissions for S3 event processor
    this.s3EventProcessor.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:GetObject',
          's3:GetObjectMetadata',
          's3:PutObject',
          's3:PutObjectAcl',
          's3:DeleteObject'
        ],
        resources: [
          this.s3Bucket.bucketArn,
          `${this.s3Bucket.bucketArn}/*`
        ]
      })
    );

    // Grant S3 event processor permissions to invoke Bedrock models
    this.s3EventProcessor.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'bedrock:*'
        ],
        resources: ["*"]
      })
    );

    // Create API Gateway
    this.api = new apigateway.RestApi(this, 'VisionareeApi', {
      restApiName: 'Visionaree Video Upload API',
      description: 'API for video upload and analysis',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS, // Configure for your domain in production
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token'
        ]
      },
      deployOptions: {
        stageName: 'prod'
      }
    });

    // Create API Gateway integration with Lambda
    const presignedUrlIntegration = new apigateway.LambdaIntegration(
      this.presignedUrlFunction,
      {
        requestTemplates: { 'application/json': '{ "statusCode": "200" }' }
      }
    );

    // Add /presigned-url resource
    const presignedUrlResource = this.api.root.addResource('presigned-url');
    presignedUrlResource.addMethod('POST', presignedUrlIntegration, {
      authorizationType: apigateway.AuthorizationType.NONE,
      requestValidator: new apigateway.RequestValidator(this, 'RequestValidator', {
        restApi: this.api,
        validateRequestBody: true,
        validateRequestParameters: false
      }),
      requestModels: {
        'application/json': new apigateway.Model(this, 'PresignedUrlRequestModel', {
          restApi: this.api,
          contentType: 'application/json',
          schema: {
            type: apigateway.JsonSchemaType.OBJECT,
            properties: {
              filename: {
                type: apigateway.JsonSchemaType.STRING,
                minLength: 1
              },
              jobId: {
                type: apigateway.JsonSchemaType.STRING,
                minLength: 1,
                pattern: '^[a-zA-Z0-9_-]+$'
              },
              contentType: {
                type: apigateway.JsonSchemaType.STRING,
                pattern: '^video\/'
              }
            },
            required: ['filename', 'jobId']
          }
        })
      }
    });

    // Add health check endpoint
    const healthResource = this.api.root.addResource('health');
    healthResource.addMethod('GET', new apigateway.MockIntegration({
      integrationResponses: [
        {
          statusCode: '200',
          responseTemplates: {
            'application/json': '{"status": "healthy", "timestamp": "$context.requestTime"}'
          }
        }
      ],
      requestTemplates: {
        'application/json': '{"statusCode": 200}'
      }
    }), {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigateway.Model.EMPTY_MODEL
          }
        }
      ]
    });

    // Configure S3 bucket to send upload events to the processor Lambda
    this.s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventProcessor),
      {
        prefix: 'videos/', // Only trigger for files in the videos/ directory
        suffix: '.mp4'     // Only trigger for video files (add more extensions as needed)
      }
    );

    // Also trigger for other video formats
    this.s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventProcessor),
      {
        prefix: 'videos/',
        suffix: '.mov'
      }
    );

    this.s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventProcessor),
      {
        prefix: 'videos/',
        suffix: '.avi'
      }
    );

    this.s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventProcessor),
      {
        prefix: 'videos/',
        suffix: '.mkv'
      }
    );

    this.s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.s3EventProcessor),
      {
        prefix: 'videos/',
        suffix: '.webm'
      }
    );

    // Output important values
    new cdk.CfnOutput(this, 'S3BucketName', {
      value: this.s3Bucket.bucketName,
      description: 'Name of the S3 bucket for video uploads'
    });

    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: this.api.url,
      description: 'API Gateway URL'
    });

    new cdk.CfnOutput(this, 'PresignedUrlEndpoint', {
      value: `${this.api.url}presigned-url`,
      description: 'Presigned URL generation endpoint'
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: this.presignedUrlFunction.functionName,
      description: 'Name of the presigned URL Lambda function'
    });

    new cdk.CfnOutput(this, 'S3EventProcessorName', {
      value: this.s3EventProcessor.functionName,
      description: 'Name of the S3 event processor Lambda function'
    });

    new cdk.CfnOutput(this, 'DynamoDBTableName', {
      value: this.videoAnalysisTable.tableName,
      description: 'Name of the DynamoDB table for video analysis results'
    });

    new cdk.CfnOutput(this, 'JobStatusTableName', {
      value: this.jobStatusTable.tableName,
      description: 'Name of the DynamoDB table for job status tracking'
    });
  }
}
