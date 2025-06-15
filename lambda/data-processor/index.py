import json
import boto3
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
from decimal import Decimal
import re

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWSクライアント初期化
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# 環境変数から設定取得
SENTIMENT_TABLE = 'social-listening-sentiment-results'
SUMMARY_TABLE = 'social-listening-summaries'
S3_BUCKET = 'social-listening-reports'

def lambda_handler(event, context):
    """
    データ処理Lambda関数のメインハンドラー
    """
    try:
        logger.info(f"Event received: {json.dumps(event)}")
        
        # 処理タイプの判定
        processing_type = event.get('type', 'auto')
        
        if processing_type == 'scheduled':
            # 定期実行（EventBridge経由）
            return process_scheduled_aggregation(event)
        elif processing_type == 'report':
            # レポート生成リクエスト
            return process_report_request(event)
        elif processing_type == 'realtime':
            # リアルタイム集計更新
            return process_realtime_update(event)
        else:
            # デフォルト：自動判定
            return process_auto_detection(event)
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }

def process_scheduled_aggregation(event: Dict) -> Dict:
    """
    定期集計処理（毎時/毎日実行）
    """
    try:
        period = event.get('period', 'hourly')  # hourly, daily, weekly
        current_time = datetime.utcnow()
        
        if period == 'hourly':
            start_time = current_time - timedelta(hours=1)
            aggregation_key = current_time.strftime('%Y-%m-%d-%H')
        elif period == 'daily':
            start_time = current_time - timedelta(days=1)
            aggregation_key = current_time.strftime('%Y-%m-%d')
        elif period == 'weekly':
            start_time = current_time - timedelta(weeks=1)
            aggregation_key = current_time.strftime('%Y-W%U')
        else:
            raise ValueError(f"Unknown period: {period}")
        
        # データ取得と分析
        sentiment_data = fetch_sentiment_data(start_time, current_time)
        
        if not sentiment_data:
            logger.info(f"No data found for {period} aggregation")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'No data for {period} aggregation',
                    'period': period,
                    'key': aggregation_key
                })
            }
        
        # 集計実行
        aggregated_data = aggregate_sentiment_data(sentiment_data, period)
        
        # トレンド分析
        trend_analysis = analyze_trends(aggregated_data, period)
        
        # 異常検知
        anomalies = detect_anomalies(aggregated_data, period)
        
        # 結果保存
        summary_result = {
            'summary_id': f"{period}_{aggregation_key}",
            'period': period,
            'aggregation_key': aggregation_key,
            'timestamp': current_time.isoformat(),
            'data_range': {
                'start': start_time.isoformat(),
                'end': current_time.isoformat()
            },
            'aggregated_data': aggregated_data,
            'trend_analysis': trend_analysis,
            'anomalies': anomalies,
            'total_posts': len(sentiment_data)
        }
        
        save_summary_data(summary_result)
        
        # アラート生成
        alerts = generate_alerts(anomalies, trend_analysis)
        if alerts:
            send_alerts(alerts)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'{period} aggregation completed',
                'summary_id': summary_result['summary_id'],
                'total_posts': summary_result['total_posts'],
                'alerts_generated': len(alerts)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in scheduled aggregation: {str(e)}")
        raise

def process_report_request(event: Dict) -> Dict:
    """
    レポート生成リクエスト処理
    """
    try:
        report_type = event.get('report_type', 'comprehensive')
        date_range = event.get('date_range', {})
        filters = event.get('filters', {})
        
        # 日付範囲の設定
        if 'start_date' in date_range and 'end_date' in date_range:
            start_time = datetime.fromisoformat(date_range['start_date'])
            end_time = datetime.fromisoformat(date_range['end_date'])
        else:
            # デフォルト：過去7日間
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
        
        # データ取得
        sentiment_data = fetch_sentiment_data(start_time, end_time, filters)
        
        # レポート生成
        if report_type == 'comprehensive':
            report = generate_comprehensive_report(sentiment_data, start_time, end_time)
        elif report_type == 'sentiment_summary':
            report = generate_sentiment_summary_report(sentiment_data, start_time, end_time)
        elif report_type == 'keyword_analysis':
            report = generate_keyword_analysis_report(sentiment_data, start_time, end_time)
        elif report_type == 'ai_insights':
            report = generate_ai_insights_report(sentiment_data, start_time, end_time)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        # S3に保存
        report_key = f"reports/{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        s3_url = save_report_to_s3(report, report_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Report generated successfully',
                'report_type': report_type,
                'report_url': s3_url,
                'data_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'total_posts': len(sentiment_data)
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise

