import boto3
import json
from typing import Dict, List, Optional, Tuple
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime

class SentimentAnalyzer:
    """感情分析を担当するクラス"""
    
    def __init__(self):
        # AWS Bedrock設定
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Hugging Face モデル設定
        self.hf_model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        self.tokenizer = AutoTokenizer.from_pretrained(self.hf_model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.hf_model_name)
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=self.model,
            tokenizer=self.tokenizer,
            device=-1  # CPU使用
        )
        
        # 日本語感情分析用モデル
        self.japanese_pipeline = pipeline(
            "sentiment-analysis",
            model="jarvisx17/japanese-sentiment-analysis"
        )
        
        # 感情ラベルマッピング
        self.label_mapping = {
            'LABEL_0': 'negative',
            'LABEL_1': 'neutral', 
            'LABEL_2': 'positive',
            'NEGATIVE': 'negative',
            'NEUTRAL': 'neutral',
            'POSITIVE': 'positive'
        }

    def analyze_with_bedrock(self, text: str, model_id: str = "amazon.nova-micro-v1:0") -> Dict:
        """Bedrock Novaで感情分析を実行"""
        try:
            prompt = f"""
            以下のテキストの感情を詳細に分析してください。

            テキスト: {text}

            以下の形式でJSONで回答してください:
            {{
                "sentiment": "positive/negative/neutral",
                "confidence": 0.0-1.0の信頼度,
                "emotions": ["joy", "anger", "sadness", "fear", "surprise", "disgust"],
                "keywords": ["重要なキーワード"],
                "summary": "分析結果の要約",
                "reasoning": "判定理由"
            }}
            
            回答はJSONのみで、他の文章は含めないでください。
            """
            
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            result_text = response_body['results'][0]['outputText']
            
            # JSONを抽出
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("JSONレスポンスが見つかりません")
                
        except Exception as e:
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": [],
                "keywords": [],
                "summary": f"分析エラー: {str(e)}",
                "reasoning": "エラーにより分析できませんでした"
            }

    def analyze_with_huggingface(self, texts: List[str], language: str = "en") -> List[Dict]:
        """Hugging Faceモデルで感情分析を実行"""
        try:
            # 言語に応じてパイプラインを選択
            pipeline_to_use = self.japanese_pipeline if language == "ja" else self.sentiment_pipeline
            
            results = []
            for text in texts:
                # テキストの前処理
                cleaned_text = self.preprocess_text(text)
                
                if not cleaned_text.strip():
                    results.append({
                        "sentiment": "neutral",
                        "confidence": 0.5,
                        "text": text,
                        "error": "空のテキスト"
                    })
                    continue
                
                # 感情分析実行
                prediction = pipeline_to_use(cleaned_text)
                
                if isinstance(prediction, list) and len(prediction) > 0:
                    pred = prediction[0]
                    sentiment = self.label_mapping.get(pred['label'], pred['label'].lower())
                    
                    results.append({
                        "sentiment": sentiment,
                        "confidence": pred['score'],
                        "text": text,
                        "processed_text": cleaned_text
                    })
                else:
                    results.append({
                        "sentiment": "neutral",
                        "confidence": 0.5,
                        "text": text,
                        "error": "予測結果が不正"
                    })
            
            return results
            
        except Exception as e:
            return [{
                "sentiment": "neutral",
                "confidence": 0.5,
                "text": text,
                "error": str(e)
            } for text in texts]

    def batch_analyze(self, df: pd.DataFrame, text_column: str = 'content', 
                     method: str = 'huggingface', language: str = 'auto') -> pd.DataFrame:
        """データフレームの感情分析をバッチ処理"""
        if df.empty or text_column not in df.columns:
            return df
        
        texts = df[text_column].astype(str).tolist()
        
        # 言語自動検出
        if language == 'auto':
            language = self.detect_language(texts[0] if texts else "")
        
        if method == 'bedrock':
            # Bedrockは1件ずつ処理（コスト削減のため）
            results = []
            for text in texts[:10]:  # 最初の10件のみ
                result = self.analyze_with_bedrock(text)
                results.append(result)
            
            # 残りはHugging Faceで処理
            if len(texts) > 10:
                hf_results = self.analyze_with_huggingface(texts[10:], language)
                for hf_result in hf_results:
                    results.append({
                        "sentiment": hf_result["sentiment"],
                        "confidence": hf_result["confidence"],
                        "emotions": [],
                        "keywords": [],
                        "summary": "",
                        "reasoning": "Hugging Face分析"
                    })
        else:
            # Hugging Faceで全て処理
            hf_results = self.analyze_with_huggingface(texts, language)
            results = [{
                "sentiment": result["sentiment"],
                "confidence": result["confidence"],
                "emotions": [],
                "keywords": [],
                "summary": "",
                "reasoning": "Hugging Face分析"
            } for result in hf_results]
        
        # 結果をデータフレームに追加
        df_result = df.copy()
        df_result['sentiment'] = [r['sentiment'] for r in results]
        df_result['confidence'] = [r['confidence'] for r in results]
        df_result['emotions'] = [r['emotions'] for r in results]
        df_result['analysis_keywords'] = [r['keywords'] for r in results]
        df_result['sentiment_summary'] = [r['summary'] for r in results]
        df_result['analysis_timestamp'] = datetime.now().isoformat()
        
        return df_result

    def get_sentiment_trends(self, df: pd.DataFrame, time_column: str = 'timestamp') -> Dict:
        """感情の時系列トレンドを分析"""
        if df.empty or 'sentiment' not in df.columns:
            return {}
        
        df[time_column] = pd.to_datetime(df[time_column])
        
        # 日別感情集計
        daily_sentiment = df.groupby([df[time_column].dt.date, 'sentiment']).size().unstack(fill_value=0)
        
        # トレンド計算
        trends = {}
        for sentiment in ['positive', 'negative', 'neutral']:
            if sentiment in daily_sentiment.columns:
                values = daily_sentiment[sentiment].values
                if len(values) > 1:
                    # 線形回帰で傾向を計算
                    x = np.arange(len(values))
                    slope = np.polyfit(x, values, 1)[0]
                    trends[sentiment] = {
                        'slope': slope,
                        'direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
                        'recent_average': np.mean(values[-3:]) if len(values) >= 3 else np.mean(values)
                    }
        
        return trends

    def calculate_sentiment_score(self, df: pd.DataFrame) -> float:
        """総合感情スコアを計算（-1から1の範囲）"""
        if df.empty or 'sentiment' not in df.columns:
            return 0.0
        
        sentiment_counts = df['sentiment'].value_counts()
        total = len(df)
        
        positive_ratio = sentiment_counts.get('positive', 0) / total
        negative_ratio = sentiment_counts.get('negative', 0) / total
        
        # 重み付け感情スコア
        score = positive_ratio - negative_ratio
        
        # 信頼度による重み付け
        if 'confidence' in df.columns:
            weighted_score = 0
            total_weight = 0
            
            for _, row in df.iterrows():
                weight = row['confidence']
                if row['sentiment'] == 'positive':
                    weighted_score += weight
                elif row['sentiment'] == 'negative':
                    weighted_score -= weight
                total_weight += weight
            
            if total_weight > 0:
                score = weighted_score / total_weight
        
        return max(-1, min(1, score))

    def detect_language(self, text: str) -> str:
        """テキストの言語を検出（簡易版）"""
        # 日本語文字が含まれているかチェック
        japanese_chars = re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text)
        if japanese_chars:
            return 'ja'
        else:
            return 'en'

    def preprocess_text(self, text: str) -> str:
        """テキストの前処理"""
        if not isinstance(text, str):
            text = str(text)
        
        # URLを除去
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # メンション(@user)を除去
        text = re.sub(r'@[A-Za-z0-9_]+', '', text)
        
        # ハッシュタグの#を除去（内容は残す）
        text = re.sub(r'#', '', text)
        
        # 余分な空白を除去
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def get_emotion_breakdown(self, df: pd.DataFrame) -> Dict:
        """感情の詳細分析結果を取得"""
        if df.empty or 'emotions' not in df.columns:
            return {}
        
        emotion_counts = {}
        total_posts = len(df)
        
        for emotions_list in df['emotions']:
            if isinstance(emotions_list, list):
                for emotion in emotions_list:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # パーセンテージに変換
        emotion_percentages = {
            emotion: (count / total_posts) * 100 
            for emotion, count in emotion_counts.items()
        }
        
        return emotion_percentages

    def generate_insights(self, df: pd.DataFrame) -> Dict:
        """感情分析結果から洞察を生成"""
        if df.empty:
            return {"insights": [], "recommendations": []}
        
        insights = []
        recommendations = []
        
        # 基本統計
        sentiment_dist = df['sentiment'].value_counts(normalize=True)
        total_posts = len(df)
        
        # インサイト生成
        if sentiment_dist.get('positive', 0) > 0.6:
            insights.append("全体的にポジティブな反応が多く見られます")
            recommendations.append("好評な要素をさらに強化することを検討してください")
        elif sentiment_dist.get('negative', 0) > 0.4:
            insights.append("ネガティブな反応が多く見られます")
            recommendations.append("問題点の特定と改善策の検討が必要です")
        
        # トレンド分析
        trends = self.get_sentiment_trends(df)
        for sentiment, trend_data in trends.items():
            if trend_data['direction'] == 'increasing' and sentiment == 'negative':
                insights.append(f"ネガティブな感情が増加傾向にあります")
                recommendations.append("早急な対応が必要な可能性があります")
        
        return {
            "insights": insights,
            "recommendations": recommendations,
            "total_analyzed": total_posts,
            "sentiment_breakdown": sentiment_dist.to_dict(),
            "overall_score": self.calculate_sentiment_score(df)
        }
