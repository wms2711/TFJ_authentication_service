import aiosmtplib
import time
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from app.config import settings

class EmailService:
    def __init__(self):
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = settings.BREVO_API_KEY

    async def send_password_reset_email(self, email: str, token: str):
        """Send password reset as a transactional campaign"""
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )

        sender = {"name": "JobMatch Team", "email": settings.EMAIL_SENDER}
        to = [{"email": email}]
        
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

        try:
            print("HERE sending email")
            api_response = api_instance.send_transac_email(send_email)
            print(f"✅ Password reset sent to {email}")
            return True
        except ApiException as e:
            print(f"❌ Failed to send email: {e}")
            return False