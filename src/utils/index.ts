/**
 * Utility functions for Social Listening Tool
 * Common helper functions used across the application
 */

import * as crypto from 'crypto';
import * as path from 'path';

// Environment and Configuration Utilities
export class EnvUtils {
  /**
   * Retry function with exponential backoff
   */
  static async retry<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<T> {
    let lastError: Error;
    
    for (let i = 0; i <= maxRetries; i++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        
        if (i === maxRetries) {
          throw lastError;
        }
        
        const delay = baseDelay * Math.pow(2, i);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError!;
  }
}

// Logging Utilities
export class LogUtils {
  private static getTimestamp(): string {
    return new Date().toISOString();
  }

  private static formatMessage(level: string, message: string, meta?: any): string {
    const logEntry = {
      timestamp: this.getTimestamp(),
      level,
      message,
      ...(meta && { meta }),
    };
    return JSON.stringify(logEntry);
  }

  static info(message: string, meta?: any): void {
    console.log(this.formatMessage('INFO', message, meta));
  }

  static warn(message: string, meta?: any): void {
    console.warn(this.formatMessage('WARN', message, meta));
  }

  static error(message: string, error?: Error, meta?: any): void {
    const errorMeta = {
      ...meta,
      ...(error && {
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name,
        },
      }),
    };
    console.error(this.formatMessage('ERROR', message, errorMeta));
  }

  static debug(message: string, meta?: any): void {
    if (EnvUtils.getBoolean('DEBUG_MODE')) {
      console.debug(this.formatMessage('DEBUG', message, meta));
    }
  }
}

// API Response Utilities
export class ApiUtils {
  /**
   * Create successful API response
   */
  static successResponse<T>(data: T, statusCode: number = 200): {
    statusCode: number;
    body: string;
    headers: Record<string, string>;
  } {
    return {
      statusCode,
      body: JSON.stringify({
        success: true,
        data,
        timestamp: DateUtils.now(),
      }),
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
      },
    };
  }

  /**
   * Create paginated API response
   */
  static paginatedResponse<T>(
    data: T[],
    page: number,
    limit: number,
    total: number
  ): {
    statusCode: number;
    body: string;
    headers: Record<string, string>;
  } {
    const totalPages = Math.ceil(total / limit);
    const hasNext = page < totalPages;
    const hasPrev = page > 1;

    return this.successResponse({
      items: data,
      pagination: {
        page,
        limit,
        total,
        totalPages,
        hasNext,
        hasPrev,
      },
    });
  }

  /**
   * Parse query parameters from event
   */
  static parseQueryParams(event: any): Record<string, string> {
    return event.queryStringParameters || {};
  }

  /**
   * Parse path parameters from event
   */
  static parsePathParams(event: any): Record<string, string> {
    return event.pathParameters || {};
  }

  /**
   * Parse JSON body from event
   */
  static parseBody<T>(event: any): T {
    if (!event.body) {
      throw new Error('Request body is required');
    }
    
    try {
      return JSON.parse(event.body);
    } catch (error) {
      throw new Error('Invalid JSON in request body');
    }
  }
}

// Cache Utilities
export class CacheUtils {
  private static cache = new Map<string, { value: any; expiry: number }>();

  /**
   * Set cache with TTL
   */
  static set(key: string, value: any, ttlSeconds: number = 300): void {
    const expiry = Date.now() + (ttlSeconds * 1000);
    this.cache.set(key, { value, expiry });
  }

  /**
   * Get from cache
   */
  static get<T>(key: string): T | null {
    const item = this.cache.get(key);
    
    if (!item) {
      return null;
    }
    
    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }
    
    return item.value;
  }

  /**
   * Delete from cache
   */
  static delete(key: string): boolean {
    return this.cache.delete(key);
  }

  /**
   * Clear all cache
   */
  static clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache stats
   */
  static stats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }
}

// Rate Limiting Utilities
export class RateLimitUtils {
  private static requests = new Map<string, number[]>();

