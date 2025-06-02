"""
Email Service
=============

Service responsible for sending transactional emails such as password reset links,
verification emails, and general notifications using the Brevo (Sendinblue) API.

Features:
- Construct and send password reset email
- Construct and send email verification link
- Construct and send general email notifications
- Uses Brevo transactional email API (via sib_api_v3_sdk)
- Jinja2 templating for consistent and customizable email formatting
- Asynchronous and non-blocking implementation using `asyncio.to_thread`
"""

import asyncio
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from app.config import settings
from utils.logger import init_logger
from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

# Setup Jinja2
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)

# Configure logger
logger = init_logger("EmailService")

class EmailService:
    """Service for handling emails."""

    def __init__(self):
        """
        Initialize the email service with Brevo API key configuration.
        """
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    def _render_template(self, template_name: str, context: dict) -> str:
        """
        Render an HTML template with provided context using Jinja2.

        Args:
            template_name (str): Filename of the HTML template.
            context (dict): Dictionary of variables to pass to the template.

        Returns:
            str: Rendered HTML content.
        """
        template = env.get_template(template_name)
        return template.render(**context)

    def _build_reset_email_content(
            self, 
            link: str
        ) -> str:
        """
        Build HTML content for password reset email.

        Args:
            link (str): Password reset link.

        Returns:
            str: Rendered HTML email body.
        """
        return self._render_template("reset_password.html", {"link": link})
    
    def _build_verify_email_content(
            self, 
            verification_link: str
        ) -> str:
        """
        Build HTML content for email verification.

        Args:
            verification_link (str): Email verification link.

        Returns:
            str: Rendered HTML email body.
        """
        return self._render_template("verify_email.html", {"verification_link": verification_link})
    
    def _build_notification_email_content(
            self, 
            message: str
        ) -> str:
        """
        Build HTML content for a general notification email.

        Args:
            message (str): Message to display in the email.

        Returns:
            str: Rendered HTML email body.
        """
        return self._render_template("notification_email.html", {"message": message})
    
    async def _send_email(
            self, 
            to_email: str, 
            subject: str, 
            html_content: str
        ) -> bool:
        """
        Internal utility to send an email asynchronously via Brevo API.

        Args:
            to_email (str): Recipient email.
            subject (str): Email subject.
            html_content (str): HTML body content.

        Returns:
            bool: True if sent successfully, False otherwise.

        Raises:
            ApiException: Failed sending email.
        """
        try:
            # Initialize transactional email API client
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(self.configuration)
            )

            # Define sender and recipient
            sender = {"name": "JobMatch Team", "email": settings.EMAIL_SENDER}
            to = [{"email": to_email}]

            # Build the email payload
            email_data = sib_api_v3_sdk.SendSmtpEmail(
                sender=sender,
                to=to,
                subject=subject,
                html_content=html_content
            )

            await asyncio.to_thread(api_instance.send_transac_email, email_data)
            logger.info(f"✅ Email sent to {to_email}")
            return True
        
        except ApiException as api_exc:
            logger.error(f"Brevo APIException when sending email to {to_email}: {str(api_exc)}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error sending email to {to_email}: {str(e)}")
            return False

    async def send_password_reset_email(
            self, 
            email: str, 
            token: str
        ) -> bool:
        """
        Send password reset email with reset link.

        Args:
            email (str): Recipient's email address.
            token (str): JWT reset token.

        Returns:
            bool: True if email sent successfully, False otherwise.

        Raises:
            HTTPException: If the email could not be sent.
        """
        try:
            # Construct password reset link with query token
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            # Define content and send email
            content = self._build_reset_email_content(reset_link)
            return await self._send_email(email, "Password Reset Request", content)
        
        except Exception as e:
            logger.exception(f"Failed to send password reset email to {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
        
    async def send_verification_email(self, email: str, token: str) -> bool:
        """
        Send email verification email to the specified recipient.
        
        Args:
            email (str): Recipient's email address.
            token (str): JWT verification token.
            
        Returns:
            bool: True if email sent successfully, False otherwise.

        Raises:
            HTTPException: If the email could not be sent.
        """
        try:
            verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

            # Define content and send email
            content = self._build_verify_email_content(verification_link)
            return await self._send_email(email, "Verify Your Email Address", content)
        
        except Exception as e:
            logger.exception(f"Failed to send verification email to {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )

    async def send_email_notification(self, email: str, title: str, message: str) -> bool:
        """
        Send email notification email to the specified recipient.
        
        Args:
            email (str): Recipient's email address.
            title (str): Email title.
            message (str): Email message.
            
        Returns:
            bool: True if email sent successfully, False otherwise.

        Raises:
            HTTPException: If the email could not be sent.
        """
        try:
            # Define content and send email
            content = self._build_notification_email_content(message)
            return await self._send_email(email, title, content)
        
        except Exception as e:
            logger.exception(f"Failed to send verification email to {email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )