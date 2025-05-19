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

class EmailService:
    """Service for handling emails."""

    def __init__(self):
        """
        Initialize the email service with Brevo API key configuration.
        """
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = settings.BREVO_API_KEY

    async def send_password_reset_email(self, email: str, token: str):
        """
        Send password reset email to the specified recipient.

        Args:
            email (str): Recipient's email address.
            token (str): JWT reset token (usually expires in 15 mins).

        Returns:
            bool: True if email sent successfully, False otherwise.

        Email Contents:
            - Contains a reset link pointing to the frontend's reset-password page
            - Token is appended as a query param
            - HTML email with expiration note

        Technical Notes:
            - Uses Brevo's TransactionalEmailsApi via the official SDK
            - Runs the blocking `send_transac_email` call in a thread to avoid blocking the event loop
        """
        # Construct password reset link with query token
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        # Initialize transactional email API client
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )

        # Define sender and recipient
        sender = {"name": "JobMatch Team", "email": settings.EMAIL_SENDER}
        to = [{"email": email}]
        
        # Build the email payload
        send_email = sib_api_v3_sdk.SendSmtpEmail(
            sender=sender,
            to=to,
            subject="Password Reset Request",
            html_content=f"""
            <p>Click below to reset your password:</p>
            <a href="{reset_link}">{reset_link}</a>
            <p>Link expires in 15 minutes.</p>
            """
        )

        # Attempt to send email
        try:
            api_response = await asyncio.to_thread(api_instance.send_transac_email, send_email)
            print(f"✅ Password reset sent to {email}")
            return True
        except ApiException as e:
            print(f"❌ Failed to send email: {e}")
            return False
        
    async def send_verification_email(self, email: str, token: str) -> bool:
        """
        Send email verification email to the specified recipient.
        
        Args:
            email (str): Recipient's email address.
            token (str): JWT verification token.
            
        Returns:
            bool: True if email sent successfully, False otherwise.
        """
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )

        sender = {"name": "JobMatch Team", "email": settings.EMAIL_SENDER}
        to = [{"email": email}]

        send_email = sib_api_v3_sdk.SendSmtpEmail(
            sender=sender,
            to=to,
            subject="Verify Your Email Address",
            html_content=f"""
            <p>Welcome! Please verify your email address:</p>
            <a href="{verification_link}">Verify Email</a>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            """
        )
        
        try:
            await asyncio.to_thread(api_instance.send_transac_email, send_email)
            print(f"✅ Verification email sent to {email}")
            return True
        except ApiException as e:
            print(f"❌ Failed to send verification email: {e}")
            return False