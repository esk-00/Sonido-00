/**
 * Application constants for Social Listening Tool
 * Centralized configuration values and constants
 */

// Application Information
export const APP_INFO = {
  NAME: 'social-listening-tool',
  VERSION: '1.0.0',
  DESCRIPTION: 'AWS-based social listening tool with real-time sentiment analysis',
  AUTHOR: 'Social Listening Development Team',
} as const;

// AWS Configuration
export const AWS_CONFIG = {
  REGIONS: {
    TOKYO: 'ap-northeast-1',
    VIRGINIA: 'us-east-1',
    OREGON: 'us-west-2',
    IRELAND: 'eu-west-1',
  },
  BEDROCK_REGIONS: ['us-east-1', 'us-west-2', 'eu-west-1'],
} as const;

// Social Media Platforms
export const PLATFORMS = {
  TWITTER: 'twitter',
  INSTAGRAM: 'instagram', 
  FACEBOOK: 'facebook',
  LINKEDIN: 'linkedin',
  TIKTOK: 'tiktok',
} as const;

// Sentiment Categories
export const SENTIMENT = {
  POSITIVE: 'positive',
  NEGATIVE: 'negative',
  NEUTRAL: 'neutral',
  THRESHOLDS: {
    POSITIVE: 0.7,
    NEGATIVE: 0.3,
  },
} as const;

// Processing Status
export const PROCESSING_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

// Alert Types
export const ALERT_TYPES = {
  SENTIMENT: 'sentiment',
  VOLUME: 'volume',
  KEYWORD: 'keyword',
  CUSTOM: 'custom',
} as const;

// Alert Severity Levels
export const ALERT_SEVERITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;

// Lambda Configuration
export const LAMBDA_CONFIG = {
  RUNTIME: 'python3.11',
  TIMEOUT: 900, // 15 minutes
  MEMORY_SIZE: 1024, // 1GB
  MAX_CONCURRENT_EXECUTIONS: 100,
  RESERVED_CONCURRENCY: 10,
} as const;

// DynamoDB Configuration
export const DYNAMODB_CONFIG = {
  BILLING_MODE: 'PAY_PER_REQUEST',
  POINT_IN_TIME_RECOVERY: true,
  STREAM_VIEW_TYPE: 'NEW_AND_OLD_IMAGES',
  DELETION_PROTECTION: true,
  TABLE_CLASS: 'STANDARD',
  BACKUP_RETENTION_DAYS: 30,
  TTL_ATTRIBUTE: 'TTL',
} as const;

// S3 Configuration
export const S3_CONFIG = {
  STORAGE_CLASSES: {
    STANDARD: 'STANDARD',
    STANDARD_IA: 'STANDARD_IA',
    GLACIER: 'GLACIER',
    DEEP_ARCHIVE: 'DEEP_ARCHIVE',
  },
  LIFECYCLE_RULES: {
    TRANSITION_TO_IA_DAYS: 30,
    TRANSITION_TO_GLACIER_DAYS: 90,
    EXPIRATION_DAYS: 365,
  },
  VERSIONING: true,
  PUBLIC_READ_WRITE: false,
} as const;

// API Gateway Configuration
export const API_GATEWAY_CONFIG = {
  THROTTLE: {
    RATE_LIMIT: 1000,
    BURST_LIMIT: 2000,
  },
  CORS: {
    ALLOW_ORIGINS: ['*'],
    ALLOW_HEADERS: [
      'Content-Type',
      'X-Amz-Date',
      'Authorization',
      'X-Api-Key',
      'X-Amz-Security-Token',
    ],
    ALLOW_METHODS: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    MAX_AGE: 86400, // 24 hours
  },
} as const;

// CloudFront Configuration
export const CLOUDFRONT_CONFIG = {
  PRICE_CLASS: 'PriceClass_100', // US, Canada, Europe
  DEFAULT_TTL: 86400, // 24 hours
  MAX_TTL: 31536000, // 1 year
  MIN_TTL: 0,
  COMPRESSION: true,
  HTTP_VERSION: 'http2',
  SSL_PROTOCOLS: ['TLSv1.2', 'TLSv1.3'],
} as const;

// Bedrock Models
export const BEDROCK_MODELS = {
  CLAUDE_HAIKU: 'anthropic.claude-3-haiku-20240307-v1:0',
  CLAUDE_SONNET: 'anthropic.claude-3-sonnet-20240229-v1:0',
  CLAUDE_OPUS: 'anthropic.claude-3-opus-20240229-v1:0',
  NOVA_MICRO: 'amazon.nova-micro-v1:0',
  NOVA_LITE: 'amazon.nova-lite-v1:0',
  NOVA_PRO: 'amazon.nova-pro-v1:0',
} as const;

// Rate Limiting
export const RATE_LIMITS = {
  TWITTER: {
    SEARCH_TWEETS: { requests: 180, window: 900 }, // 15 minutes
    USER_TWEETS: { requests: 75, window: 900 },
    RATE_LIMIT_EXCEEDED: 429,
  },
  INSTAGRAM: {
    MEDIA_SEARCH: { requests: 200, window: 3600 }, // 1 hour
    USER_MEDIA: { requests: 200, window: 3600 },
  },
  API_GATEWAY: {
    DEFAULT: { requests: 1000, window: 3600 },
    BURST: 2000,
  },
} as const;

