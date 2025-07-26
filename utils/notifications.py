import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import date
from config import config
from database.models import AlertLog

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages notifications and alerts."""
    
    def __init__(self):
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.sender_email = config.SENDER_EMAIL
        self.sender_password = config.EMAIL_PASSWORD
        self.recipient_email = config.RECIPIENT_EMAIL
    
    def send_anomaly_alert(self, anomalies: List, target_date: date):
        """Send email alert for detected anomalies."""
        try:
            # Create email content
            subject = f"Options Anomaly Alert - {target_date}"
            content = self._create_anomaly_email_content(anomalies, target_date)
            
            # Send email
            success = self._send_email(subject, content)
            
            # Log the alert
            self._log_alert("email", self.recipient_email, subject, content, 
                           "sent" if success else "failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending anomaly alert: {e}")
            self._log_alert("email", self.recipient_email, subject, content, "failed", str(e))
            return False
    
    def _create_anomaly_email_content(self, anomalies: List, target_date: date) -> str:
        """Create email content for anomaly alert."""
        
        # Sort anomalies by insider probability (highest first)
        sorted_anomalies = sorted(anomalies, key=lambda x: x.insider_probability, reverse=True)
        
        content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
                .anomaly {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ff6b6b; background-color: #fff5f5; }}
                .high-risk {{ border-left-color: #ff0000; background-color: #ffe6e6; }}
                .medium-risk {{ border-left-color: #ffa500; background-color: #fff8e6; }}
                .low-risk {{ border-left-color: #ffff00; background-color: #fffff0; }}
                .metric {{ margin: 5px 0; }}
                .trigger {{ font-weight: bold; color: #ff0000; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Options Anomaly Alert</h2>
                <p><strong>Date:</strong> {target_date}</p>
                <p><strong>Total Anomalies:</strong> {len(anomalies)}</p>
            </div>
        """
        
        if not anomalies:
            content += "<p>No anomalies detected for today.</p>"
        else:
            content += "<h3>Detected Anomalies:</h3>"
            
            for anomaly in sorted_anomalies:
                # Determine risk level
                if anomaly.insider_probability >= 0.7:
                    risk_class = "high-risk"
                    risk_level = "HIGH"
                elif anomaly.insider_probability >= 0.4:
                    risk_class = "medium-risk"
                    risk_level = "MEDIUM"
                else:
                    risk_class = "low-risk"
                    risk_level = "LOW"
                
                content += f"""
                <div class="anomaly {risk_class}">
                    <h4>{risk_level} RISK - {anomaly.stock.symbol} - {anomaly.insider_probability:.1%} Insider Probability</h4>
                    <div class="metric"><strong>Unusual Activity Score:</strong> {anomaly.unusual_activity_score:.2f}</div>
                    <div class="metric"><strong>Notes:</strong> {anomaly.notes}</div>
                    
                    <h5>Volume Anomalies:</h5>
                    <div class="metric">Call Volume: {anomaly.call_volume:,} (Baseline: {anomaly.call_volume_baseline:.0f}) 
                    <span class="trigger">{'ALERT' if anomaly.call_volume_trigger else ''}</span></div>
                    <div class="metric">Put Volume: {anomaly.put_volume:,} (Baseline: {anomaly.put_volume_baseline:.0f})
                    <span class="trigger">{'ALERT' if anomaly.put_volume_trigger else ''}</span></div>
                    
                    <h5>Special Anomalies:</h5>
                    <div class="metric">Short-term Calls: {anomaly.short_term_call_volume:,} 
                    <span class="trigger">{'ALERT' if anomaly.short_term_call_trigger else ''}</span></div>
                    <div class="metric">OTM Calls: {anomaly.otm_call_volume:,}
                    <span class="trigger">{'ALERT' if anomaly.otm_call_trigger else ''}</span></div>
                    <div class="metric">OI Delta: {anomaly.call_oi_delta:,}
                    <span class="trigger">{'ALERT' if anomaly.call_oi_trigger else ''}</span></div>
                </div>
                """
        
        content += """
        </body>
        </html>
        """
        
        return content
    
    def _send_email(self, subject: str, content: str) -> bool:
        """Send email using SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            # Attach HTML content
            html_part = MIMEText(content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _log_alert(self, alert_type: str, recipient: str, subject: str, 
                   content: str, status: str, error_message: str = None):
        """Log alert attempt to database."""
        try:
            # This would need to be called within a database session
            # For now, just log to console
            logger.info(f"Alert logged: {alert_type} to {recipient} - {status}")
            
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
    
    def send_test_email(self) -> bool:
        """Send a test email to verify configuration."""
        subject = "Options Tracker - Test Email"
        content = """
        <html>
        <body>
            <h2>Options Tracker Test Email</h2>
            <p>This is a test email to verify that the notification system is working correctly.</p>
            <p>If you received this email, the configuration is correct.</p>
        </body>
        </html>
        """
        
        return self._send_email(subject, content)
    
    def send_error_alert(self, error_message: str, context: str = ""):
        """Send alert for system errors."""
        subject = f"Options Tracker Error Alert - {context}"
        content = f"""
        <html>
        <body>
            <h2>Options Tracker Error</h2>
            <p><strong>Context:</strong> {context}</p>
            <p><strong>Error:</strong> {error_message}</p>
            <p>Please check the system logs for more details.</p>
        </body>
        </html>
        """
        
        return self._send_email(subject, content) 