def process_realtime_update(event: Dict) -> Dict:
    """
    リアルタイム集計更新処理
    """
    try:
        # 新しい分析結果を取得
        new_analyses = event.get('analyses', [])
        
        results = []
        for analysis in new_analyses:
            # 現在の集計データを更新
            update_result = update_realtime_aggregation(analysis)
            results.append(update_result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Realtime aggregation updated',
                'updated_analyses': len(results),
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in realtime update: {str(e)}")
        raise

def fetch_sentiment_data(start_time: datetime, end_time: datetime, filters: Dict = None) -> List[Dict]:
    """
    DynamoDBから感情分析データを取得
    """
    try:
        table = dynamodb.Table(SENTIMENT_TABLE)
        
        # 時間範囲でのスキャン（実際のプロダクションではGSIを使用推奨）
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('analysis_timestamp').between(
                start_time.isoformat(),
                end_time.isoformat()
            )
        )
        
        items = response['Items']
        
        # ページネーション処理
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('analysis_timestamp').between(
                    start_time.isoformat(),
                    end_time.isoformat()
                ),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
        
        # フィルター適用
        if filters:
            items = apply_filters(items, filters)
        
        return items
        
    except Exception as e:
        logger.error(f"Error fetching sentiment data: {str(e)}")
        return []

