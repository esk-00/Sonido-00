import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
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
    // S3 Buckets
    // ==============================================
    
    // 投稿データ保存用S3バケット
    const dataBucket = new s3.Bucket(this, 'SocialListeningDataBucket', {
      bucketName: `social-listening-data-${this.account}-${this.region}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // 開発環境用
    });

    // Gradioアプリ用静的ファイルバケット
    const staticBucket = new s3.Bucket(this, 'SocialListeningStaticBucket', {
      bucketName: `social-listening-static-${this.account}-${this.region}`,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ==============================================
    // DynamoDB Tables
    // ==============================================
    
    // 投稿データテーブル
    const postsTable = new dynamodb.Table(this, 'PostsTable', {
      tableName: 'social-listening-posts',
      partitionKey: { name: 'postId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.NUMBER },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // インデックス追加（プラットフォーム別検索用）
    postsTable.addGlobalSecondaryIndex({
      indexName: 'platform-timestamp-index',
      partitionKey: { name: 'platform', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.NUMBER },
    });

    // 感情分析結果テーブル
    const sentimentTable = new dynamodb.Table(this, 'SentimentTable', {
      tableName: 'social-listening-sentiment',
      partitionKey: { name: 'postId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ==============================================
    // IAM Roles
    // ==============================================
    
    // Lambda実行用のIAMロール
    const lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
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
                `arn:aws:bedrock:${this.region}::foundation-model/${props.novaModelId}`,
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
                's3:DeleteObject',
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
    // Lambda Functions
    // ==============================================
    
    // 投稿抜き出しLambda
    const postExtractorFunction = new lambda.Function(this, 'PostExtractorFunction', {
      functionName: 'social-listening-post-extractor',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/post-extractor'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      role: lambdaExecutionRole,
      environment: {
        POSTS_TABLE_NAME: postsTable.tableName,
        DATA_BUCKET_NAME: dataBucket.bucketName,
        TWITTER_BEARER_TOKEN: props.twitterBearerToken || '',
        HUGGINGFACE_API_KEY: props.huggingFaceApiKey || '',
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // 感情分析Lambda
    const sentimentAnalyzerFunction = new lambda.Function(this, 'SentimentAnalyzerFunction', {
      functionName: 'social-listening-sentiment-analyzer',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/sentiment-analyzer'),
      timeout: cdk.Duration.minutes(3),
      memorySize: 1024,
      role: lambdaExecutionRole,
      environment: {
        POSTS_TABLE_NAME: postsTable.tableName,
        SENTIMENT_TABLE_NAME: sentimentTable.tableName,
        BEDROCK_MODEL_ID: props.novaModelId,
        AWS_REGION: this.region,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Gradio アプリケーション Lambda
    const gradioAppFunction = new lambda.Function(this, 'GradioAppFunction', {
      functionName: 'social-listening-gradio-app',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'app.handler',
      code: lambda.Code.fromAsset('frontend/gradio-app'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      role: lambdaExecutionRole,
      environment: {
        POSTS_TABLE_NAME: postsTable.tableName,
        SENTIMENT_TABLE_NAME: sentimentTable.tableName,
        DATA_BUCKET_NAME: dataBucket.bucketName,
        STATIC_BUCKET_NAME: staticBucket.bucketName,
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
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key'],
      },
    });

    // API エンドポイント設定
    const postsResource = api.root.addResource('posts');
    const extractResource = postsResource.addResource('extract');
    const analyzeResource = postsResource.addResource('analyze');
    const gradioResource = api.root.addResource('gradio');

    // Lambda統合
    extractResource.addMethod('POST', new apigateway.LambdaIntegration(postExtractorFunction));
    analyzeResource.addMethod('POST', new apigateway.LambdaIntegration(sentimentAnalyzerFunction));
    postsResource.addMethod('GET', new apigateway.LambdaIntegration(postExtractorFunction));
    
    // Gradio プロキシ統合
    gradioResource.addProxy({
      defaultIntegration: new apigateway.LambdaIntegration(gradioAppFunction),
      anyMethod: true,
    });

    // ==============================================
    // CloudFront Distribution
    // ==============================================
    
    const distribution = new cloudfront.Distribution(this, 'SocialListeningDistribution', {
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
          origin: new origins.S3Origin(staticBucket),
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        },
      },
    });

    // ==============================================
    // Outputs
    // ==============================================
    
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'CloudFrontUrl', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL',
    });

    new cdk.CfnOutput(this, 'GradioAppUrl', {
      value: `https://${distribution.distributionDomainName}/gradio`,
      description: 'Gradio Application URL',
    });

    new cdk.CfnOutput(this, 'PostsTableName', {
      value: postsTable.tableName,
      description: 'DynamoDB Posts Table Name',
    });

    new cdk.CfnOutput(this, 'DataBucketName', {
      value: dataBucket.bucketName,
      description: 'S3 Data Bucket Name',
    });
  }
}
