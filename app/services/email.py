from fastapi import BackgroundTasks
from app.config import settings

class EmailService:
    async def send_password_reset_email(self, email: str, token: str):
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        subject = "Password Reset Request"
        body = f"""
        Click the link below to reset your password:
        {reset_link}
        
        This link expires in 15 minutes.
        """
        print("REACHED EMAIL SERVICE")
        
        # await send_email(
        #     recipient=email,
        #     subject=subject,
        #     body=body
        # )