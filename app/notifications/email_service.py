"""
Email notification service using SendGrid.
Sends compliance report notifications to users.
"""

import os
from typing import Optional, Dict, Any
import logging

# Try to import SendGrid, but make it optional
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    SendGridAPIClient = None
    Mail = None

from app.logging_config import get_logger

logger = get_logger(__name__)


class EmailService:
    """Send email notifications for compliance reports."""
    
    def __init__(self, api_key: Optional[str] = None, from_email: Optional[str] = None):
        """
        Initialize email service.
        
        Args:
            api_key: SendGrid API key (defaults to SENDGRID_API_KEY env var)
            from_email: Sender email address (defaults to FROM_EMAIL env var)
        """
        self.api_key = api_key or os.getenv('SENDGRID_API_KEY')
        self.from_email = from_email or os.getenv('FROM_EMAIL', 'noreply@compliance.example.com')
        
        if not SENDGRID_AVAILABLE:
            logger.warning("SendGrid SDK not available - email notifications disabled")
            self.client = None
        elif not self.api_key:
            logger.warning("SendGrid API key not configured - email notifications disabled")
            self.client = None
        else:
            self.client = SendGridAPIClient(self.api_key)
            logger.info(f"EmailService initialized with from_email={self.from_email}")
    
    def send_compliance_report_ready(
        self,
        to_email: str,
        user_name: Optional[str],
        report_id: str,
        document_id: str,
        compliance_score: float,
        report_url: str,
        gaps_count: int = 0
    ) -> bool:
        """
        Send notification when compliance report is ready.
        
        Args:
            to_email: Recipient email address
            user_name: User's name (optional)
            report_id: Report identifier
            document_id: Document identifier
            compliance_score: Compliance score (0-100)
            report_url: URL to view report
            gaps_count: Number of identified gaps
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.warning(f"Email service not configured, skipping notification to {to_email}")
            return False
        
        try:
            greeting = f"Hello {user_name}," if user_name else "Hello,"
            
            score_status = self._get_score_status(compliance_score)
            
            subject = f"Compliance Report Ready - {compliance_score:.1f}% ({score_status})"
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .score {{ font-size: 24px; font-weight: bold; color: {self._get_score_color(compliance_score)}; }}
        .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .info-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        .info-table td:first-child {{ font-weight: bold; width: 40%; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; color: white; 
                   text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #777; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Compliance Report Ready</h1>
        </div>
        
        <div class="content">
            <p>{greeting}</p>
            
            <p>Your compliance analysis has been completed. Here are the results:</p>
            
            <table class="info-table">
                <tr>
                    <td>Document ID:</td>
                    <td>{document_id}</td>
                </tr>
                <tr>
                    <td>Report ID:</td>
                    <td>{report_id}</td>
                </tr>
                <tr>
                    <td>Compliance Score:</td>
                    <td><span class="score">{compliance_score:.1f}%</span> ({score_status})</td>
                </tr>
                <tr>
                    <td>Identified Gaps:</td>
                    <td>{gaps_count}</td>
                </tr>
            </table>
            
            <p style="text-align: center;">
                <a href="{report_url}" class="button">View Full Report</a>
            </p>
            
            <p>The report includes:</p>
            <ul>
                <li>Detailed compliance analysis</li>
                <li>Identified gaps and deficiencies</li>
                <li>Actionable recommendations</li>
                <li>Section-by-section breakdown</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>This is an automated notification from the Compliance Checker System.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
            """
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to_email}: status {response.status_code}")
                return True
            else:
                logger.warning(f"Email send returned status {response.status_code} for {to_email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False
    
    def send_template_processed(
        self,
        to_email: str,
        user_name: Optional[str],
        template_id: str,
        template_type: str,
        chunk_count: int,
        status: str = "success"
    ) -> bool:
        """
        Send notification when template processing is complete.
        
        Args:
            to_email: Recipient email address
            user_name: User's name (optional)
            template_id: Template identifier
            template_type: Template type/category
            chunk_count: Number of chunks created
            status: Processing status ("success" or "failed")
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.warning(f"Email service not configured, skipping notification to {to_email}")
            return False
        
        try:
            greeting = f"Hello {user_name}," if user_name else "Hello,"
            
            if status == "success":
                subject = f"Template Processed Successfully - {template_type}"
                status_icon = "✓"
                status_color = "#4CAF50"
            else:
                subject = f"Template Processing Failed - {template_type}"
                status_icon = "✗"
                status_color = "#f44336"
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .info-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .info-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        .info-table td:first-child {{ font-weight: bold; width: 40%; }}
        .footer {{ text-align: center; padding: 20px; color: #777; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{status_icon} Template Processing {status.title()}</h1>
        </div>
        
        <div class="content">
            <p>{greeting}</p>
            
            <p>Your compliance template has been processed.</p>
            
            <table class="info-table">
                <tr>
                    <td>Template ID:</td>
                    <td>{template_id}</td>
                </tr>
                <tr>
                    <td>Template Type:</td>
                    <td>{template_type}</td>
                </tr>
                <tr>
                    <td>Chunks Created:</td>
                    <td>{chunk_count}</td>
                </tr>
                <tr>
                    <td>Status:</td>
                    <td style="color: {status_color}; font-weight: bold;">{status.upper()}</td>
                </tr>
            </table>
            
            <p>The template is now available for compliance checking.</p>
        </div>
        
        <div class="footer">
            <p>This is an automated notification from the Compliance Checker System.</p>
        </div>
    </div>
</body>
</html>
            """
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Template notification email sent to {to_email}: status {response.status_code}")
                return True
            else:
                logger.warning(f"Email send returned status {response.status_code} for {to_email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send template notification to {to_email}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _get_score_status(score: float) -> str:
        """Get human-readable status from compliance score."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        else:
            return "Needs Improvement"
    
    @staticmethod
    def _get_score_color(score: float) -> str:
        """Get color code for compliance score."""
        if score >= 90:
            return "#4CAF50"  # Green
        elif score >= 75:
            return "#8BC34A"  # Light Green
        elif score >= 60:
            return "#FFC107"  # Amber
        else:
            return "#f44336"  # Red
