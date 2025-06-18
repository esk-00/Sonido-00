import json
import os
from mangum import Mangum
from app import main

# Gradioアプリを取得
try:
    app_instance = main()
    handler = Mangum(app_instance)
except Exception as e:
    print(f"App initialization error: {e}")
    handler = None

def lambda_handler(event, context):
    """Lambda関数のエントリーポイント"""
    try:
        # ヘルスチェック
        if event.get('httpMethod') == 'GET' and event.get('path') == '/health':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'healthy',
                    'timestamp': context.aws_request_id if context else 'local'
                })
            }
        
        # Gradioアプリが正常に初期化されている場合
        if handler:
            return handler(event, context)
        else:
            # フォールバック: 基本的なHTMLレスポンス
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Social Listening Tool</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        .container { max-width: 800px; margin: 0 auto; }
                        .error { color: #d32f2f; }
                        .info { color: #1976d2; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🔍 ソーシャルリスニングツール</h1>
                        <div class="error">
                            アプリケーションの初期化に失敗しました。
                        </div>
                        <div class="info">
                            <p>考えられる原因:</p>
                            <ul>
                                <li>AWS認証の設定不備</li>
                                <li>必要な環境変数の未設定</li>
                                <li>依存関係のインストール不備</li>
                            </ul>
                        </div>
                        <p>システム管理者にお問い合わせください。</p>
                    </div>
                </body>
                </html>
                '''
            }
            
    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }
