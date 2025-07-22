class EmailTemplates:
    @staticmethod
    def get_daily_reminder_template(user_name, reminder_data):
        # HTML template for daily reminder emails
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <div style="background-color: #007bff; color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">Daily Parking Reminder</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px;">Vehicle Parking App</p>
                </div>
                
                <div style="padding: 30px;">
                    <h2 style="color: #007bff; margin-bottom: 20px;">Hello {user_name},</h2>
                    <p style="font-size: 16px; margin-bottom: 25px;">Here's your daily parking summary:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-left: 5px solid #007bff; margin-bottom: 25px;">
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #007bff;">Active Reservations:</strong> 
                            <span style="font-size: 18px; font-weight: bold;">{reminder_data.get('active_reservations', 0)}</span>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #007bff;">Total Spent This Month:</strong> 
                            <span style="font-size: 18px; font-weight: bold;">Rs.{reminder_data.get('monthly_spending', 0.0)}</span>
                        </div>
                        <div>
                            <strong style="color: #007bff;">Available Parking Lots:</strong> 
                            <span style="font-size: 18px; font-weight: bold;">{reminder_data.get('available_lots', 0)}</span>
                        </div>
                    </div>
                    
                    <p style="font-size: 16px; margin-bottom: 25px;">Don't forget to check your parking status and plan your day!</p>
                    
                    <div style="text-align: center; margin-bottom: 25px;">
                        <a href="http://localhost:5000" style="
                            background-color: #007bff; 
                            color: white; 
                            padding: 15px 30px; 
                            text-decoration: none; 
                            border-radius: 5px;
                            font-size: 16px;
                            font-weight: bold;
                            display: inline-block;
                        ">Open Parking App</a>
                    </div>
                    
                    <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; text-align: center;">
                        <p style="margin: 0; font-size: 14px; color: #6c757d;">
                            Need help? Contact our support team or visit our help center.
                        </p>
                    </div>
                </div>
                
                <div style="background-color: #6c757d; color: white; padding: 20px; text-align: center;">
                    <p style="margin: 0; font-size: 14px;">Thank you for using Vehicle Parking App!</p>
                    <p style="margin: 5px 0 0 0; font-size: 14px;">Visit: http://localhost:5000</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def get_monthly_report_template(user_name, report_data):
        # HTML template for monthly report emails
        recent_reservations_html = ""
        for reservation in report_data.get('recent_reservations', []):
            recent_reservations_html += f"""
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">{reservation.get('date', 'N/A')}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{reservation.get('lot_name', 'N/A')}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{reservation.get('duration', 'N/A')}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">Rs.{reservation.get('cost', 0.0)}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Monthly Parking Report</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5;">
            <div style="max-width: 800px; margin: 0 auto; background-color: white;">
                <div style="background-color: #007bff; color: white; padding: 40px; text-align: center;">
                    <h1 style="margin: 0; font-size: 32px; font-weight: bold;">Monthly Parking Report</h1>
                    <p style="margin: 15px 0 0 0; font-size: 20px; opacity: 0.9;">
                        Period: {report_data.get('period', 'Current Month')}
                    </p>
                </div>
                
                <div style="padding: 40px;">
                    <h2 style="color: #007bff; margin-bottom: 20px; font-size: 24px;">Hello {user_name},</h2>
                    <p style="font-size: 18px; margin-bottom: 30px; color: #333;">
                        Here's your comprehensive monthly parking activity summary:
                    </p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px;">
                        <div style="background-color: #e3f2fd; padding: 20px; border-left: 5px solid #2196f3; border-radius: 5px;">
                            <h3 style="margin: 0 0 10px 0; color: #1976d2;">Total Reservations</h3>
                            <p style="margin: 0; font-size: 32px; font-weight: bold; color: #1976d2;">
                                {report_data.get('total_reservations', 0)}
                            </p>
                        </div>
                        <div style="background-color: #e8f5e8; padding: 20px; border-left: 5px solid #4caf50; border-radius: 5px;">
                            <h3 style="margin: 0 0 10px 0; color: #388e3c;">Total Amount Spent</h3>
                            <p style="margin: 0; font-size: 32px; font-weight: bold; color: #388e3c;">
                                Rs.{report_data.get('total_spent', 0.0)}
                            </p>
                        </div>
                        <div style="background-color: #fff3e0; padding: 20px; border-left: 5px solid #ff9800; border-radius: 5px;">
                            <h3 style="margin: 0 0 10px 0; color: #f57c00;">Average Duration</h3>
                            <p style="margin: 0; font-size: 32px; font-weight: bold; color: #f57c00;">
                                {report_data.get('avg_duration', 0)} hours
                            </p>
                        </div>
                        <div style="background-color: #f3e5f5; padding: 20px; border-left: 5px solid #9c27b0; border-radius: 5px;">
                            <h3 style="margin: 0 0 10px 0; color: #7b1fa2;">Favorite Lot</h3>
                            <p style="margin: 0; font-size: 18px; font-weight: bold; color: #7b1fa2;">
                                {report_data.get('favorite_lot', 'N/A')}
                            </p>
                        </div>
                    </div>
                    
                    <h3 style="color: #007bff; margin-bottom: 20px; font-size: 22px;">Recent Activity</h3>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; margin-top: 20px; background-color: white;">
                            <thead>
                                <tr style="background-color: #007bff;">
                                    <th style="padding: 15px 12px; border: 1px solid #ddd; color: white; text-align: left;">Date</th>
                                    <th style="padding: 15px 12px; border: 1px solid #ddd; color: white; text-align: left;">Parking Lot</th>
                                    <th style="padding: 15px 12px; border: 1px solid #ddd; color: white; text-align: left;">Duration (Hours)</th>
                                    <th style="padding: 15px 12px; border: 1px solid #ddd; color: white; text-align: left;">Cost (Rs.)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recent_reservations_html}
                            </tbody>
                        </table>
                    </div>
                    
                    <div style="margin-top: 40px; text-align: center;">
                        <a href="http://localhost:5000" style="
                            background-color: #007bff; 
                            color: white; 
                            padding: 15px 30px; 
                            text-decoration: none; 
                            border-radius: 5px;
                            font-size: 16px;
                            font-weight: bold;
                            display: inline-block;
                        ">View Full Dashboard</a>
                    </div>
                </div>
                
                <div style="background-color: #6c757d; color: white; padding: 30px; text-align: center;">
                    <h3 style="margin: 0 0 10px 0;">Thank you for using Vehicle Parking App!</h3>
                    <p style="margin: 0; font-size: 16px;">Visit: http://localhost:5000</p>
                    <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.8;">
                        This report was generated automatically. For questions, contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
