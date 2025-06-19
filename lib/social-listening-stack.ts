import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';

export interface SocialListeningStackProps extends cdk.StackProps {
  novaModelId: string;
  huggingFaceApiKey?: string;
  twitterBearerToken?: string;
}

export class SocialListeningStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: SocialListeningStackProps) {
    super(scope, id, props);

    // ==============================================
    // DynamoDB Tables (既存のものを参照)
    // ==============================================
    
    const postsTable = dynamodb.Table.fromTableName(this, 'PostsTable', 'social-listening-posts');
    const sentimentTable = dynamodb.Table.fromTableName(this, 'SentimentTable', 'social-listening-sentiment');

    // ==============================================
    // S3 Buckets
    // ==============================================
    
    const dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: `social-listening-data-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.RETAIN, // 既存データ保護
    });

    const staticBucket = new s3.Bucket(this, 'StaticBucket', {
      bucketName: `social-listening-static-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const oai = new cloudfront.OriginAccessIdentity(this, 'StaticBucketOAI');
    staticBucket.grantRead(oai);

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
                `${postsTable.tableArn}/index/*`,
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
              resources: [
                `${dataBucket.bucketArn}/*`,
                `${staticBucket.bucketArn}/*`,
              ],
            }),
          ],
        }),
      },
    });

    // ==============================================
    // Lambda Function (元のシンプルな構成)
    // ==============================================
    
    const gradioFunction = new lambda.Function(this, 'GradioFunction', {
      functionName: 'social-listening-gradio',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('frontend/gradio-app'),
      timeout: cdk.Duration.seconds(300),
      memorySize: 1024,
      role: lambdaRole,
      environment: {
        POSTS_TABLE_NAME: postsTable.tableName,
        SENTIMENT_TABLE_NAME: sentimentTable.tableName,
        DATA_BUCKET_NAME: dataBucket.bucketName,
        BEDROCK_MODEL_ID: props.novaModelId,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
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

    // Gradioアプリのエンドポイント
    const gradioResource = api.root.addResource('gradio');
    const gradioIntegration = new apigateway.LambdaIntegration(gradioFunction, {
      proxy: true,
    });

    // Gradio関連のエンドポイント
    gradioResource.addMethod('ANY', gradioIntegration);
    gradioResource.addProxy({
      defaultIntegration: gradioIntegration,
      anyMethod: true,
    });

    // ルートパスもGradio関数にルーティング（フォールバック）
    api.root.addMethod('ANY', gradioIntegration);

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
      additionalBehaviors: {
        '/gradio/*': {
          origin: new origins.RestApiOrigin(api),
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        },
        '/static/*': {
          origin: new origins.S3Origin(staticBucket, {
            originAccessIdentity: oai,
          }),
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        },
      },
    });

    // index.htmlのデプロイ
    new s3deploy.BucketDeployment(this, 'StaticDeploy', {
      sources: [s3deploy.Source.asset('frontend/public')],
      destinationBucket: staticBucket,
      distribution: distribution,
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
