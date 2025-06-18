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
    """最小動作確認用Lambda関数"""
    
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
            <title>Lambda Test</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    background: #667eea; 
                    color: white; 
                    padding: 20px; 
                    text-align: center;
                }
                .success { 
                    background: rgba(0,255,0,0.2); 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin: 20px;
                }
            </style>
        </head>
        <body>
            <h1>Lambda Function Works!</h1>
            <div class="success">
                基本的なLambda関数が正常に動作しています
            </div>
            <p>Event: ''' + str(event) + '''</p>
            <p>Context: ''' + str(context.aws_request_id if context else 'none') + '''</p>
        </body>
        </html>
        '''
    }