def aggregate_sentiment_data(data: List[Dict], period: str) -> Dict:
    """
    感情分析データの集計
    """
    if not data:
        return {}
    
    # 基本統計
    sentiments = [item.get('sentiment', 'unknown') for item in data]
    sentiment_counts = Counter(sentiments)
    
    # 信頼度統計
    confidences = [float(item.get('confidence', 0)) for item in data if item.get('confidence')]
    
    # 感情スコア統計
    emotions_data = defaultdict(list)
    for item in data:
        emotions = item.get('emotions', {})
        for emotion, score in emotions.items():
            if isinstance(score, (int, float, Decimal)):
                emotions_data[emotion].append(float(score))
    
    emotions_stats = {}
    for emotion, scores in emotions_data.items():
        if scores:
            emotions_stats[emotion] = {
                'mean': statistics.mean(scores),
                'median': statistics.median(scores),
                'std': statistics.stdev(scores) if len(scores) > 1 else 0,
                'min': min(scores),
                'max': max(scores)
            }
    
    # キーワード分析
    all_keywords = []
    for item in data:
        keywords = item.get('keywords', [])
        all_keywords.extend(keywords)
    
    keyword_counts = Counter(all_keywords)
    
    # 時間別分析
    hourly_counts = defaultdict(int)
    for item in data:
        timestamp = item.get('analysis_timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour_key = dt.strftime('%H')
                hourly_counts[hour_key] += 1
            except:
                continue
    
    # 言語分析
    languages = [item.get('metadata', {}).get('language', 'unknown') for item in data]
    language_counts = Counter(languages)
    
    return {
        'basic_stats': {
            'total_posts': len(data),
            'sentiment_distribution': dict(sentiment_counts),
            'sentiment_percentages': {
                k: round(v / len(data) * 100, 2) 
                for k, v in sentiment_counts.items()
            }
        },
        'confidence_stats': {
            'mean': statistics.mean(confidences) if confidences else 0,
            'median': statistics.median(confidences) if confidences else 0,
            'std': statistics.stdev(confidences) if len(confidences) > 1 else 0
        },
        'emotions_stats': emotions_stats,
        'keyword_analysis': {
            'top_keywords': dict(keyword_counts.most_common(20)),
            'total_unique_keywords': len(keyword_counts)
        },
        'temporal_analysis': {
            'hourly_distribution': dict(hourly_counts)
        },
        'language_analysis': {
            'distribution': dict(language_counts)
        }
    }

def analyze_trends(aggregated_data: Dict, period: str) -> Dict:
    """
    トレンド分析
    """
    try:
        # 過去データとの比較のため、同期間の履歴データを取得
        historical_data = fetch_historical_summaries(period, 5)  # 過去5期間
        
        trends = {}
        
        if historical_data:
            current_sentiment = aggregated_data.get('basic_stats', {}).get('sentiment_percentages', {})
            
            # 感情トレンド計算
            sentiment_trends = {}
            for sentiment in ['positive', 'negative', 'neutral']:
                current_pct = current_sentiment.get(sentiment, 0)
                historical_values = [
                    h.get('aggregated_data', {}).get('basic_stats', {}).get('sentiment_percentages', {}).get(sentiment, 0)
                    for h in historical_data
                ]
                
                if historical_values:
                    avg_historical = statistics.mean(historical_values)
                    change = current_pct - avg_historical
                    sentiment_trends[sentiment] = {
                        'current': current_pct,
                        'historical_avg': round(avg_historical, 2),
                        'change': round(change, 2),
                        'trend': 'increasing' if change > 5 else 'decreasing' if change < -5 else 'stable'
                    }
            
            trends['sentiment_trends'] = sentiment_trends
            
            # ボリュームトレンド
            current_volume = aggregated_data.get('basic_stats', {}).get('total_posts', 0)
            historical_volumes = [
                h.get('aggregated_data', {}).get('basic_stats', {}).get('total_posts', 0)
                for h in historical_data
            ]
            
            if historical_volumes:
                avg_historical_volume = statistics.mean(historical_volumes)
                volume_change = current_volume - avg_historical_volume
                trends['volume_trend'] = {
                    'current': current_volume,
                    'historical_avg': round(avg_historical_volume, 2),
                    'change': round(volume_change, 2),
                    'percentage_change': round((volume_change / avg_historical_volume * 100), 2) if avg_historical_volume > 0 else 0
                }
        
        return trends
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {str(e)}")
        return {}

def detect_anomalies(aggregated_data: Dict, period: str) -> List[Dict]:
    """
    異常検知
    """
    anomalies = []
    
    try:
        basic_stats = aggregated_data.get('basic_stats', {})
        
        # 異常に高いネガティブ感情の検知
        negative_pct = basic_stats.get('sentiment_percentages', {}).get('negative', 0)
        if negative_pct > 70:  # 70%以上がネガティブ
            anomalies.append({
                'type': 'high_negative_sentiment',
                'severity': 'high',
                'value': negative_pct,
                'threshold': 70,
                'description': f'異常に高いネガティブ感情: {negative_pct}%'
            })
        
        # 投稿量の急激な変化
        total_posts = basic_stats.get('total_posts', 0)
        if period == 'hourly' and total_posts > 1000:  # 1時間で1000投稿以上
            anomalies.append({
                'type': 'volume_spike',
                'severity': 'medium',
                'value': total_posts,
                'threshold': 1000,
                'description': f'投稿量の急増: {total_posts}投稿/時間'
            })
        
        # 信頼度の異常な低下
        confidence_stats = aggregated_data.get('confidence_stats', {})
        mean_confidence = confidence_stats.get('mean', 1.0)
        if mean_confidence < 0.5:  # 平均信頼度50%未満
            anomalies.append({
                'type': 'low_confidence',
                'severity': 'medium',
                'value': mean_confidence,
                'threshold': 0.5,
                'description': f'分析信頼度の低下: {round(mean_confidence*100, 1)}%'
            })
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {str(e)}")
    
    return anomalies

def generate_comprehensive_report(data: List[Dict], start_time: datetime, end_time: datetime) -> Dict:
    """
    包括的レポート生成
    """
    # データ集計
    aggregated = aggregate_sentiment_data(data, 'custom')
    
    # AI による洞察生成
    ai_insights = generate_ai_insights(data, aggregated)
    
    # 推奨アクション
    recommendations = generate_recommendations(aggregated, ai_insights)
    
    return {
        'report_type': 'comprehensive',
        'generated_at': datetime.utcnow().isoformat(),
        'data_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        },
        'summary': {
            'total_posts_analyzed': len(data),
            'analysis_period_days': (end_time - start_time).days,
            'overall_sentiment': get_dominant_sentiment(aggregated)
        },
        'detailed_analysis': aggregated,
        'ai_insights': ai_insights,
        'recommendations': recommendations,
        'raw_data_sample': data[:5] if data else []  # 最初の5件をサンプルとして含める
    }

def generate_ai_insights(data: List[Dict], aggregated: Dict) -> Dict:
    """
    AI による洞察生成
    """
    try:
        # 分析結果をまとめたプロンプト作成
        summary_text = f"""
        以下のソーシャルリスニング分析結果について、ビジネス洞察を提供してください：

        基本統計:
        - 総投稿数: {aggregated.get('basic_stats', {}).get('total_posts', 0)}
        - 感情分布: {json.dumps(aggregated.get('basic_stats', {}).get('sentiment_percentages', {}), ensure_ascii=False)}
        
        上位キーワード:
        {json.dumps(list(aggregated.get('keyword_analysis', {}).get('top_keywords', {}).items())[:10], ensure_ascii=False)}
        
        以下の観点で分析してください:
        1. 全体的な感情傾向の解釈
        2. 注目すべきキーワードやトピック
        3. ビジネスへの影響や機会
        4. 潜在的なリスクや課題
        5. 推奨される対応策
        """
        
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": summary_text
                }
            ],
            "temperature": 0.3
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        ai_insight_text = response_body['content'][0]['text']
        
        return {
            'insight_text': ai_insight_text,
            'generated_at': datetime.utcnow().isoformat(),
            'model_used': 'Claude Sonnet 4'
        }
        
    except Exception as e:
        logger.error(f"Error generating AI insights: {str(e)}")
        return {
            'insight_text': 'AI洞察の生成に失敗しました。手動での分析をお勧めします。',
            'error': str(e),
            'generated_at': datetime.utcnow().isoformat()
        }