  /**
   * Check if request is within rate limit
   */
  static isAllowed(
    key: string,
    maxRequests: number,
    windowSeconds: number
  ): boolean {
    const now = Date.now();
    const windowStart = now - (windowSeconds * 1000);
    
    if (!this.requests.has(key)) {
      this.requests.set(key, []);
    }
    
    const keyRequests = this.requests.get(key)!;
    
    // Remove old requests outside the window
    const validRequests = keyRequests.filter(timestamp => timestamp > windowStart);
    this.requests.set(key, validRequests);
    
    if (validRequests.length >= maxRequests) {
      return false;
    }
    
    // Add current request
    validRequests.push(now);
    return true;
  }

  /**
   * Get remaining requests in current window
   */
  static getRemainingRequests(
    key: string,
    maxRequests: number,
    windowSeconds: number
  ): number {
    const now = Date.now();
    const windowStart = now - (windowSeconds * 1000);
    
    if (!this.requests.has(key)) {
      return maxRequests;
    }
    
    const keyRequests = this.requests.get(key)!;
    const validRequests = keyRequests.filter(timestamp => timestamp > windowStart);
    
    return Math.max(0, maxRequests - validRequests.length);
  }
}

// Sentiment Analysis Utilities
export class SentimentUtils {
  /**
   * Categorize sentiment score
   */
  static categorize(score: number): 'positive' | 'negative' | 'neutral' {
    const positiveThreshold = EnvUtils.getNumber('SENTIMENT_THRESHOLD_POSITIVE', 0.7);
    const negativeThreshold = EnvUtils.getNumber('SENTIMENT_THRESHOLD_NEGATIVE', 0.3);
    
    if (score >= positiveThreshold) return 'positive';
    if (score <= negativeThreshold) return 'negative';
    return 'neutral';
  }

  /**
   * Calculate sentiment distribution
   */
  static calculateDistribution(scores: number[]): {
    positive: number;
    negative: number;
    neutral: number;
    average: number;
  } {
    if (scores.length === 0) {
      return { positive: 0, negative: 0, neutral: 0, average: 0 };
    }

    let positive = 0;
    let negative = 0;
    let neutral = 0;
    let total = 0;

    scores.forEach(score => {
      const category = this.categorize(score);
      switch (category) {
        case 'positive':
          positive++;
          break;
        case 'negative':
          negative++;
          break;
        case 'neutral':
          neutral++;
          break;
      }
      total += score;
    });

    return {
      positive: DataUtils.percentage(positive, scores.length),
      negative: DataUtils.percentage(negative, scores.length),
      neutral: DataUtils.percentage(neutral, scores.length),
      average: total / scores.length,
    };
  }

  /**
   * Detect sentiment spike (sudden change)
   */
  static detectSpike(
    currentScore: number,
    previousScores: number[],
    threshold: number = 0.3
  ): boolean {
    if (previousScores.length === 0) return false;
    
    const average = previousScores.reduce((sum, score) => sum + score, 0) / previousScores.length;
    const difference = Math.abs(currentScore - average);
    
    return difference > threshold;
  }
}

// Export all utilities as a single object for convenience
export const Utils = {
  Env: EnvUtils,
  String: StringUtils,
  Date: DateUtils,
  AWS: AWSUtils,
  Data: DataUtils,
  Validation: ValidationUtils,
  SocialMedia: SocialMediaUtils,
  Error: ErrorUtils,
  Log: LogUtils,
  Api: ApiUtils,
  Cache: CacheUtils,
  RateLimit: RateLimitUtils,
  Sentiment: SentimentUtils,
};

