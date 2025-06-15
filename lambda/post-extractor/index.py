import json
import os
import boto3
import requests
from datetime import datetime, timezone
import uuid
from typing import Dict, List, Any, Optional

# AWS サービス初期化
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# 環境変数取得
POSTS_TABLE_NAME = os.environ['POSTS_TABLE_NAME']
DATA_BUCKET_NAME = os.environ['DATA_BUCKET_NAME']
TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN', '')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY', '')

# DynamoDB テーブル
posts_table = dynamodb.Table(POSTS_TABLE_NAME)

def handler(event, context):
    """
    Lambda エントリーポイント
    """
    try:
        # HTTPリクエストの種類に応じて処理分岐
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        
        if http_method == 'POST' and 'extract' in path:
            return extract_posts(event)
        elif http_method == 'GET':
            return get_posts(event)
        else:
            return create_response(400, {'error': 'Unsupported method'})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': str(e)})

def extract_posts(event) -> Dict[str, Any]:
    """
    ソーシャルメディアから投稿を抜き出す
    """
    try:
        # リクエストボディ解析
        body = json.loads(event.get('body', '{}'))
        platform = body.get('platform', 'twitter').lower()
        query = body.get('query', '')
        max_results = min(body.get('max_results', 10), 100)  # 最大100件
        
        if not query:
            return create_response(400, {'error': 'Query parameter is required'})
        
        posts = []
        
        if platform == 'twitter':
            posts = extract_twitter_posts(query, max_results)
        elif platform == 'demo':
            # デモ用のダミーデータ
            posts = generate_demo_posts(query, max_results)
        else:
            return create_response(400, {'error': f'Unsupported platform: {platform}'})
        
        # DynamoDB に保存
        saved_posts = []
        for post in posts:
            saved_post = save_post_to_dynamodb(post)
            saved_posts.append(saved_post)
        
        return create_response(200, {
            'message': f'Successfully extracted {len(saved_posts)} posts',
            'posts': saved_posts,
            'platform': platform,
            'query': query
        })
        
    except Exception as e:
        print(f"Extract posts error: {str(e)}")
        return create_response(500, {'error': f'Failed to extract posts: {str(e)}'})

def extract_twitter_posts(query: str, max_results: int) -> List[Dict[str, Any]]:
    """
    Twitter API v2 を使用して投稿を抜き出す
    """
    if not TWITTER_BEARER_TOKEN:
        print("Twitter Bearer Token not configured, using demo data")
        return generate_demo_posts(query, max_results)
    
    try:
        # Twitter API v2 エンドポイント
        url = "https://api.twitter.com/2/tweets/search/recent"
        
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,author_id,public_metrics,context_annotations,lang',
            'user.fields': 'name,username,verified,public_metrics',
            'expansions': 'author_id'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Twitter API error: {response.status_code} - {response.text}")
            return generate_demo_posts(query, max_results)
        
        data = response.json()
        posts = []
        
        # ユーザー情報のマッピング作成
        users = {}
        if 'includes' in data and 'users' in data['includes']:
            for user in data['includes']['users']:
                users[user['id']] = user
        
        # 投稿データ変換
        if 'data' in data:
            for tweet in data['data']:
                user = users.get(tweet['author_id'], {})
                
                post = {
                    'platform': 'twitter',
                    'original_id': tweet['id'],
                    'text': tweet['text'],
                    'author': {
                        'id': tweet['author_id'],
                        'name': user.get('name', 'Unknown'),
                        'username': user.get('username', 'unknown'),
                        'verified': user.get('verified', False),
                        'followers_count': user.get('public_metrics', {}).get('followers_count', 0)
                    },
                    'created_at': tweet['created_at'],
                    'metrics': {
                        'retweet_count': tweet.get('public_metrics', {}).get('retweet_count', 0),
                        'like_count': tweet.get('public_metrics', {}).get('like_count', 0),
                        'reply_count': tweet.get('public_metrics', {}).get('reply_count', 0),
                        'quote_count': tweet.get('public_metrics', {}).get('quote_count', 0)
                    },
                    'lang': tweet.get('lang', 'unknown'),
                    'query': query
                }
                posts.append(post)
        
        return posts
        
    except Exception as e:
        print(f"Twitter extraction error: {str(e)}")
        return generate_demo_posts(query, max_results)

