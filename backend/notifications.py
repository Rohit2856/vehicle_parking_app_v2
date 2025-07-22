import requests
import json
from flask import current_app

class NotificationService:
    @staticmethod
    def send_gchat_webhook_notification(message, title="Vehicle Parking App"):
        # notification via google chat webhook
        try:
            webhook_url = current_app.config['GCHAT_WEBHOOK_URL']
            
            if not current_app.config.get('GCHAT_NOTIFICATIONS_ENABLED'):
                print("Google Chat notifications disabled")
                return False
            
            # Google Chat card message
            payload = {
                'text': message,
                'cards': [{
                    'header': {
                        'title': f'{title}',
                        'subtitle': 'Parking Notification',
                        'imageUrl': 'https://developers.google.com/chat/images/chat-product-icon.png'
                    },
                    'sections': [{
                        'widgets': [{
                            'textParagraph': {
                                'text': f'<b>{message}</b>'
                            }
                        }, {
                            'buttons': [{
                                'textButton': {
                                    'text': 'Open Parking App',
                                    'onClick': {
                                        'openLink': {
                                            'url': 'http://localhost:5000'
                                        }
                                    }
                                }
                            }]
                        }]
                    }]
                }]
            }
            
            # Send to Google Chat
            response = requests.post(
                webhook_url, 
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                print(f"Google Chat notification sent successfully")
                return True
            else:
                print(f"Google Chat webhook error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error sending Google Chat notification: {e}")
            return False