def generate_recommendations(aggregated: Dict, ai_insights: Dict) -> List[Dict]:
    """
    推奨アクション生成
    """
    recommendations = []
    
    basic_stats = aggregated.get('basic_stats', {})
    sentiment_pct = basic_stats.get('sentiment_percentages', {})
    
    # ネガティブ感情が高い場合
    if sentiment_pct.get('negative', 0) > 40:
        recommendations.append({
            'priority': 'high',
            'category': 'sentiment_management',
            'action': 'ネガティブ感情への対応',
            'description': 'ネガティブ感情が40%を超えています。顧客サポートチームとの連携を強化し、問題の早期解決に取り組むことをお勧めします。',
            'estimated_impact': 'high'
        })
    
    # 投稿量が少ない場合
    if basic_stats.get('total_posts', 0) < 100:
        recommendations.append({
            'priority': 'medium',
            'category': 'engagement',
            'action': 'エンゲージメント向上',
            'description': '投稿量が少ないため、ブランド認知度やエンゲージメントの向上施策を検討してください。',
            'estimated_impact': 'medium'
        })
    
    # ポジティブ感情が高い場合
    if sentiment_pct.get('positive', 0) > 60:
        recommendations.append({
            'priority': 'low',
            'category': 'opportunity',
            'action': 'ポジティブ感情の活用',
            'description': 'ポジティブな反応が多いため、成功事例をマーケティング材料として活用することをお勧めします。',
            'estimated_impact': 'medium'
        })
    
    return recommendations

def save_summary_data(summary: Dict) -> None:
    """
    集計データをDynamoDBに保存
    """
    try:
        table = dynamodb.Table(SUMMARY_TABLE)
        
        # Decimal型変換（DynamoDB用）
        summary_item = json.loads(json.dumps(summary), parse_float=Decimal)
        
        # TTLを設定（90日後に自動削除）
        ttl = int((datetime.utcnow().timestamp()) + (90 * 24 * 3600))
        summary_item['ttl'] = ttl
        
        table.put_item(Item=summary_item)
        logger.info(f"Saved summary data: {summary['summary_id']}")
        
    except Exception as e:
        logger.error(f"Error saving summary data: {str(e)}")
        raise

def save_report_to_s3(report: Dict, report_key: str) -> str:
    """
    レポートをS3に保存
    """
    try:
        report_json = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=report_key,
            Body=report_json,
            ContentType='application/json',
            Metadata={
                'report-type': report.get('report_type', 'unknown'),
                'generated-at': datetime.utcnow().isoformat()
            }
        )
        
        # Pre-signed URL生成（24時間有効）
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': report_key},
            ExpiresIn=86400  # 24時間
        )
        
        logger.info(f"Report saved to S3: {report_key}")
        return url
        
    except Exception as e:
        logger.error(f"Error saving report to S3: {str(e)}")
        raise

def apply_filters(data: List[Dict], filters: Dict) -> List[Dict]:
    """
    データにフィルターを適用
    """
    filtered_data = data
    
    # 感情フィルター
    if 'sentiment' in filters:
        sentiment_filter = filters['sentiment']
        filtered_data = [item for item in filtered_data if item.get('sentiment') == sentiment_filter]
    
    # キーワードフィルター
    if 'keywords' in filters:
        keyword_filter = filters['keywords']
        filtered_data = [
            item for item in filtered_data 
            if any(kw in item.get('keywords', []) for kw in keyword_filter)
        ]
    
    # 信頼度フィルター
    if 'min_confidence' in filters:
        min_conf = float(filters['min_confidence'])
        filtered_data = [
            item for item in filtered_data 
            if float(item.get('confidence', 0)) >= min_conf
        ]
    
    return filtered_data

def fetch_historical_summaries(period: str, count: int) -> List[Dict]:
    """
    過去の集計データを取得
    """
    try:
        table = dynamodb.Table(SUMMARY_TABLE)
        
        # 期間タイプでフィルター
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('period').eq(period),
            Limit=count
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        logger.error(f"Error fetching historical summaries: {str(e)}")
        return []

