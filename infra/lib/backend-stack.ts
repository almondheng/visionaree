import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as path from 'path';

export class BackendStack extends cdk.Stack {
  public readonly s3Bucket: s3.Bucket;
  public readonly presignedUrlFunction: lambda.Function;
  public readonly api: apigateway.RestApi;

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

    // Grant Lambda function permissions to generate presigned URLs for the S3 bucket
    this.s3Bucket.grantPut(this.presignedUrlFunction);
    this.s3Bucket.grantRead(this.presignedUrlFunction);

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
  }
}
