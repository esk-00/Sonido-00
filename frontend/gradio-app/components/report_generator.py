import pandas as pd
import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import re

class ReportGenerator:
    """レポート生成を担当するクラス"""
    
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        self.report_templates = {
            'executive_summary': self._executive_summary_template,
            'detailed_analysis': self._detailed_analysis_template,
            'trend_report': self._trend_report_template,
            'crisis_alert': self._crisis_alert_template
        }

    def generate_comprehensive_report(self, df: pd.DataFrame, keyword: str, 
                                    report_type: str = 'detailed_analysis') -> str:
        """包括的なレポートを生成"""
        if df.empty:
            return "分析対象のデータがありません。"
        
        # データの基本統計を計算
        stats = self._calculate_statistics(df)
        
        # レポートテンプレートを選択
        template_func = self.report_templates.get(report_type, self._detailed_analysis_template)
        
        # Bedrockでレポート生成
        report_content = self._generate_with_bedrock(df, keyword, stats, template_func)
        
        # レポートのフォーマット
        formatted_report = self._format_report(report_content, stats, keyword)
        
        return formatted_report

    def _calculate_statistics(self, df: pd.DataFrame) -> Dict:
        """データの統計情報を計算"""
        stats = {
            'total_posts': len(df),
            'date_range': {
                'start': df['timestamp'].min().strftime('%Y-%m-%d') if 'timestamp' in df.columns else 'N/A',
                'end': df['timestamp'].max().strftime('%Y-%m-%d') if 'timestamp' in df.columns else 'N/A'
            },
            'sentiment_distribution': df['sentiment'].value_counts().to_dict() if 'sentiment' in df.columns else {},
            'platform_distribution': df['platform'].value_counts().to_dict() if 'platform' in df.columns else {},
            'engagement_stats': {
                'mean': df['engagement_score'].mean() if 'engagement_score' in df.columns else 0,
                'median': df['engagement_score'].median() if 'engagement_score' in df.columns else 0,
                'max': df['engagement_score'].max() if 'engagement_score' in df.columns else 0
            },
            'top_keywords': self._extract_top_keywords(df),
            'sentiment_score': self._calculate_overall_sentiment_score(df),
            'daily_volume': self._calculate_daily_volume(df)
        }
        
        return stats

    def _extract_top_keywords(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """頻出キーワードを抽出"""
        if 'content' not in df.columns:
            return []
        
        # 簡単な単語抽出（実際にはより高度な自然言語処理を使用）
        all_text = ' '.join(df['content'].astype(str))
        words = re.findall(r'\b\w+\b', all_text.lower())
        
        # ストップワードを除外（簡易版）
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                     'は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'より', 'の', 'こと', 'それ', 'これ'}
        
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        word_freq = pd.Series(filtered_words).value_counts().head(top_n)
        
        return [{'word': word, 'count': count} for word, count in word_freq.items()]

    def _calculate_overall_sentiment_score(self, df: pd.DataFrame) -> float:
        """総合感情スコアを計算"""
        if 'sentiment' not in df.columns:
            return 0.0
        
        sentiment_counts = df['sentiment'].value_counts()
        total = len(df)
        
        positive_ratio = sentiment_counts.get('positive', 0) / total
        negative_ratio = sentiment_counts.get('negative', 0) / total
        
        return positive_ratio - negative_ratio

    def _calculate_daily_volume(self, df: pd.DataFrame) -> Dict:
        """日別投稿量を計算"""
        if 'timestamp' not in df.columns:
            return {}
        
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_counts = df['date'].value_counts().sort_index()
        
        return {
            'average_daily': daily_counts.mean(),
            'peak_day': daily_counts.idxmax(),
            'peak_volume': daily_counts.max(),
            'trend': 'increasing' if daily_counts.iloc[-1] > daily_counts.iloc[0] else 'decreasing'
        }

    def _generate_with_bedrock(self, df: pd.DataFrame, keyword: str, stats: Dict, 
                              template_func) -> str:
        """Bedrockを使用してレポートを生成"""
        prompt = template_func(keyword, stats, df)
        
        try:
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2000,
                    "temperature": 0.3,
                    "topP": 0.9
                }
            }
            
            response = self.bedrock_client.invoke_model(
                modelId="amazon.nova-micro-v1:0",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['results'][0]['outputText']
            
        except Exception as e:
            return f"レポート生成エラー: {str(e)}"

    def _executive_summary_template(self, keyword: str, stats: Dict, df: pd.DataFrame) -> str:
        """エグゼクティブサマリー用テンプレート"""
        return f"""
        キーワード「{keyword}」に関するソーシャルメディア分析のエグゼクティブサマリーを作成してください。

        ## データ概要
        - 分析期間: {stats['date_range']['start']} 〜 {stats['date_range']['end']}
        - 総投稿数: {stats['total_posts']}件
        - 感情分布: {stats['sentiment_distribution']}
        - 総合感情スコア: {stats['sentiment_score']:.2f}

        ## 重要指標
        - 日平均投稿数: {stats['daily_volume'].get('average_daily', 0):.1f}件
        - ピーク日: {stats['daily_volume'].get('peak_day', 'N/A')}
        - 主要キーワード: {[kw['word'] for kw in stats['top_keywords'][:5]]}

        以下の構成で簡潔なエグゼクティブサマリーを作成してください：
        1. 主要な発見事項（3-4点）
        2. ビジネスへの影響
        3. 推奨アクション
        4. 注意すべきリスク

        専門用語は避け、経営陣向けに分かりやすく記述してください。
        """

    def _detailed_analysis_template(self, keyword: str, stats: Dict, df: pd.DataFrame) -> str:
        """詳細分析用テンプレート"""
        return f"""
        キーワード「{keyword}」に関する詳細なソーシャルメディア分析レポートを作成してください。

        ## 分析データ
        - 期間: {stats['date_range']['start']} 〜 {stats['date_range']['end']}
        - 総投稿数: {stats['total_posts']}件
        - 感情分布: ポジティブ {stats['sentiment_distribution'].get('positive', 0)}件、
                   ネガティブ {stats['sentiment_distribution'].get('negative', 0)}件、
                   ニュートラル {stats['sentiment_distribution'].get('neutral', 0)}件
        - プラットフォーム別: {stats['platform_distribution']}
        - 頻出キーワード: {stats['top_keywords'][:10]}

        以下の構成で詳細レポートを作成してください：

        ## 1. 概要
        - 分析結果のハイライト
        - 全体的な傾向

        ## 2. 感情分析結果
        - 感情分布の詳細
        - 各感情の特徴的な投稿内容
        - 時系列での感情変化

        ## 3. エンゲージメント分析
        - 高エンゲージメント投稿の特徴
        - プラットフォーム別パフォーマンス

        ## 4. キーワード・トピック分析
        - 関連キーワードの分析
        - 話題の変遷

        ## 5. リスク・機会の特定
        - 注意すべき негатив傾向
        - 活用できるポジティブ要素

        ## 6. 改善提案
        - 具体的なアクションプラン
        - モニタリング推奨事項

        データに基づいた客観的な分析を心がけ、実用的な洞察を提供してください。
        """

    def _trend_report_template(self, keyword: str, stats: Dict, df: pd.DataFrame) -> str:
        """トレンドレポート用テンプレート"""
        return f"""
        キーワード「{keyword}」のソーシャルメディアトレンド分析レポートを作成してください。

        ## トレンドデータ
        - 分析期間: {stats['date_range']['start']} 〜 {stats['date_range']['end']}
        - 投稿量トレンド: {stats['daily_volume'].get('trend', '不明')}
        - 平均日次投稿数: {stats['daily_volume'].get('average_daily', 0):.1f}件
        - ピーク期間: {stats['daily_volume'].get('peak_day', 'N/A')}

        以下の観点からトレンド分析を実施してください：

        ## 1. 投稿量の変遷
        - 期間中の投稿数の推移
        - 特異な増減とその要因

        ## 2. 感情の変化
        - 時系列での感情変化
        - 感情転換点の特定

        ## 3. 話題の移り変わり
        - 期間中の主要トピックの変遷
        - 新しく登場した話題

        ## 4. 予測と展望
        - 今後の傾向予測
        - 注意すべき変化の兆候

        ## 5. 戦略的示唆
        - トレンドを活用した施策提案
        - タイミング最適化のアドバイス

        データの時系列変化に焦点を当て、将来への示唆を含めてください。
        """

    def _crisis_alert_template(self, keyword: str, stats: Dict, df: pd.DataFrame) -> str:
        """危機警告用テンプレート"""
        negative_ratio = stats['sentiment_distribution'].get('negative', 0) / stats['total_posts']
        
        return f"""
        キーワード「{keyword}」に関するリスク分析アラートレポートを作成してください。

        ## 警告指標
        - ネガティブ投稿比率: {negative_ratio:.1%}
        - 総合感情スコア: {stats['sentiment_score']:.2f}
        - 最近の投稿量: {stats['daily_volume'].get('peak_volume', 0)}件/日

        ## 緊急度評価基準
        - 高リスク: ネガティブ比率 > 40% または 感情スコア < -0.3
        - 中リスク: ネガティブ比率 20-40% または 感情スコア -0.3〜0
        - 低リスク: その他

        以下の構成で危機対応レポートを作成してください：

        ## 1. リスクレベル判定
        - 現在のリスク度合い
        - 主要な懸念事項

        ## 2. 問題の詳細分析
        - ネガティブ投稿の内容分析
        - 炎上の可能性評価
        - 影響範囲の推定

        ## 3. 緊急対応推奨事項
        - 即座に取るべき対応
        - ステークホルダーへの連絡事項
        - 対外コミュニケーション戦略

        ## 4. 継続監視計画
        - 重点監視項目
        - エスカレーション基準
        - 報告頻度

        リスク管理の観点から、迅速な意思決定を支援する内容としてください。
        """

    def _format_report(self, content: str, stats: Dict, keyword: str) -> str:
        """レポートのフォーマット"""
        header = f"""
# ソーシャルリスニング分析レポート

**キーワード:** {keyword}  
**生成日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M')}  
**分析期間:** {stats['date_range']['start']} 〜 {stats['date_range']['end']}  
**総投稿数:** {stats['total_posts']:,}件  

---

"""
        
        footer = f"""

---

## データ詳細

### 基本統計
- **感情分布:**
  - ポジティブ: {stats['sentiment_distribution'].get('positive', 0)}件 ({stats['sentiment_distribution'].get('positive', 0)/stats['total_posts']*100:.1f}%)
  - ネガティブ: {stats['sentiment_distribution'].get('negative', 0)}件 ({stats['sentiment_distribution'].get('negative', 0)/stats['total_posts']*100:.1f}%)
  - ニュートラル: {stats['sentiment_distribution'].get('neutral', 0)}件 ({stats['sentiment_distribution'].get('neutral', 0)/stats['total_posts']*100:.1f}%)

- **総合感情スコア:** {stats['sentiment_score']:.3f} (-1.0〜1.0)

### 頻出キーワード
{self._format_keywords(stats['top_keywords'])}

### プラットフォーム別投稿数
{self._format_platforms(stats['platform_distribution'])}

---

*このレポートはAIによって自動生成されました。詳細な分析が必要な場合は人による確認を推奨します。*
"""
        
        return header + content + footer

    def _format_keywords(self, keywords: List[Dict]) -> str:
        """キーワードリストのフォーマット"""
        if not keywords:
            return "キーワードが抽出されませんでした。"
        
        formatted = []
        for i, kw in enumerate(keywords[:10], 1):
            formatted.append(f"{i}. {kw['word']} ({kw['count']}回)")
        
        return "\n".join(formatted)

    def _format_platforms(self, platforms: Dict) -> str:
        """プラットフォーム分布のフォーマット"""
        if not platforms:
            return "プラットフォーム情報がありません。"
        
        formatted = []
        total = sum(platforms.values())
        
        for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            formatted.append(f"- {platform}: {count}件 ({percentage:.1f}%)")
        
        return "\n".join(formatted)

    def generate_summary_metrics(self, df: pd.DataFrame) -> Dict:
        """サマリー指標を生成（ダッシュボード用）"""
        if df.empty:
            return {
                'total_posts': 0,
                'sentiment_score': 0,
                'engagement_rate': 0,
                'top_platform': 'N/A',
                'trend_direction': 'stable',
                'alert_level': 'low'
            }
        
        stats = self._calculate_statistics(df)
        
        # アラートレベルの判定
        negative_ratio = stats['sentiment_distribution'].get('negative', 0) / stats['total_posts']
        if negative_ratio > 0.4 or stats['sentiment_score'] < -0.3:
            alert_level = 'high'
        elif negative_ratio > 0.2 or stats['sentiment_score'] < 0:
            alert_level = 'medium'
        else:
            alert_level = 'low'
        
        # トップ プラットフォーム
        top_platform = max(stats['platform_distribution'].items(), 
                          key=lambda x: x[1])[0] if stats['platform_distribution'] else 'N/A'
        
        return {
            'total_posts': stats['total_posts'],
            'sentiment_score': round(stats['sentiment_score'], 3),
            'engagement_rate': round(stats['engagement_stats']['mean'], 2),
            'top_platform': top_platform,
            'trend_direction': stats['daily_volume'].get('trend', 'stable'),
            'alert_level': alert_level,
            'last_updated': datetime.now().isoformat()
        }

    def export_data(self, df: pd.DataFrame, format_type: str = 'csv') -> str:
        """データをエクスポート"""
        if df.empty:
            return "エクスポートするデータがありません。"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            if format_type.lower() == 'csv':
                filename = f"social_listening_data_{timestamp}.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                return f"データを{filename}にエクスポートしました。"
            
            elif format_type.lower() == 'json':
                filename = f"social_listening_data_{timestamp}.json"
                df.to_json(filename, orient='records', force_ascii=False, indent=2)
                return f"データを{filename}にエクスポートしました。"
            
            elif format_type.lower() == 'excel':
                filename = f"social_listening_data_{timestamp}.xlsx"
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Raw Data', index=False)
                    
                    # 統計情報もシートに追加
                    stats = self._calculate_statistics(df)
                    stats_df = pd.DataFrame([stats])
                    stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                
                return f"データを{filename}にエクスポートしました。"
            
            else:
                return f"サポートされていないフォーマット: {format_type}"
                
        except Exception as e:
            return f"エクスポートエラー: {str(e)}"
