import json
import os
import sys

def lambda_handler(event, context):
    """段階的Gradio実装"""
    
    # デバッグ情報
    debug_info = {
        'event_keys': list(event.keys()) if event else [],
        'http_method': event.get('httpMethod', 'N/A'),
        'path': event.get('path', 'N/A'),
        'python_version': sys.version,
        'python_path': sys.path[:3],  # 最初の3つだけ
    }
    
    # Gradioライブラリの存在確認
    libraries_status = {}
    try:
        import gradio
        libraries_status['gradio'] = f"✓ {gradio.__version__}"
    except ImportError as e:
        libraries_status['gradio'] = f"✗ {str(e)}"
    
    try:
        import pandas
        libraries_status['pandas'] = f"✓ {pandas.__version__}"
    except ImportError as e:
        libraries_status['pandas'] = f"✗ {str(e)}"
    
    try:
        import plotly
        libraries_status['plotly'] = f"✓ {plotly.__version__}"
    except ImportError as e:
        libraries_status['plotly'] = f"✗ {str(e)}"
    
    try:
        import mangum
        libraries_status['mangum'] = f"✓ {mangum.__version__}"
    except ImportError as e:
        libraries_status['mangum'] = f"✗ {str(e)}"
    
    # ライブラリが全て利用可能な場合のみGradioを試行
    if all('✓' in status for status in libraries_status.values()):
        try:
            return create_gradio_response(event, context, debug_info, libraries_status)
        except Exception as e:
            return create_error_response(str(e), debug_info, libraries_status)
    else:
        return create_debug_response(debug_info, libraries_status)

def create_gradio_response(event, context, debug_info, libraries_status):
    """Gradioアプリケーションの作成と実行"""
    
    # Gradioアプリの最小実装
    try:
        import gradio as gr
        import pandas as pd
        import plotly.graph_objects as go
        from mangum import Mangum
        
        def simple_analysis(keyword):
            """シンプルな分析関数"""
            if not keyword:
                return "キーワードを入力してください"
            
            # デモデータ作成
            data = {
                'sentiment': ['positive', 'negative', 'neutral'],
                'count': [10, 3, 7]
            }
            df = pd.DataFrame(data)
            
            # 簡単なプロット
            fig = go.Figure(data=[go.Bar(x=df['sentiment'], y=df['count'])])
            fig.update_layout(title=f'{keyword} 分析結果')
            
            summary = f"""
# {keyword} 分析結果

- ポジティブ: 10件
- ネガティブ: 3件  
- ニュートラル: 7件

総合評価: 良好
"""
            return fig, summary
        
        # Gradioインターフェース
        with gr.Blocks(title="Social Listening Tool") as app:
            gr.Markdown("# 🔍 Social Listening Tool")
            
            with gr.Row():
                keyword_input = gr.Textbox(
                    label="検索キーワード",
                    placeholder="例: iPhone",
                    value="iPhone"
                )
                analyze_btn = gr.Button("分析開始", variant="primary")
            
            with gr.Row():
                chart_output = gr.Plot(label="分析チャート")
            
            summary_output = gr.Markdown(label="分析結果")
            
            analyze_btn.click(
                fn=simple_analysis,
                inputs=[keyword_input],
                outputs=[chart_output, summary_output]
            )
        
        # Mangum経由でLambdaハンドラーとして実行
        handler = Mangum(app)
        return handler(event, context)
        
    except Exception as e:
        return create_error_response(f"Gradio実行エラー: {str(e)}", debug_info, libraries_status)

def create_debug_response(debug_info, libraries_status):
    """デバッグ情報レスポンス"""
    
    libs_html = ""
    for lib, status in libraries_status.items():
        color = "#4CAF50" if "✓" in status else "#F44336"
        libs_html += f'<div style="color: {color}; margin: 5px 0;">{lib}: {status}</div>'
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lambda診断</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background: #667eea; 
                    color: white; 
                    padding: 20px;
                }}
                .box {{ 
                    background: rgba(255,255,255,0.1); 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin: 15px 0;
                }}
                pre {{ 
                    background: rgba(0,0,0,0.3); 
                    padding: 10px; 
                    border-radius: 5px; 
                    overflow: auto;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🔧 Lambda環境診断</h1>
                <h3>📚 ライブラリ状況</h3>
                {libs_html}
            </div>
            
            <div class="box">
                <h3>📊 イベント情報</h3>
                <pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>
            </div>
            
            <div class="box">
                <h3>💡 次のステップ</h3>
                <p>不足しているライブラリをrequirements.txtに追加してください</p>
            </div>
        </body>
        </html>
        '''
    }

def create_error_response(error_msg, debug_info, libraries_status):
    """エラーレスポンス"""
    
    return {
        'statusCode': 500,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lambda エラー</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background: #d32f2f; 
                    color: white; 
                    padding: 20px;
                }}
                .box {{ 
                    background: rgba(255,255,255,0.1); 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🚨 エラーが発生しました</h1>
                <p><strong>エラー内容:</strong> {error_msg}</p>
            </div>
            
            <div class="box">
                <h3>📊 診断情報</h3>
                <pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>
            </div>
        </body>
        </html>
        '''
    }
