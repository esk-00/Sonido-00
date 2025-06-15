/**
 * Type definitions for Social Listening Tool
 * Common interfaces and types used across the application
 */

// Base Types
export type SentimentScore = number; // 0-1 range
export type Platform = 'twitter' | 'instagram' | 'facebook' | 'linkedin' | 'tiktok';
export type SentimentCategory = 'positive' | 'negative' | 'neutral';
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

// Social Media Post Interface
export interface SocialPost {
  id: string;
  platform: Platform;
  content: string;
  author: {
    id: string;
    username: string;
    displayName?: string;
    verified?: boolean;
    followersCount?: number;
  };
  metrics: {
    likes?: number;
    shares?: number;
    comments?: number;
    views?: number;
    retweets?: number;
  };
  createdAt: string;
  url?: string;
  hashtags: string[];
  mentions: string[];
  media?: MediaItem[];
  location?: Location;
  language?: string;
  isRetweet?: boolean;
  originalPost?: string; // ID of original post if retweet
}

// Media Item Interface
export interface MediaItem {
  type: 'image' | 'video' | 'gif';
  url: string;
  thumbnailUrl?: string;
  width?: number;
  height?: number;
  duration?: number; // for videos
}

// Location Interface
export interface Location {
  name?: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  country?: string;
  city?: string;
}

// Sentiment Analysis Result
export interface SentimentResult {
  id: string;
  postId: string;
  score: SentimentScore;
  category: SentimentCategory;
  confidence: number;
  details?: {
    positive: number;
    negative: number;
    neutral: number;
    mixed?: number;
  };
  keywords?: string[]; // Key sentiment-driving words
  processedAt: string;
  model: string; // Bedrock model used
  version: string; // Model version
}

// Keyword Monitoring Configuration
export interface KeywordConfig {
  id: string;
  keyword: string;
  platforms: Platform[];
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  alertThresholds?: {
    sentimentDrop: number; // Threshold for negative sentiment spike
    volumeSpike: number; // Threshold for post volume spike
  };
  filters?: {
    language?: string[];
    minFollowers?: number;
    excludeRetweets?: boolean;
    includeReplies?: boolean;
  };
}

// Alert Configuration
export interface AlertConfig {
  id: string;
  name: string;
  type: 'sentiment' | 'volume' | 'keyword' | 'custom';
  isActive: boolean;
  conditions: {
    keywords?: string[];
    platforms?: Platform[];
    sentimentThreshold?: number;
    volumeThreshold?: number;
    timeWindow?: number; // minutes
  };
  notifications: {
    email?: boolean;
    slack?: boolean;
    webhook?: string;
  };
  createdAt: string;
  updatedAt: string;
}

// Alert Event
export interface AlertEvent {
  id: string;
  alertConfigId: string;
  type: AlertConfig['type'];
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  data: any; // Specific data related to the alert
  triggeredAt: string;
  acknowledgedAt?: string;
  acknowledgedBy?: string;
  resolvedAt?: string;
  resolvedBy?: string;
}

// Data Processing Job
export interface ProcessingJob {
  id: string;
  type: 'post_collection' | 'sentiment_analysis' | 'data_export' | 'cleanup';
  status: ProcessingStatus;
  progress: number; // 0-100
  metadata: {
    totalItems?: number;
    processedItems?: number;
    failedItems?: number;
    keywords?: string[];
    platforms?: Platform[];
    dateRange?: {
      start: string;
      end: string;
    };
  };
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  result?: any;
}

// Analytics Data Types
export interface SentimentTrend {
  timestamp: string;
  positive: number;
  negative: number;
  neutral: number;
  total: number;
  keywords?: string[];
}

export interface VolumeMetrics {
  timestamp: string;
  count: number;
  platform: Platform;
  keyword?: string;
}

export interface TopKeywords {
  keyword: string;
  count: number;
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
  platforms: Platform[];
}

export interface InfluencerMetrics {
  userId: string;
  username: string;
  displayName?: string;
  platform: Platform;
  postsCount: number;
  avgSentiment: number;
  totalEngagement: number;
  followersCount?: number;
  verified?: boolean;
}

// Dashboard Data
export interface DashboardData {
  summary: {
    totalPosts: number;
    avgSentiment: number;
    sentimentDistribution: {
      positive: number;
      negative: number;
      neutral: number;
    };
    topKeywords: TopKeywords[];
    platformBreakdown: Array<{
      platform: Platform;
      count: number;
      avgSentiment: number;
    }>;
  };
  trends: {
    sentiment: SentimentTrend[];
    volume: VolumeMetrics[];
  };
  alerts: {
    active: AlertEvent[];
    recent: AlertEvent[];
  };
  processing: {
    activeJobs: ProcessingJob[];
    recentJobs: ProcessingJob[];
  };
}

// API Request/Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// Lambda Event Types
export interface LambdaEvent {
  httpMethod?: string;
  path?: string;
  pathParameters?: Record<string, string>;
  queryStringParameters?: Record<string, string>;
  headers?: Record<string, string>;
  body?: string;
  requestContext?: {
    requestId: string;
    stage: string;
    resourcePath: string;
    httpMethod: string;
    requestTime: string;
    requestTimeEpoch: number;
    identity: {
      sourceIp: string;
      userAgent?: string;
    };
  };
}

export interface LambdaResponse {
  statusCode: number;
  headers?: Record<string, string>;
  body: string;
  isBase64Encoded?: boolean;
}

