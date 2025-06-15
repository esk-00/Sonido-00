import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWSクライアント初期化
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """
    感情分析Lambda関数のメインハンドラー
    """
    try:
        logger.info(f"Event received: {json.dumps(event)}")
        
        # イベントソースに応じた処理分岐
        if 'Records' in event:
            # SQSまたはDynamoDB Streamsからの呼び出し
            return process_batch_records(event['Records'])
        elif 'posts' in event:
            # 直接呼び出し（API Gateway経由）
            return process_direct_request(event)
        else:
            raise ValueError("Unknown event format")
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }

def process_batch_records(records: List[Dict]) -> Dict:
    """
    バッチレコード処理
    """
    results = []
    errors = []
    
    for record in records:
        try:
            # レコードからデータ抽出
            if 'body' in record:  # SQS
                post_data = json.loads(record['body'])
            elif 'dynamodb' in record:  # DynamoDB Streams
                post_data = extract_from_dynamodb_record(record)
            else:
                continue
                
            # 感情分析実行
            analysis_result = analyze_sentiment(post_data)
            results.append(analysis_result)
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            errors.append({
                'record_id': record.get('messageId', 'unknown'),
                'error': str(e)
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(results),
            'errors': len(errors),
            'results': results,
            'error_details': errors
        })
    }

def process_direct_request(event: Dict) -> Dict:
    """
    直接リクエスト処理（API Gateway経由）
    """
    posts = event.get('posts', [])
    
    if not posts:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'No posts provided',
                'message': 'Please provide posts array'
            })
        }
    
    results = []
    
    for post in posts:
        try:
            analysis_result = analyze_sentiment(post)
            results.append(analysis_result)
        except Exception as e:
            logger.error(f"Error analyzing post {post.get('id', 'unknown')}: {str(e)}")
            results.append({
                'post_id': post.get('id'),
                'error': str(e),
                'sentiment': 'unknown'
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'results': results,
            'total_analyzed': len(results)
        })
    }

def analyze_sentiment(post_data: Dict) -> Dict:
    """
    投稿の感情分析を実行
    """
    try:
        post_id = post_data.get('id', 'unknown')
        text = post_data.get('text', '').strip()
        
        if not text:
            return create_error_result(post_id, "Empty text")
        
        # テキストの前処理
        cleaned_text = preprocess_text(text)
        
        # Bedrock Nova/Claude Sonnet 4で感情分析
        sentiment_result = call_bedrock_for_sentiment(cleaned_text)
        
        # 結果の構造化
        structured_result = {
            'post_id': post_id,
            'original_text': text,
            'cleaned_text': cleaned_text,
            'sentiment': sentiment_result.get('sentiment', 'unknown'),
            'confidence': sentiment_result.get('confidence', 0.0),
            'emotions': sentiment_result.get('emotions', {}),
            'keywords': extract_keywords(text),
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'metadata': {
                'text_length': len(text),
                'language': detect_language(text),
                'has_mentions': '@' in text,
                'has_hashtags': '#' in text,
                'has_urls': 'http' in text.lower()
            }
        }
        
        # DynamoDBに結果保存
        save_analysis_result(structured_result)
        
        return structured_result
        
    except Exception as e:
        logger.error(f"Error in analyze_sentiment: {str(e)}")
        return create_error_result(post_data.get('id', 'unknown'), str(e))

def call_bedrock_for_sentiment(text: str) -> Dict:
    """
    Bedrock API呼び出しで感情分析実行
    """
    try:
        # Claude Sonnet 4を使用
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        prompt = f"""以下のテキストの感情分析を行ってください。

テキスト: "{text}"

以下の形式でJSONで回答してください：
{{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0の数値,
    "emotions": {{
        "joy": 0.0-1.0の数値,
        "anger": 0.0-1.0の数値,
        "sadness": 0.0-1.0の数値,
        "fear": 0.0-1.0の数値,
        "surprise": 0.0-1.0の数値,
        "disgust": 0.0-1.0の数値
    }},
    "reasoning": "分析の理由を簡潔に説明"
}}

注意点：
- 日本語のニュアンスを考慮してください
- ソーシャルメディア特有の表現（絵文字、スラング等）も考慮してください
- 皮肉や反語表現にも注意してください"""

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # JSON部分を抽出
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            logger.warning("Could not extract JSON from Bedrock response")
            return parse_fallback_response(content)
            
    except Exception as e:
        logger.error(f"Error calling Bedrock: {str(e)}")
        # フォールバック：簡単なキーワードベース分析
        return perform_keyword_based_sentiment(text)