def get_dominant_sentiment(aggregated: Dict) -> str:
    """
    主要な感情を取得
    """
    sentiment_pct = aggregated.get('basic_stats', {}).get('sentiment_percentages', {})
    
    if not sentiment_pct:
        return 'unknown'
    
    return max(sentiment_pct.items(), key=lambda x: x[1])[0]

def update_realtime_aggregation(analysis: Dict) -> Dict:
    """
    リアルタイム集計更新（この関数は簡略化版）
    """
    # 実際の実装では、現在の集計値を取得して更新する
    return {
        'post_id': analysis.get('post_id'),
        'updated': True,
        'timestamp': datetime.utcnow().isoformat()
    }

def generate_alerts(anomalies: List[Dict], trends: Dict) -> List[Dict]:
    """
    アラート生成
    """
    alerts = []
    
    # 異常値に基づくアラート
    for anomaly in anomalies:
        if anomaly.get('severity') == 'high':
            alerts.append({
                'type': 'anomaly_alert',
                'priority': 'high',
                'title': anomaly.get('description', 'Unknown anomaly'),
                'details': anomaly,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    return alerts

def send_alerts(alerts: List[Dict]) -> None:
    """
    アラート送信（SNS経由など）
    """
    # 実際の実装ではSNSやSlackに通知
    logger.info(f"Generated {len(alerts)} alerts")
    for alert in alerts:
        logger.warning(f"ALERT: {alert['title']}")

def generate_sentiment_summary_report(data: List[Dict], start_time: datetime, end_time: datetime) -> Dict:
    """
    感情サマリーレポート生成
    """
    aggregated = aggregate_sentiment_data(data, 'custom')
    
    return {
        'report_type': 'sentiment_summary',
        'generated_at': datetime.utcnow().isoformat(),
        'data_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        },
        'sentiment_overview': aggregated.get('basic_stats', {}),
        'emotion_details': aggregated.get('emotions_stats', {}),
        'confidence_analysis': aggregated.get('confidence_stats', {})
    }

def generate_keyword_analysis_report(data: List[Dict], start_time: datetime, end_time: datetime) -> Dict:
    """
    キーワード分析レポート生成
    """
    aggregated = aggregate_sentiment_data(data, 'custom')
    
    return {
        'report_type': 'keyword_analysis',
        'generated_at': datetime.utcnow().isoformat(),
        'data_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        },
        'keyword_insights': aggregated.get('keyword_analysis', {}),
        'temporal_patterns': aggregated.get('temporal_analysis', {}),
        'language_breakdown': aggregated.get('language_analysis', {})
    }

def generate_ai_insights_report(data: List[Dict], start_time: datetime, end_time: datetime) -> Dict:
    """
    AI洞察レポート生成
    """
    aggregated = aggregate_sentiment_data(data, 'custom')
    ai_insights = generate_ai_insights(data, aggregated)
    recommendations = generate_recommendations(aggregated, ai_insights)
    
    return {
        'report_type': 'ai_insights',
        'generated_at': datetime.utcnow().isoformat(),
        'data_range': {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        },
        'ai_analysis': ai_insights,
        'actionable_recommendations': recommendations,
        'key_metrics': {
            'total_posts': len(data),
            'dominant_sentiment': get_dominant_sentiment(aggregated),
            'confidence_score': aggregated.get('confidence_stats', {}).get('mean', 0)
        }
    }

def process_auto_detection(event: Dict) -> Dict:
    """
    自動判定処理（イベント内容に基づいて適切な処理を選択）
    """
    try:
        # EventBridgeからの定期実行を検出
        if event.get('source') == 'aws.events':
            return process_scheduled_aggregation({
                'type': 'scheduled',
                'period': 'hourly'
            })
        
        # SQSからのバッチ処理を検出
        elif 'Records' in event:
            analyses = []
            for record in event['Records']:
                if 'body' in record:
                    try:
                        body = json.loads(record['body'])
                        analyses.append(body)
                    except json.JSONDecodeError:
                        continue
            
            return process_realtime_update({
                'type': 'realtime',
                'analyses': analyses
            })
        
        # API Gateway からの直接呼び出しを検出
        elif 'httpMethod' in event:
            body = json.loads(event.get('body', '{}'))
            if 'report_type' in body:
                return process_report_request(body)
            else:
                return process_realtime_update(body)
        
        # デフォルト処理
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Unknown event format',
                    'message': 'Could not determine processing type from event'
                })
            }
            
    except Exception as e:
        logger.error(f"Error in auto detection: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Error in auto detection processing'
            })
        }