// DynamoDB Item Types
export interface DynamoDBPost extends Omit<SocialPost, 'createdAt'> {
  TTL?: number; // For automatic item expiration
  GSI1PK?: string; // Global Secondary Index partition key
  GSI1SK?: string; // Global Secondary Index sort key
  createdAt: number; // Unix timestamp for DynamoDB
}

export interface DynamoDBSentiment extends Omit<SentimentResult, 'processedAt'> {
  TTL?: number;
  processedAt: number; // Unix timestamp
}

export interface DynamoDBKeyword extends Omit<KeywordConfig, 'createdAt' | 'updatedAt'> {
  createdAt: number;
  updatedAt: number;
}

// Configuration Types
export interface AppConfig {
  aws: {
    region: string;
    accountId: string;
  };
  app: {
    name: string;
    stage: string;
    version: string;
  };
  social: {
    twitter: {
      apiKey: string;
      apiSecret: string;
      accessToken: string;
      accessTokenSecret: string;
      bearerToken: string;
    };
    instagram: {
      accessToken: string;
    };
    facebook: {
      appId: string;
      appSecret: string;
    };
  };
  aws_services: {
    bedrock: {
      region: string;
      modelId: string;
      novaModelId: string;
    };
    dynamodb: {
      postsTable: string;
      sentimentTable: string;
      keywordsTable: string;
      alertsTable: string;
    };
    s3: {
      rawDataBucket: string;
      processedDataBucket: string;
      staticAssetsBucket: string;
    };
    lambda: {
      timeout: number;
      memorySize: number;
      runtime: string;
    };
  };
  processing: {
    batchSize: number;
    maxPostsPerRequest: number;
    dataRetentionDays: number;
  };
  monitoring: {
    alertEmail: string;
    slackWebhook?: string;
  };
}

// Error Types
export class SocialListeningError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500,
    public details?: any
  ) {
    super(message);
    this.name = 'SocialListeningError';
  }
}

export class ValidationError extends SocialListeningError {
  constructor(message: string, details?: any) {
    super(message, 'VALIDATION_ERROR', 400, details);
    this.name = 'ValidationError';
  }
}

export class AuthenticationError extends SocialListeningError {
  constructor(message: string = 'Authentication failed') {
    super(message, 'AUTH_ERROR', 401);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends SocialListeningError {
  constructor(message: string = 'Rate limit exceeded') {
    super(message, 'RATE_LIMIT_ERROR', 429);
    this.name = 'RateLimitError';
  }
}

export class ExternalApiError extends SocialListeningError {
  constructor(message: string, public service: string, public originalError?: any) {
    super(message, 'EXTERNAL_API_ERROR', 502, { service, originalError });
    this.name = 'ExternalApiError';
  }
}

// Utility Types
export type DeepPartial<T> = {
  [P in keyof T]?: DeepPartial<T[P]>;
};

export type RequireFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OmitFields<T, K extends keyof T> = Omit<T, K>;

export type PickFields<T, K extends keyof T> = Pick<T, K>;

// Environment Variables Type
export interface EnvironmentVariables {
  // AWS
  AWS_ACCOUNT_ID: string;
  AWS_REGION: string;
  AWS_PROFILE?: string;
  
  // App
  APP_NAME: string;
  ENVIRONMENT: string;
  STAGE: string;
  
  // Social Media APIs
  TWITTER_API_KEY: string;
  TWITTER_API_SECRET: string;
  TWITTER_ACCESS_TOKEN: string;
  TWITTER_ACCESS_TOKEN_SECRET: string;
  TWITTER_BEARER_TOKEN: string;
  
  // Bedrock
  BEDROCK_REGION: string;
  BEDROCK_MODEL_ID: string;
  BEDROCK_NOVA_MODEL_ID: string;
  
  // DynamoDB
  POSTS_TABLE_NAME: string;
  SENTIMENT_TABLE_NAME: string;
  KEYWORDS_TABLE_NAME: string;
  ALERTS_TABLE_NAME: string;
  
  // S3
  RAW_DATA_BUCKET: string;
  PROCESSED_DATA_BUCKET: string;
  STATIC_ASSETS_BUCKET: string;
  
  // Processing
  BATCH_SIZE: string;
  MAX_POSTS_PER_REQUEST: string;
  SENTIMENT_THRESHOLD_POSITIVE: string;
  SENTIMENT_THRESHOLD_NEGATIVE: string;
  DATA_RETENTION_DAYS: string;
  
  // Monitoring
  ALERT_EMAIL: string;
  SLACK_WEBHOOK_URL?: string;
  
  // Feature Flags
  ENABLE_REAL_TIME_PROCESSING: string;
  ENABLE_BATCH_PROCESSING: string;
  ENABLE_TWITTER_COLLECTION: string;
  ENABLE_INSTAGRAM_COLLECTION: string;
  ENABLE_AUTOMATED_ALERTS: string;
  
  // Development
  DEBUG_MODE: string;
  LOCAL_DEVELOPMENT: string;
}

// Export commonly used type combinations
export type CreatePostRequest = OmitFields<SocialPost, 'id' | 'createdAt'>;
export type UpdateKeywordRequest = DeepPartial<OmitFields<KeywordConfig, 'id' | 'createdAt'>>;
export type CreateAlertRequest = OmitFields<AlertConfig, 'id' | 'createdAt' | 'updatedAt'>;

// Re-export for convenience
export {
  SocialPost as Post,
  SentimentResult as Sentiment,
  KeywordConfig as Keyword,
  AlertConfig as Alert,
  AlertEvent as AlertEvent,
  ProcessingJob as Job,
};
