import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as iam from 'aws-cdk-lib/aws-iam';

export interface SocialListeningStackProps extends cdk.StackProps {
  novaModelId?: string;
}

export class SocialListeningStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: SocialListeningStackProps) {
    super(scope, id, props);

    // ==============================================
    // DynamoDB Tables
    // ==============================================
    
    const postsTable = new dynamodb.Table(this, 'PostsTable', {
      tableName: 'social-listening-posts',
      partitionKey: { name: 'postId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.NUMBER },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const sentimentTable = new dynamodb.Table(this, 'SentimentTable', {
      tableName: 'social-listening-sentiment',
      partitionKey: { name: 'postId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ==============================================
    // S3 Bucket
    // ==============================================
    
    const dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: `social-listening-data-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ==============================================
    // IAM Role for Lambda
    // ==============================================
    
    const lambdaRole = new iam.Role(this, 'LambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
      inlinePolicies: {
        BedrockPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
              ],
              resources: [
                `arn:aws:bedrock:${this.region}::foundation-model/*`,
              ],
            }),
          ],
        }),
        DynamoDBPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'dynamodb:GetItem',
                'dynamodb:PutItem',
                'dynamodb:Query',
                'dynamodb:Scan',
                'dynamodb:UpdateItem',
              ],
              resources: [
                postsTable.tableArn,
                sentimentTable.tableArn,
              ],
            }),
          ],
        }),
        S3Policy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:GetObject',
                's3:PutObject',
              ],
              resources: [`${dataBucket.bucketArn}/*`],
            }),
          ],
        }),
      },
    });

    // ==============================================
    // Lambda Function
    // ==============================================
    
    const gradioFunction = new lambda.Function(this, 'GradioFunction', {
      functionName: 'social-listening-gradio',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('frontend/gradio-app'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      role: lambdaRole,
      environment: {
        POSTS_TABLE_NAME: postsTable.tableName,
        SENTIMENT_TABLE_NAME: sentimentTable.tableName,
        DATA_BUCKET_NAME: dataBucket.bucketName,
        BEDROCK_MODEL_ID: props?.novaModelId || 'amazon.nova-micro-v1:0',
      },
    });

    // ==============================================
    // API Gateway
    // ==============================================
    
    const api = new apigateway.RestApi(this, 'SocialListeningApi', {
      restApiName: 'Social Listening API',
      description: 'API for Social Listening Tool',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });

    // Lambda統合
    const lambdaIntegration = new apigateway.LambdaIntegration(gradioFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
    });

    // ルート設定
    api.root.addMethod('ANY', lambdaIntegration);
    api.root.addProxy({
      defaultIntegration: lambdaIntegration,
      anyMethod: true,
    });

    // ==============================================
    // CloudFront Distribution
    // ==============================================
    
    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: new origins.RestApiOrigin(api),
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
    });

    // ==============================================
    // Outputs
    // ==============================================
    
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'CloudFrontUrl', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL',
    });

    new cdk.CfnOutput(this, 'PostsTableName', {
      value: postsTable.tableName,
      description: 'Posts Table Name',
    });

    new cdk.CfnOutput(this, 'SentimentTableName', {
      value: sentimentTable.tableName,
      description: 'Sentiment Table Name',
    });
  }
}