// Data Processing
export const PROCESSING_CONFIG = {
  BATCH_SIZES: {
    SMALL: 10,
    MEDIUM: 50,
    LARGE: 100,
    XLARGE: 500,
  },
  MAX_RETRIES: 3,
  RETRY_DELAY_BASE: 1000, // 1 second
  RETRY_DELAY_MAX: 30000, // 30 seconds
  TIMEOUT: 30000, // 30 seconds
  PARALLEL_PROCESSING: true,
  MAX_PARALLEL_JOBS: 10,
} as const;

// Data Retention
export const DATA_RETENTION = {
  RAW_POSTS: 90, // days
  SENTIMENT_RESULTS: 365, // days
  AGGREGATED_DATA: 1095, // 3 years
  ALERT_LOGS: 30, // days
} as const;

// Hugging Face Configuration
export const HUGGINGFACE_CONFIG = {
  MODELS: {
    SENTIMENT_ANALYSIS: 'cardiffnlp/twitter-roberta-base-sentiment-latest',
    EMOTION_ANALYSIS: 'j-hartmann/emotion-english-distilroberta-base',
    TEXT_CLASSIFICATION: 'microsoft/DialoGPT-medium',
  },
  API_BASE_URL: 'https://api-inference.huggingface.co',
  MAX_RETRIES: 3,
  TIMEOUT: 30000,
} as const;

// Gradio Configuration
export const GRADIO_CONFIG = {
  PORT: 7860,
  SERVER_NAME: '0.0.0.0',
  SHARE: false,
  DEBUG: false,
  THEME: 'default',
  TITLE: 'Social Listening Dashboard',
  DESCRIPTION: 'Real-time social media sentiment analysis and monitoring',
} as const;

// Database Table Names
export const TABLE_NAMES = {
  POSTS: 'social-posts',
  SENTIMENT_RESULTS: 'sentiment-results',
  KEYWORDS: 'keywords',
  ALERTS: 'alerts',
  USERS: 'users',
  CONFIGURATIONS: 'configurations',
} as const;

// API Endpoints
export const API_ENDPOINTS = {
  POSTS: '/api/posts',
  SENTIMENT: '/api/sentiment',
  KEYWORDS: '/api/keywords',
  ALERTS: '/api/alerts',
  ANALYTICS: '/api/analytics',
  HEALTH: '/api/health',
} as const;

// Monitoring and Logging
export const MONITORING_CONFIG = {
  LOG_LEVELS: {
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
  },
  METRICS: {
    POSTS_PROCESSED: 'PostsProcessed',
    SENTIMENT_ANALYZED: 'SentimentAnalyzed',
    ALERTS_GENERATED: 'AlertsGenerated',
    API_REQUESTS: 'ApiRequests',
    ERROR_COUNT: 'ErrorCount',
  },
  CLOUDWATCH_NAMESPACE: 'SocialListening',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  INVALID_PLATFORM: 'Invalid social media platform specified',
  AUTHENTICATION_FAILED: 'Authentication failed for social media platform',
  RATE_LIMIT_EXCEEDED: 'Rate limit exceeded for API requests',
  INVALID_KEYWORDS: 'Invalid keywords provided for monitoring',
  PROCESSING_FAILED: 'Failed to process social media data',
  SENTIMENT_ANALYSIS_FAILED: 'Sentiment analysis processing failed',
  DATABASE_ERROR: 'Database operation failed',
  API_ERROR: 'API request failed',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  POSTS_EXTRACTED: 'Posts successfully extracted from social media',
  SENTIMENT_ANALYZED: 'Sentiment analysis completed successfully',
  ALERT_CREATED: 'Alert created successfully',
  CONFIGURATION_SAVED: 'Configuration saved successfully',
  DATA_EXPORTED: 'Data exported successfully',
} as const;

// Feature Flags
export const FEATURE_FLAGS = {
  REAL_TIME_PROCESSING: true,
  ADVANCED_ANALYTICS: true,
  EXPORT_FUNCTIONALITY: true,
  CUSTOM_ALERTS: true,
  MULTI_LANGUAGE_SUPPORT: false,
  SOCIAL_MEDIA_POSTING: false,
} as const;

// Time Intervals (in milliseconds)
export const TIME_INTERVALS = {
  MINUTE: 60 * 1000,
  FIVE_MINUTES: 5 * 60 * 1000,
  FIFTEEN_MINUTES: 15 * 60 * 1000,
  THIRTY_MINUTES: 30 * 60 * 1000,
  HOUR: 60 * 60 * 1000,
  DAY: 24 * 60 * 60 * 1000,
  WEEK: 7 * 24 * 60 * 60 * 1000,
} as const;

// Export all constants as a single object for convenience
export const CONSTANTS = {
  APP_INFO,
  AWS_CONFIG,
  PLATFORMS,
  SENTIMENT,
  PROCESSING_STATUS,
  ALERT_TYPES,
  ALERT_SEVERITY,
  LAMBDA_CONFIG,
  DYNAMODB_CONFIG,
  S3_CONFIG,
  API_GATEWAY_CONFIG,
  CLOUDFRONT_CONFIG,
  BEDROCK_MODELS,
  RATE_LIMITS,
  PROCESSING_CONFIG,
  DATA_RETENTION,
  HUGGINGFACE_CONFIG,
  GRADIO_CONFIG,
  TABLE_NAMES,
  API_ENDPOINTS,
  MONITORING_CONFIG,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  FEATURE_FLAGS,
  TIME_INTERVALS,
} as const;