export default Utils;
   * Get environment variable with optional default value
   */
  static get(key: string, defaultValue?: string): string {
    const value = process.env[key];
    if (value === undefined && defaultValue === undefined) {
      throw new Error(`Environment variable ${key} is required but not set`);
    }
    return value || defaultValue || '';
  }

  /**
   * Get required environment variable
   */
  static getRequired(key: string): string {
    const value = process.env[key];
    if (!value) {
      throw new Error(`Environment variable ${key} is required but not set`);
    }
    return value;
  }

  /**
   * Get boolean environment variable
   */
  static getBoolean(key: string, defaultValue: boolean = false): boolean {
    const value = process.env[key];
    if (!value) return defaultValue;
    return value.toLowerCase() === 'true' || value === '1';
  }

  /**
   * Get number environment variable
   */
  static getNumber(key: string, defaultValue: number = 0): number {
    const value = process.env[key];
    if (!value) return defaultValue;
    const parsed = parseInt(value, 10);
    if (isNaN(parsed)) {
      throw new Error(`Environment variable ${key} must be a valid number`);
    }
    return parsed;
  }
}

// String Utilities
export class StringUtils {
  /**
   * Generate random string
   */
  static randomString(length: number = 8): string {
    return crypto.randomBytes(length).toString('hex').substring(0, length);
  }

  /**
   * Convert string to kebab-case
   */
  static toKebabCase(str: string): string {
    return str
      .replace(/([a-z])([A-Z])/g, '$1-$2')
      .toLowerCase()
      .replace(/\s+/g, '-');
  }

  /**
   * Convert string to camelCase
   */
  static toCamelCase(str: string): string {
    return str
      .toLowerCase()
      .replace(/-(.)/g, (_, group1) => group1.toUpperCase());
  }

  /**
   * Truncate string with ellipsis
   */
  static truncate(str: string, maxLength: number): string {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - 3) + '...';
  }

  /**
   * Remove HTML tags from string
   */
  static stripHtml(html: string): string {
    return html.replace(/<[^>]*>/g, '');
  }

  /**
   * Escape special regex characters
   */
  static escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}

// Date and Time Utilities
export class DateUtils {
  /**
   * Get current timestamp in ISO format
   */
  static now(): string {
    return new Date().toISOString();
  }

  /**
   * Get timestamp N days ago
   */
  static daysAgo(days: number): string {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date.toISOString();
  }

  /**
   * Format date for display
   */
  static formatDisplay(date: Date | string): string {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  /**
   * Get start of day timestamp
   */
  static startOfDay(date?: Date): string {
    const d = date || new Date();
    d.setHours(0, 0, 0, 0);
    return d.toISOString();
  }

  /**
   * Get end of day timestamp
   */
  static endOfDay(date?: Date): string {
    const d = date || new Date();
    d.setHours(23, 59, 59, 999);
    return d.toISOString();
  }
}

// AWS Resource Name Utilities
export class AWSUtils {
  /**
   * Generate consistent resource name
   */
  static resourceName(
    appName: string,
    resourceType: string,
    stage: string,
    suffix?: string
  ): string {
    const parts = [appName, resourceType, stage];
    if (suffix) parts.push(suffix);
    return parts.join('-');
  }

  /**
   * Generate Lambda function name
   */
  static lambdaName(appName: string, functionName: string, stage: string): string {
    return this.resourceName(appName, functionName, stage);
  }

  /**
   * Generate DynamoDB table name
   */
  static dynamoTableName(appName: string, tableName: string, stage: string): string {
    return this.resourceName(appName, tableName, stage);
  }

  /**
   * Generate S3 bucket name (must be globally unique)
   */
  static s3BucketName(appName: string, bucketType: string, stage: string): string {
    const timestamp = Date.now().toString().slice(-8);
    return `${appName}-${bucketType}-${stage}-${timestamp}`.toLowerCase();
  }

  /**
   * Parse ARN and extract resource information
   */
  static parseArn(arn: string): {
    service: string;
    region: string;
    accountId: string;
    resourceType: string;
    resourceName: string;
  } {
    const parts = arn.split(':');
    if (parts.length < 6) {
      throw new Error(`Invalid ARN format: ${arn}`);
    }

    const [, , service, region, accountId, resource] = parts;
    const resourceParts = resource.split('/');
    const resourceType = resourceParts[0];
    const resourceName = resourceParts.slice(1).join('/');

    return {
      service,
      region,
      accountId,
      resourceType,
      resourceName,
    };
  }
}

// Data Processing Utilities
export class DataUtils {
  /**
   * Deep clone object
   */
  static deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
  }