def generate_demo_posts(query: str, max_results: int) -> List[Dict[str, Any]]:
    """
    デモ用のダミー投稿データを生成
    """
    demo_texts = [
        f"Just tried the new {query} feature and it's amazing! 🚀",
        f"What do you think about {query}? I'm not sure if it's worth it...",
        f"Love the {query} update! Makes everything so much easier 💖",
        f"Anyone else having issues with {query}? Need help!",
        f"{query} is trending! Here's my honest review...",
        f"Can't believe how good {query} has become. Highly recommend! ⭐",
        f"Mixed feelings about {query}. Some good points, some bad.",
        f"Breaking: Major update to {query} just dropped! 🔥",
        f"{query} vs competitors - here's what I found out",
        f"Tutorial: How to get the most out of {query}"
    ]
    
    posts = []
    for i in range(min(max_results, len(demo_texts))):
        timestamp = datetime.now(timezone.utc)
        
        post = {
            'platform': 'demo',
            'original_id': f'demo_{uuid.uuid4().hex[:8]}',
            'text': demo_texts[i],
            'author': {
                'id': f'user_{i + 1}',
                'name': f'Demo User {i + 1}',
                'username': f'demouser{i + 1}',
                'verified': i % 3 == 0,  # 3人に1人を認証済みに
                'followers_count': (i + 1) * 1000
            },
            'created_at': timestamp.isoformat(),
            'metrics': {
                'retweet_count': i * 5,
                'like_count': i * 15,
                'reply_count': i * 3,
                'quote_count': i * 2
            },
            'lang': 'en',
            'query': query
        }
        posts.append(post)
    
    return posts

def save_post_to_dynamodb(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    投稿をDynamoDBに保存
    """
    try:
        # 一意のpostIdを生成
        post_id = f"{post['platform']}_{post['original_id']}"
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        # DynamoDB用のアイテム作成
        db_item = {
            'postId': post_id,
            'timestamp': timestamp,
            'platform': post['platform'],
            'originalId': post['original_id'],
            'text': post['text'],
            'author': post['author'],
            'createdAt': post['created_at'],
            'metrics': post['metrics'],
            'lang': post['lang'],
            'query': post['query'],
            'extracted_at': datetime.now(timezone.utc).isoformat()
        }
        
        # DynamoDBに挿入
        posts_table.put_item(Item=db_item)
        
        return {
            'postId': post_id,
            'platform': post['platform'],
            'text': post['text'][:100] + '...' if len(post['text']) > 100 else post['text'],
            'author': post['author']['name'],
            'timestamp': timestamp
        }
        
    except Exception as e:
        print(f"DynamoDB save error: {str(e)}")
        raise e

def get_posts(event) -> Dict[str, Any]:
    """
    保存された投稿を取得
    """
    try:
        # クエリパラメータ取得
        query_params = event.get('queryStringParameters') or {}
        platform = query_params.get('platform')
        limit = min(int(query_params.get('limit', 50)), 100)
        
        # DynamoDB スキャン
        scan_kwargs = {
            'Limit': limit
        }
        
        if platform:
            scan_kwargs['FilterExpression'] = 'platform = :platform'
            scan_kwargs['ExpressionAttributeValues'] = {':platform': platform}
        
        response = posts_table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
        # レスポンス用にデータ整形
        posts = []
        for item in items:
            posts.append({
                'postId': item['postId'],
                'platform': item['platform'],
                'text': item['text'],
                'author': item['author'],
                'metrics': item['metrics'],
                'createdAt': item['createdAt'],
                'query': item.get('query', ''),
                'extractedAt': item.get('extracted_at', '')
            })
        
        # 新しい順でソート
        posts.sort(key=lambda x: x.get('extractedAt', ''), reverse=True)
        
        return create_response(200, {
            'posts': posts,
            'count': len(posts),
            'platform': platform
        })
        
    except Exception as e:
        print(f"Get posts error: {str(e)}")
        return create_response(500, {'error': f'Failed to get posts: {str(e)}'})

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    HTTP レスポンス作成
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body, ensure_ascii=False, default=str)
    }
