import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime, timedelta

class DataVisualizer:
    """データ可視化を担当するクラス"""
    
    def __init__(self):
        self.color_scheme = {
            'positive': '#2E8B57',  # Sea Green
            'negative': '#DC143C',  # Crimson
            'neutral': '#708090',   # Slate Gray
            'primary': '#1f77b4',   # Blue
            'secondary': '#ff7f0e', # Orange
            'accent': '#2ca02c'     # Green
        }
    
    def create_sentiment_distribution(self, df: pd.DataFrame) -> go.Figure:
        """感情分布の円グラフを作成"""
        if df.empty:
            return self._create_empty_chart("感情分析データがありません")
        
        sentiment_counts = df['sentiment'].value_counts()
        
        fig = px.pie(
            values=sentiment_counts.values,
            names=sentiment_counts.index,
            title="感情分析結果の分布",
            color_discrete_map=self.color_scheme,
            hole=0.4  # ドーナツ型
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>件数: %{value}<br>割合: %{percent}<extra></extra>'
        )
        
        fig.update_layout(
            title_x=0.5,
            font=dict(size=12),
            showlegend=True,
            height=400
        )
        
        return fig
    
    def create_timeline_analysis(self, df: pd.DataFrame, groupby: str = 'day') -> go.Figure:
        """時系列分析チャートを作成"""
        if df.empty:
            return self._create_empty_chart("時系列データがありません")
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # グループ化の設定
        if groupby == 'hour':
            df['time_group'] = df['timestamp'].dt.floor('H')
            title = "時間別投稿数推移"
            x_title = "時間"
        elif groupby == 'day':
            df['time_group'] = df['timestamp'].dt.date
            title = "日別投稿数推移"
            x_title = "日付"
        else:
            df['time_group'] = df['timestamp'].dt.to_period('W').dt.start_time
            title = "週別投稿数推移"
            x_title = "週"
        
        # 感情別の時系列データ
        timeline_data = df.groupby(['time_group', 'sentiment']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        
        for sentiment in timeline_data.columns:
            fig.add_trace(go.Scatter(
                x=timeline_data.index,
                y=timeline_data[sentiment],
                mode='lines+markers',
                name=sentiment,
                line=dict(color=self.color_scheme.get(sentiment, '#000000')),
                hovertemplate=f'<b>{sentiment}</b><br>%{{x}}<br>投稿数: %{{y}}<extra></extra>'
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title="投稿数",
            hovermode='x unified',
            height=400
        )
        
        return fig
    
    def create_platform_comparison(self, df: pd.DataFrame) -> go.Figure:
        """プラットフォーム別比較チャートを作成"""
        if df.empty:
            return self._create_empty_chart("プラットフォームデータがありません")
        
        platform_sentiment = df.groupby(['platform', 'sentiment']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        
        for sentiment in platform_sentiment.columns:
            fig.add_trace(go.Bar(
                name=sentiment,
                x=platform_sentiment.index,
                y=platform_sentiment[sentiment],
                marker_color=self.color_scheme.get(sentiment, '#000000'),
                hovertemplate=f'<b>{sentiment}</b><br>プラットフォーム: %{{x}}<br>投稿数: %{{y}}<extra></extra>'
            ))
        
        fig.update_layout(
            title="プラットフォーム別感情分析結果",
            xaxis_title="プラットフォーム",
            yaxis_title="投稿数",
            barmode='stack',
            height=400
        )
        
        return fig
    
    def create_engagement_analysis(self, df: pd.DataFrame) -> go.Figure:
        """エンゲージメント分析チャートを作成"""
        if df.empty or 'engagement_score' not in df.columns:
            return self._create_empty_chart("エンゲージメントデータがありません")
        
        # 感情とエンゲージメントの関係
        fig = px.box(
            df,
            x='sentiment',
            y='engagement_score',
            color='sentiment',
            color_discrete_map=self.color_scheme,
            title="感情別エンゲージメント分析"
        )
        
        fig.update_layout(
            xaxis_title="感情",
            yaxis_title="エンゲージメントスコア",
            height=400
        )
        
        return fig
    
    def create_word_cloud_data(self, df: pd.DataFrame, sentiment: str = None) -> Dict:
        """ワードクラウド用のデータを作成"""
        if df.empty:
            return {}
        
        # 感情でフィルタリング
        if sentiment:
            filtered_df = df[df['sentiment'] == sentiment]
        else:
            filtered_df = df
        
        if filtered_df.empty:
            return {}
        
        # テキストを結合して単語頻度を計算
        all_text = ' '.join(filtered_df['content'].astype(str))
        
        # 簡単な単語分析（実際にはMeCabやjanomeを使用することを推奨）
        words = all_text.split()
        word_freq = pd.Series(words).value_counts().head(50)
        
        return word_freq.to_dict()
    
    def create_trend_analysis(self, df: pd.DataFrame, window: int = 3) -> go.Figure:
        """トレンド分析チャートを作成"""
        if df.empty:
            return self._create_empty_chart("トレンドデータがありません")
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        daily_counts = df.groupby(df['timestamp'].dt.date).size()
        
        # 移動平均を計算
        rolling_avg = daily_counts.rolling(window=window, center=True).mean()
        
        fig = go.Figure()
        
        # 実際の値
        fig.add_trace(go.Scatter(
            x=daily_counts.index,
            y=daily_counts.values,
            mode='markers',
            name='実際の投稿数',
            marker=dict(color=self.color_scheme['primary'])
        ))
        
        # 移動平均
        fig.add_trace(go.Scatter(
            x=rolling_avg.index,
            y=rolling_avg.values,
            mode='lines',
            name=f'{window}日移動平均',
            line=dict(color=self.color_scheme['accent'], width=3)
        ))
        
        fig.update_layout(
            title=f"投稿数トレンド分析（{window}日移動平均）",
            xaxis_title="日付",
            yaxis_title="投稿数",
            height=400
        )
        
        return fig
    
    def create_heatmap(self, df: pd.DataFrame) -> go.Figure:
        """時間別投稿ヒートマップを作成"""
        if df.empty:
            return self._create_empty_chart("ヒートマップデータがありません")
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        
        # 曜日と時間のクロス集計
        heatmap_data = df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
        
        # 曜日の順序を設定
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex(day_order)
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='Viridis',
            hovertemplate='曜日: %{y}<br>時間: %{x}時<br>投稿数: %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title="曜日・時間別投稿ヒートマップ",
            xaxis_title="時間",
            yaxis_title="曜日",
            height=400
        )
        
        return fig
    
    def create_summary_metrics(self, df: pd.DataFrame) -> Dict:
        """サマリーメトリクスを作成"""
        if df.empty:
            return {
                'total_posts': 0,
                'unique_users': 0,
                'avg_engagement': 0,
                'sentiment_ratio': {'positive': 0, 'negative': 0, 'neutral': 0}
            }
        
        metrics = {
            'total_posts': len(df),
            'unique_users': df['user_id'].nunique() if 'user_id' in df.columns else 0,
            'avg_engagement': df['engagement_score'].mean() if 'engagement_score' in df.columns else 0,
            'sentiment_ratio': df['sentiment'].value_counts(normalize=True).to_dict()
        }
        
        return metrics
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """空のチャートを作成"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            xanchor='center',
            yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=400
        )
        return fig