def preprocess_text(text: str) -> str:
    """
    テキストの前処理
    """
    # URLを除去
    text = re.sub(r'https?://[^\s]+', '', text)
    
    # 過度な空白を除去
    text = re.sub(r'\s+', ' ', text)
    
    # 前後の空白を除去
    text = text.strip()
    
    return text

def extract_keywords(text: str) -> List[str]:
    """
    キーワード抽出（簡単な実装）
    """
    # ハッシュタグ抽出
    hashtags = re.findall(r'#\w+', text)
    
    # メンション抽出
    mentions = re.findall(r'@\w+', text)
    
    # 基本的な感情キーワード
    positive_keywords = ['良い', '素晴らしい', '最高', '嬉しい', '楽しい', '感謝', 'ありがとう']
    negative_keywords = ['悪い', 'ひどい', '最悪', '悲しい', '怒り', '不満', '困る']
    
    found_keywords = []
    text_lower = text.lower()
    
    for keyword in positive_keywords + negative_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    return list(set(hashtags + mentions + found_keywords))

def detect_language(text: str) -> str:
    """
    簡単な言語検出
    """
    # ひらがな・カタカナ・漢字が含まれていれば日本語と判定
    if re.search(r'[ひらがな-んカタカナ-ヶ一-龯]', text):
        return 'ja'
    elif re.search(r'[a-zA-Z]', text):
        return 'en'
    else:
        return 'unknown'

def perform_keyword_based_sentiment(text: str) -> Dict:
    """
    キーワードベースの感情分析（フォールバック）
    """
    positive_words = ['良い', '素晴らしい', '最高', '嬉しい', '楽しい', '感謝', 'good', 'great', 'awesome', 'happy']
    negative_words = ['悪い', 'ひどい', '最悪', '悲しい', '怒り', '不満', 'bad', 'terrible', 'awful', 'sad', 'angry']
    
    text_lower = text.lower()
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        sentiment = 'positive'
        confidence = min(0.8, 0.5 + (positive_count - negative_count) * 0.1)
    elif negative_count > positive_count:
        sentiment = 'negative'
        confidence = min(0.8, 0.5 + (negative_count - positive_count) * 0.1)
    else:
        sentiment = 'neutral'
        confidence = 0.5
    
    return {
        'sentiment': sentiment,
        'confidence': confidence,
        'emotions': {
            'joy': 0.7 if sentiment == 'positive' else 0.2,
            'anger': 0.7 if sentiment == 'negative' else 0.1,
            'sadness': 0.6 if sentiment == 'negative' else 0.1,
            'fear': 0.3,
            'surprise': 0.2,
            'disgust': 0.5 if sentiment == 'negative' else 0.1
        },
        'reasoning': 'Keyword-based analysis (fallback method)'
    }

def parse_fallback_response(content: str) -> Dict:
    """
    JSON解析失敗時のフォールバック
    """
    # 基本的なパターンマッチングで感情を推定
    content_lower = content.lower()
    
    if 'positive' in content_lower:
        sentiment = 'positive'
    elif 'negative' in content_lower:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    
    return {
        'sentiment': sentiment,
        'confidence': 0.5,
        'emotions': {
            'joy': 0.5,
            'anger': 0.3,
            'sadness': 0.3,
            'fear': 0.2,
            'surprise': 0.2,
            'disgust': 0.2
        },
        'reasoning': 'Fallback parsing from Bedrock response'
    }

def save_analysis_result(result: Dict) -> None:
    """
    分析結果をDynamoDBに保存
    """
    try:
        table_name = 'social-listening-sentiment-results'
        table = dynamodb.Table(table_name)
        
        # TTLを設定（30日後に自動削除）
        ttl = int((datetime.utcnow().timestamp()) + (30 * 24 * 3600))
        
        item = {
            **result,
            'ttl': ttl
        }
        
        table.put_item(Item=item)
        logger.info(f"Saved analysis result for post {result['post_id']}")
        
    except Exception as e:
        logger.error(f"Error saving to DynamoDB: {str(e)}")
        # 保存エラーでも処理は継続

def extract_from_dynamodb_record(record: Dict) -> Dict:
    """
    DynamoDB Streamレコードからデータ抽出
    """
    if record['eventName'] in ['INSERT', 'MODIFY']:
        return record['dynamodb']['NewImage']
    else:
        return record['dynamodb']['OldImage']

def create_error_result(post_id: str, error_message: str) -> Dict:
    """
    エラー結果の作成
    """
    return {
        'post_id': post_id,
        'error': error_message,
        'sentiment': 'unknown',
        'confidence': 0.0,
        'emotions': {},
        'keywords': [],
        'analysis_timestamp': datetime.utcnow().isoformat(),
        'metadata': {}
    }
