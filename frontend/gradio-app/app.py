import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import boto3
from typing import Dict, List, Tuple
import os
import requests
from transformers import pipeline
import asyncio
import concurrent.futures
from components.data_visualizer import DataVisualizer
from components.sentiment_analyzer import SentimentAnalyzer
from components.report_generator import ReportGenerator

class SocialListeningApp:
    def __init__(self):
        self.data_visualizer = DataVisualizer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.report_generator = ReportGenerator()
        
        # AWS設定
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.api_gateway_url = os.getenv('API_GATEWAY_URL')
        
        # Hugging Face モデル初期化
        self.sentiment_pipeline = pipeline("sentiment-analysis", 
                                          model="cardiffnlp/twitter-roberta-base-sentiment-latest")
        
        # データベーステーブル
        self.posts_table = self.dynamodb.Table(os.getenv('POSTS_TABLE', 'social-posts'))
        self.analytics_table = self.dynamodb.Table(os.getenv('ANALYTICS_TABLE', 'social-analytics'))

    def fetch_posts_data(self, keyword: str, date_range: int = 7) -> pd.DataFrame:
        """DynamoDBから投稿データを取得"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=date_range)
            
            response = self.posts_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('keyword').contains(keyword) &
                               boto3.dynamodb.conditions.Attr('timestamp').between(
                                   start_date.isoformat(), end_date.isoformat()
                               )
            )
            
            items = response['Items']
            df = pd.DataFrame(items)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp', ascending=False)
            
            return df
            
        except Exception as e:
            gr.Warning(f"データ取得エラー: {str(e)}")
            return pd.DataFrame()

    def analyze_sentiment_with_bedrock(self, text: str) -> Dict:
        """Bedrock Novaで感情分析"""
        try:
            prompt = f"""
            以下のテキストの感情を分析してください。
            
            テキスト: {text}
            
            以下の形式でJSONで回答してください:
            {{
                "sentiment": "positive/negative/neutral",
                "confidence": 0.0-1.0,
                "emotions": ["joy", "anger", "sadness", "fear", "surprise"],
                "summary": "分析結果の要約"
            }}
            """
            
            response = self.bedrock.invoke_model(
                modelId="amazon.nova-micro-v1:0",
                body=json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 500,
                        "temperature": 0.1
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            return json.loads(result['results'][0]['outputText'])
            
        except Exception as e:
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": [],
                "summary": f"分析エラー: {str(e)}"
            }

    def analyze_sentiment_with_huggingface(self, texts: List[str]) -> List[Dict]:
        """Hugging Faceで感情分析"""
        try:
            results = self.sentiment_pipeline(texts)
            return [
                {
                    "sentiment": result['label'].lower(),
                    "confidence": result['score'],
                    "text": text
                }
                for result, text in zip(results, texts)
            ]
        except Exception as e:
            gr.Warning(f"感情分析エラー: {str(e)}")
            return []

    def extract_posts(self, keyword: str, platform: str, count: int = 100) -> str:
        """API Gateway経由で投稿を抽出"""
        try:
            response = requests.post(
                f"{self.api_gateway_url}/extract-posts",
                json={
                    "keyword": keyword,
                    "platform": platform,
                    "count": count
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"✅ {result.get('extracted_count', 0)}件の投稿を抽出しました"
            else:
                return f"❌ 抽出エラー: {response.text}"
                
        except Exception as e:
            return f"❌ 抽出エラー: {str(e)}"

    def create_sentiment_chart(self, df: pd.DataFrame) -> go.Figure:
        """感情分析チャートを作成"""
        if df.empty:
            return go.Figure().add_annotation(text="データがありません", showarrow=False)
        
        sentiment_counts = df['sentiment'].value_counts()
        
        fig = px.pie(
            values=sentiment_counts.values,
            names=sentiment_counts.index,
            title="感情分析結果",
            color_discrete_map={
                'positive': '#2E8B57',
                'negative': '#DC143C',
                'neutral': '#708090'
            }
        )
        
        return fig

    def create_timeline_chart(self, df: pd.DataFrame) -> go.Figure:
        """時系列チャートを作成"""
        if df.empty:
            return go.Figure().add_annotation(text="データがありません", showarrow=False)
        
        # 日別投稿数
        daily_counts = df.groupby(df['timestamp'].dt.date).size().reset_index()
        daily_counts.columns = ['date', 'count']
        
        fig = px.line(
            daily_counts,
            x='date',
            y='count',
            title="日別投稿数推移",
            markers=True
        )
        
        fig.update_layout(
            xaxis_title="日付",
            yaxis_title="投稿数"
        )
        
        return fig

    def create_word_frequency_chart(self, df: pd.DataFrame) -> go.Figure:
        """単語頻度チャートを作成"""
        if df.empty:
            return go.Figure().add_annotation(text="データがありません", showarrow=False)
        
        # 簡単な単語分析（実際にはMeCabなどを使用）
        all_text = ' '.join(df['content'].astype(str))
        words = all_text.split()
        word_freq = pd.Series(words).value_counts().head(20)
        
        fig = px.bar(
            x=word_freq.values,
            y=word_freq.index,
            orientation='h',
            title="頻出単語TOP20"
        )
        
        fig.update_layout(
            xaxis_title="出現回数",
            yaxis_title="単語"
        )
        
        return fig

    def generate_summary_report(self, df: pd.DataFrame, keyword: str) -> str:
        """分析レポートを生成"""
        if df.empty:
            return "データがありません"
        
        total_posts = len(df)
        sentiment_dist = df['sentiment'].value_counts()
        
        # Bedrockでレポート生成
        prompt = f"""
        キーワード「{keyword}」に関するソーシャルメディア分析レポートを作成してください。
        
        データ概要:
        - 総投稿数: {total_posts}
        - 感情分布: {sentiment_dist.to_dict()}
        - 期間: {df['timestamp'].min()} - {df['timestamp'].max()}
        
        以下の点を含めて日本語でレポートを作成してください:
        1. 概要
        2. 感情分析結果
        3. 主要なトレンド
        4. 注目すべき投稿
        5. 改善提案
        """
        
        try:
            response = self.bedrock.invoke_model(
                modelId="amazon.nova-micro-v1:0",
                body=json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 1000,
                        "temperature": 0.3
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            return result['results'][0]['outputText']
            
        except Exception as e:
            return f"レポート生成エラー: {str(e)}"

    def build_interface(self):
        """Gradioインターフェースを構築"""
        
        with gr.Blocks(title="Social Listening Tool", theme=gr.themes.Soft()) as app:
            gr.Markdown("# 🔍 ソーシャルリスニングツール")
            gr.Markdown("SNSの投稿を分析して、ブランドや商品に関する評判を監視します")
            
            with gr.Tabs() as tabs:
                # データ抽出タブ
                with gr.TabItem("📊 データ抽出"):
                    with gr.Row():
                        with gr.Column():
                            keyword_input = gr.Textbox(
                                label="検索キーワード",
                                placeholder="例: 新商品, ブランド名",
                                value=""
                            )
                            platform_select = gr.Dropdown(
                                choices=["twitter", "instagram", "facebook", "all"],
                                label="プラットフォーム",
                                value="twitter"
                            )
                            count_slider = gr.Slider(
                                minimum=10,
                                maximum=1000,
                                value=100,
                                step=10,
                                label="抽出件数"
                            )
                            extract_btn = gr.Button("🔍 投稿を抽出", variant="primary")
                        
                        with gr.Column():
                            extract_status = gr.Textbox(
                                label="抽出状況",
                                interactive=False,
                                lines=3
                            )
                
                # 分析ダッシュボードタブ
                with gr.TabItem("📈 分析ダッシュボード"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            analysis_keyword = gr.Textbox(
                                label="分析キーワード",
                                placeholder="分析するキーワードを入力"
                            )
                            date_range = gr.Slider(
                                minimum=1,
                                maximum=30,
                                value=7,
                                step=1,
                                label="分析期間（日）"
                            )
                            analyze_btn = gr.Button("📊 分析実行", variant="primary")
                            refresh_btn = gr.Button("🔄 データ更新")
                        
                        with gr.Column(scale=3):
                            with gr.Row():
                                sentiment_chart = gr.Plot(label="感情分析")
                                timeline_chart = gr.Plot(label="時系列推移")
                            
                            word_freq_chart = gr.Plot(label="頻出単語")
                
                # 詳細レポートタブ
                with gr.TabItem("📋 詳細レポート"):
                    with gr.Row():
                        with gr.Column():
                            report_keyword = gr.Textbox(
                                label="レポート対象キーワード",
                                placeholder="レポートを生成するキーワード"
                            )
                            report_btn = gr.Button("📝 レポート生成", variant="primary")
                        
                        with gr.Column(scale=2):
                            report_output = gr.Textbox(
                                label="分析レポート",
                                lines=15,
                                interactive=False
                            )
                
                # 投稿データビューアタブ
                with gr.TabItem("💬 投稿データ"):
                    with gr.Row():
                        with gr.Column():
                            viewer_keyword = gr.Textbox(
                                label="表示キーワード",
                                placeholder="表示する投稿のキーワード"
                            )
                            load_posts_btn = gr.Button("📄 投稿を読み込み")
                        
                        with gr.Column(scale=3):
                            posts_dataframe = gr.Dataframe(
                                headers=["日時", "プラットフォーム", "内容", "感情", "信頼度"],
                                interactive=False
                            )
            
            # イベントハンドラー
            extract_btn.click(
                fn=self.extract_posts,
                inputs=[keyword_input, platform_select, count_slider],
                outputs=extract_status
            )
            
            def analyze_data(keyword, days):
                df = self.fetch_posts_data(keyword, days)
                
                sentiment_fig = self.create_sentiment_chart(df)
                timeline_fig = self.create_timeline_chart(df)
                word_freq_fig = self.create_word_frequency_chart(df)
                
                return sentiment_fig, timeline_fig, word_freq_fig
            
            analyze_btn.click(
                fn=analyze_data,
                inputs=[analysis_keyword, date_range],
                outputs=[sentiment_chart, timeline_chart, word_freq_chart]
            )
            
            refresh_btn.click(
                fn=analyze_data,
                inputs=[analysis_keyword, date_range],
                outputs=[sentiment_chart, timeline_chart, word_freq_chart]
            )
            
            report_btn.click(
                fn=lambda keyword: self.generate_summary_report(
                    self.fetch_posts_data(keyword), keyword
                ),
                inputs=report_keyword,
                outputs=report_output
            )
            
            def load_posts_table(keyword):
                df = self.fetch_posts_data(keyword)
                if df.empty:
                    return []
                
                # 表示用データフォーマット
                display_data = []
                for _, row in df.head(100).iterrows():
                    display_data.append([
                        row['timestamp'].strftime('%Y-%m-%d %H:%M'),
                        row.get('platform', 'unknown'),
                        row['content'][:100] + "..." if len(row['content']) > 100 else row['content'],
                        row.get('sentiment', 'unknown'),
                        f"{row.get('confidence', 0):.2f}"
                    ])
                
                return display_data
            
            load_posts_btn.click(
                fn=load_posts_table,
                inputs=viewer_keyword,
                outputs=posts_dataframe
            )
        
        return app

def main():
    app = SocialListeningApp()
    interface = app.build_interface()
    
    # Lambda環境の場合はinterfaceを返すだけ
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        return interface
    
    # ローカル環境の場合は起動
    port = int(os.getenv('PORT', 7860))
    host = os.getenv('HOST', '0.0.0.0')
    
    interface.launch(
        server_name=host,
        server_port=port,
        share=False,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
    
    return interface
if __name__ == "__main__":
    main()
