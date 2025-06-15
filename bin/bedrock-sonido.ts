#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SocialListeningStack } from '../lib/social-listening-stack';

const app = new cdk.App();
new SocialListeningStack(app, 'SocialListeningStack', {
  // Bedrock Nova モデル設定
  novaModelId: 'us.amazon.nova-lite-v1:0',
  // または Nova Micro を使用する場合
  // novaModelId: 'us.amazon.nova-micro-v1:0',
  
  // Hugging Face設定（環境变数から取得）
  huggingFaceApiKey: process.env.HUGGINGFACE_API_KEY,
  
  // ソーシャルメディアAPI設定
  twitterBearerToken: process.env.TWITTER_BEARER_TOKEN,
  // 他のソーシャルメディアのAPIキーも追加可能
  
  // 環境変数から取得したリージョンを使用、またはデフォルトとしてus-east-1を使用
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1'
  },
});

// タグはスタックレベルで追加
cdk.Tags.of(app).add('Project', 'SocialListening');
cdk.Tags.of(app).add('Environment', 'Dev');
cdk.Tags.of(app).add('Purpose', 'PostExtraction');