  /**
   * Remove undefined values from object
   */
  static removeUndefined<T extends Record<string, any>>(obj: T): Partial<T> {
    const result: Partial<T> = {};
    Object.keys(obj).forEach((key) => {
      if (obj[key] !== undefined) {
        result[key as keyof T] = obj[key];
      }
    });
    return result;
  }

  /**
   * Group array by key
   */
  static groupBy<T>(array: T[], keyFn: (item: T) => string): Record<string, T[]> {
    return array.reduce((groups, item) => {
      const key = keyFn(item);
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(item);
      return groups;
    }, {} as Record<string, T[]>);
  }

  /**
   * Chunk array into smaller arrays
   */
  static chunk<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  /**
   * Calculate percentage
   */
  static percentage(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100 * 100) / 100; // Round to 2 decimal places
  }
}

// Validation Utilities
export class ValidationUtils {
  /**
   * Validate email format
   */
  static isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Validate URL format
   */
  static isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Validate Twitter handle
   */
  static isValidTwitterHandle(handle: string): boolean {
    const twitterRegex = /^@?[a-zA-Z0-9_]{1,15}$/;
    return twitterRegex.test(handle);
  }

  /**
   * Validate sentiment score (0-1 range)
   */
  static isValidSentimentScore(score: number): boolean {
    return typeof score === 'number' && score >= 0 && score <= 1;
  }

  /**
   * Validate AWS region format
   */
  static isValidAwsRegion(region: string): boolean {
    const regionRegex = /^[a-z]{2}-[a-z]+-\d{1}$/;
    return regionRegex.test(region);
  }
}

// Social Media Utilities
export class SocialMediaUtils {
  /**
   * Extract hashtags from text
   */
  static extractHashtags(text: string): string[] {
    const hashtagRegex = /#[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+/g;
    const matches = text.match(hashtagRegex);
    return matches ? matches.map(tag => tag.substring(1)) : [];
  }

  /**
   * Extract mentions from text
   */
  static extractMentions(text: string): string[] {
    const mentionRegex = /@[\w]+/g;
    const matches = text.match(mentionRegex);
    return matches ? matches.map(mention => mention.substring(1)) : [];
  }

  /**
   * Extract URLs from text
   */
  static extractUrls(text: string): string[] {
    const urlRegex = /https?:\/\/[^\s]+/g;
    const matches = text.match(urlRegex);
    return matches || [];
  }

  /**
   * Clean tweet text (remove URLs, mentions, extra whitespace)
   */
  static cleanText(text: string): string {
    return text
      .replace(/https?:\/\/[^\s]+/g, '') // Remove URLs
      .replace(/@[\w]+/g, '') // Remove mentions
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();
  }

  /**
   * Determine social media platform from URL
   */
  static getPlatformFromUrl(url: string): string {
    if (url.includes('twitter.com') || url.includes('x.com')) return 'twitter';
    if (url.includes('instagram.com')) return 'instagram';
    if (url.includes('facebook.com')) return 'facebook';
    if (url.includes('linkedin.com')) return 'linkedin';
    if (url.includes('tiktok.com')) return 'tiktok';
    return 'unknown';
  }
}

// Error Handling Utilities
export class ErrorUtils {
  /**
   * Create standardized error response
   */
  static createErrorResponse(error: Error, statusCode: number = 500): {
    statusCode: number;
    body: string;
    headers: Record<string, string>;
  } {
    return {
      statusCode,
      body: JSON.stringify({
        error: error.message,
        timestamp: DateUtils.now(),
      }),
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    };
  }

  /**
   * Safe JSON parse with error handling
   */
  static safeJsonParse<T>(jsonString: string, defaultValue: T): T {
    try {
      return JSON.parse(jsonString);
    } catch {
      return defaultValue;
    }
  }

  /**
