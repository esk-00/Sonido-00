import json
import os
from mangum import Mangum
from app import main

# Gradioアプリを取得
app_instance = main()
handler = Mangum(app_instance.app)

def lambda_handler(event, context):
    """Lambda関数のエントリーポイント"""
    try:
        # API Gateway統合用
        return handler(event, context)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }
