import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime
import pytz

ist_timezone = pytz.timezone('Asia/Kolkata')

class EmailTemplates:
    @staticmethod
    def send_email(to_email, subject, body, html=False, attachment_path=None):
        try:
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            sender_email = "enter_your_mail"
            sender_password = "enter_your_password"
            
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if html:
                html_part = MIMEText(body, 'html')
                msg.attach(html_part)
                import re
                plain_text = re.sub('<[^<]+?>', '', body)
                text_part = MIMEText(plain_text, 'plain')
                msg.attach(text_part)
            else:
                text_part = MIMEText(body, 'plain')
                msg.attach(text_part)
            
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(attachment_path)}'
                    )
                    msg.attach(part)
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, to_email, text)
            server.quit()
            
            return {'status': 'SUCCESS'}
            
        except Exception as e:
            return {'status': 'FAILED', 'error': str(e)}

    @staticmethod
    def get_daily_reminder_template(user_name, reminder_data):
        return f"""
Hi {user_name},

We noticed you haven't booked a parking spot recently.

Don't let parking stress ruin your day! We have great spots available right now.

Book now and enjoy:
- Guaranteed parking spot
- Easy online booking
- Competitive hourly rates
- Safe and secure locations

Visit your dashboard to book a spot now!

Best regards,
Vehicle Parking App Team
"""

    @staticmethod
    def get_monthly_report_template(user_name, report_data):
        return f"""
Dear {user_name},

Here's your monthly parking activity summary:

Monthly Overview:
- Total Bookings: {report_data.get('total_bookings', 0)}
- Total Amount Spent: Rs.{report_data.get('total_spent', 0.0)}
- Average Duration: {report_data.get('avg_duration', 0)} hours
- Most Used Location: {report_data.get('favorite_lot', 'N/A')}

Thank you for using Vehicle Parking App!

Best regards,
Parking Management Team
"""

    @staticmethod
    def get_export_ready_template(user_name, export_data):
        return f"""
Dear {user_name},

Your parking data export has been completed successfully!

Export Details:
- Records Exported: {export_data.get('records_count', 0)}
- Export Type: {export_data.get('export_type', 'User').title()}
- Generated On: {datetime.now(ist_timezone).replace(tzinfo=None).strftime('%B %d, %Y at %I:%M %p IST')}
- File Name: {export_data.get('filename', 'export.csv')}

Your CSV file is ready for download. Please visit your dashboard to download it.

Thank you for using Vehicle Parking App!

Best regards,
Parking Management Team
"""

def send_email(to_email, subject, body, html=False):
    return EmailTemplates.send_email(to_email, subject, body, html)  

