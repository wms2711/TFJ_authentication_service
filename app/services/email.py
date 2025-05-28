"""
Email Service
=============

Service responsible for sending transactional emails such as password reset links using the Brevo (Sendinblue) API.

Features:
- Construct and send password reset email
- Uses Brevo transactional email API (via sib_api_v3_sdk)
- Asynchronous and non-blocking implementation with `asyncio.to_thread` for thread safety
"""

import asyncio
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from app.config import settings
from utils.logger import init_logger
from fastapi import HTTPException, status

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

    def _build_reset_email_content(
            self, 
            link: str
        ) -> str:
        return f"""
            <p>Click below to reset your password:</p>
            <a href="{link}">Reset Password</a>
            <p>Link expires in 15 minutes.</p>
        """
    
    def _build_verify_email_content(
            self, 
            verification_link: str
        ) -> str:
        return f"""
            <p>Welcome! Please verify your email address:</p>
            <a href="{verification_link}">Verify Email</a>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
        """

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

