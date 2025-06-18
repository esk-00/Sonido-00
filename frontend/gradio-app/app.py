import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import boto3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SocialListeningApp:
    def __init__(self):
        self.setup_aws_clients()
        
    def setup_aws_clients(self):
        """AWS クライアントの初期化"""
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            self.posts_table_name = os.getenv('POSTS_TABLE_NAME', 'social-listening-posts')
            self.sentiment_table_name = os.getenv('SENTIMENT_TABLE_NAME', 'social-listening-sentiment')
            logger.info("AWS clients initialized successfully")
        except Exception as e:
            logger.error(f"AWS client initialization failed: {e}")
            self.dynamodb = None
            self.bedrock = None

    def search_posts(self, keyword: str, days: int = 7) -> pd.DataFrame:
        """投稿を検索（DynamoDBから）"""
        if not keyword.strip():
            return pd.DataFrame()
            
        if not self.dynamodb:
            return pd.DataFrame()
            
        try:
            table = self.dynamodb.Table(self.posts_table_name)
            
            # 日付範囲
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('content').contains(keyword) &
                               boto3.dynamodb.conditions.Attr('timestamp').between(
                                   int(start_date.timestamp()),
                                   int(end_date.timestamp())
                               )
            )
            
            items = response.get('Items', [])
            if not items:
                return pd.DataFrame()
                
            df = pd.DataFrame(items)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            return df.sort_values('timestamp', ascending=False)
            
        except Exception as e:
            logger.error(f"DynamoDB search failed: {e}")
            return pd.DataFrame()

    def analyze_sentiment_bedrock(self, text: str) -> dict:
        """Bedrockで感情分析"""
        if not self.bedrock:
            return {'sentiment': 'neutral', 'confidence': 0.5}
        
        try:
            prompt = f"""
            以下のテキストの感情を分析してください：
            {text}
            
            JSONで回答してください：
            {{"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0}}
            """
            
            response = self.bedrock.invoke_model(
                modelId="amazon.nova-micro-v1:0",
                body=json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 200,
                        "temperature": 0.1
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            output_text = result['results'][0]['outputText']
            
            # JSON部分を抽出
            import re
            json_match = re.search(r'\{.*\}', output_text)
            if json_match:
                return json.loads(json_match.group())
            
            return {'sentiment': 'neutral', 'confidence': 0.5}
            
        except Exception as e:
            logger.error(f"Bedrock analysis failed: {e}")
            return {'sentiment': 'neutral', 'confidence': 0.5}

    def create_sentiment_chart(self, df: pd.DataFrame) -> go.Figure:
        """感情分析チャート作成"""
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(height=400)
            return fig
        
        sentiment_counts = df['sentiment'].value_counts()
        total = len(df)
        
        colors = {
            'positive': '#4CAF50',  # Green
            'negative': '#F44336',  # Red
            'neutral': '#9E9E9E'    # Gray
        }
        
        labels = []
        values = []
        colors_list = []
        
        for sentiment in ['positive', 'negative', 'neutral']:
            count = sentiment_counts.get(sentiment, 0)
            if count > 0:
                percentage = (count / total * 100)
                
                if sentiment == 'positive':
                    label = f"ポジティブ<br>{count}件 ({percentage:.1f}%)"
                elif sentiment == 'negative':
                    label = f"ネガティブ<br>{count}件 ({percentage:.1f}%)"
                else:
                    label = f"ニュートラル<br>{count}件 ({percentage:.1f}%)"
                
                labels.append(label)
                values.append(count)
                colors_list.append(colors[sentiment])
        
        if not values:
            fig = go.Figure()
            fig.add_annotation(
                text="感情データがありません",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(height=400)
            return fig
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors_list,
            textinfo='label',
            textposition='inside',
            hole=0.3,
            textfont=dict(size=12, color="white")
        )])
        
        fig.update_layout(
            title=dict(
                text="感情分析結果",
                font=dict(size=20, color="#333"),
                x=0.5
            ),
            font=dict(family="Arial, sans-serif"),
            height=400,
            margin=dict(t=60, b=20, l=20, r=20),
            showlegend=False
        )
        
        return fig

    def create_timeline_chart(self, df: pd.DataFrame) -> go.Figure:
        """時系列チャート作成"""
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(height=400)
            return fig
        
        # 日別集計
        df['date'] = df['timestamp'].dt.date
        daily_counts = df.groupby(['date', 'sentiment']).size().unstack(fill_value=0)
        
        colors = {
            'positive': '#4CAF50',
            'negative': '#F44336',
            'neutral': '#9E9E9E'
        }
        
        sentiment_names = {
            'positive': 'ポジティブ',
            'negative': 'ネガティブ',
            'neutral': 'ニュートラル'
        }
        
        fig = go.Figure()
        
        for sentiment in ['positive', 'negative', 'neutral']:
            if sentiment in daily_counts.columns:
                fig.add_trace(go.Scatter(
                    x=daily_counts.index,
                    y=daily_counts[sentiment],
                    mode='lines+markers',
                    name=sentiment_names[sentiment],
                    line=dict(color=colors[sentiment], width=3),
                    marker=dict(size=8)
                ))
        
        fig.update_layout(
            title=dict(
                text="感情推移（日別）",
                font=dict(size=20, color="#333"),
                x=0.5
            ),
            xaxis_title="日付",
            yaxis_title="投稿数",
            font=dict(family="Arial, sans-serif"),
            height=400,
            margin=dict(t=60, b=50, l=50, r=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified'
        )
        
        return fig

    def generate_summary(self, df: pd.DataFrame, keyword: str) -> str:
        """分析サマリー生成"""
        if df.empty:
            return f"""
# 📊 分析結果 - {keyword}

## ❌ データが見つかりません

「{keyword}」に関する投稿データが見つかりませんでした。

### 考えられる原因:
- データベースに該当する投稿がない
- キーワードの表記が異なる
- 指定した期間にデータがない

### 改善案:
- 別のキーワードで検索してみる
- 期間を延長してみる
- より一般的な用語で検索してみる
"""
        
        total_posts = len(df)
        sentiment_dist = df['sentiment'].value_counts()
        
        positive_count = sentiment_dist.get('positive', 0)
        negative_count = sentiment_dist.get('negative', 0)
        neutral_count = sentiment_dist.get('neutral', 0)
        
        positive_pct = (positive_count / total_posts) * 100
        negative_pct = (negative_count / total_posts) * 100
        neutral_pct = (neutral_count / total_posts) * 100
        
        # 総合スコア計算
        overall_score = positive_pct - negative_pct
        
        # スコアに基づく評価
        if overall_score > 30:
            overall_status = "🟢 **非常に良好**"
        elif overall_score > 10:
            overall_status = "🟡 **良好**"
        elif overall_score > -10:
            overall_status = "🟡 **中立**"
        elif overall_score > -30:
            overall_status = "🟠 **注意が必要**"
        else:
            overall_status = "🔴 **要緊急対応**"

        # プラットフォーム分析
        platform_dist = df['platform'].value_counts()
        top_platform = platform_dist.index[0] if len(platform_dist) > 0 else "不明"
        
        # 時間分析
        latest_post = df['timestamp'].max()
        oldest_post = df['timestamp'].min()

        summary = f"""
# 📊 分析レポート - {keyword}

## 🎯 総合評価
{overall_status}  
**スコア**: {overall_score:+.1f}点

## 📈 基本統計
- **総投稿数**: {total_posts:,}件
- **分析期間**: {oldest_post.strftime('%Y年%m月%d日')} ～ {latest_post.strftime('%Y年%m月%d日')}

## 💭 感情分析結果
| 感情 | 件数 | 割合 |
|------|------|------|
| 🟢 ポジティブ | {positive_count:,}件 | {positive_pct:.1f}% |
| 🔴 ネガティブ | {negative_count:,}件 | {negative_pct:.1f}% |
| ⚪ ニュートラル | {neutral_count:,}件 | {neutral_pct:.1f}% |

## 📱 プラットフォーム分析
- **最も多い投稿元**: {top_platform}

---
*分析実行時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}*
"""
        
        return summary

    def create_interface(self):
        """Gradioインターフェース作成"""
        
        custom_css = """
        .gradio-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .main-header {
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        """
        
        with gr.Blocks(
            title="ソーシャルリスニングツール", 
            theme=gr.themes.Soft(),
            css=custom_css
        ) as app:
            
            gr.HTML("""
            <div class="main-header">
                <h1>🔍 ソーシャルリスニングツール</h1>
                <p>ブランドや商品に関するソーシャルメディアの投稿を分析し、リアルタイムで感情を可視化します</p>
            </div>
            """)
            
            with gr.Row():
                with gr.Column(scale=3):
                    keyword_input = gr.Textbox(
                        label="🔍 検索キーワード",
                        placeholder="例: iPhone, Nintendo, Starbucks, 新商品名など",
                        info="分析したいブランド、商品、サービス名を入力してください"
                    )
                with gr.Column(scale=1):
                    days_input = gr.Slider(
                        minimum=1,
                        maximum=30,
                        value=7,
                        step=1,
                        label="📅 分析期間（日）",
                        info="過去何日間のデータを分析するか"
                    )
                with gr.Column(scale=1):
                    search_btn = gr.Button(
                        "🚀 分析開始", 
                        variant="primary", 
                        size="lg"
                    )
            
            with gr.Row():
                with gr.Column():
                    sentiment_chart = gr.Plot(label="感情分析結果")
                with gr.Column():
                    timeline_chart = gr.Plot(label="感情推移")
            
            summary_output = gr.Markdown(
                label="📋 分析レポート",
                value="分析を開始するには、キーワードを入力して「分析開始」ボタンをクリックしてください。"
            )
            
            with gr.Accordion("📄 投稿データ詳細", open=False):
                posts_data = gr.Dataframe(
                    headers=["投稿内容", "プラットフォーム", "感情", "信頼度", "投稿時間"],
                    interactive=False,
                    wrap=True,
                    height=300
                )
            
            def perform_analysis(keyword, days):
                """分析実行"""
                if not keyword.strip():
                    empty_fig = go.Figure()
                    empty_fig.add_annotation(
                        text="キーワードを入力してください",
                        x=0.5, y=0.5, xref="paper", yref="paper",
                        showarrow=False, font=dict(size=16, color="red")
                    )
                    empty_fig.update_layout(height=400)
                    return empty_fig, empty_fig, "キーワードを入力してください", []
                
                # データ取得
                df = self.search_posts(keyword, days)
                
                # チャート生成
                sentiment_fig = self.create_sentiment_chart(df)
                timeline_fig = self.create_timeline_chart(df)
                
                # サマリー生成
                summary = self.generate_summary(df, keyword)
                
                # 投稿データの準備
                display_data = []
                if not df.empty:
                    for _, row in df.head(50).iterrows():
                        content_preview = row['content'][:150] + "..." if len(row['content']) > 150 else row['content']
                        display_data.append([
                            content_preview,
                            row.get('platform', 'unknown').title(),
                            "🟢 ポジティブ" if row['sentiment'] == 'positive' 
                            else "🔴 ネガティブ" if row['sentiment'] == 'negative' 
                            else "⚪ ニュートラル",
                            f"{row.get('confidence', 0):.1%}",
                            row['timestamp'].strftime('%Y-%m-%d %H:%M')
                        ])
                
                return sentiment_fig, timeline_fig, summary, display_data
            
            search_btn.click(
                fn=perform_analysis,
                inputs=[keyword_input, days_input],
                outputs=[sentiment_chart, timeline_chart, summary_output, posts_data]
            )
            
            keyword_input.submit(
                fn=perform_analysis,
                inputs=[keyword_input, days_input],
                outputs=[sentiment_chart, timeline_chart, summary_output, posts_data]
            )
        
        return app

def main():
    app_instance = SocialListeningApp()
    interface = app_instance.create_interface()
    
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        return interface
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
    
    return interface

if __name__ == "__main__":
    main()
