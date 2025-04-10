import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings, logger
from fastapi import BackgroundTasks, HTTPException, status

async def send_email(
    email_to: str,
    subject: str,
    html_content: str,
    background_tasks: BackgroundTasks
) -> None:
    """
    Отправляет email с использованием фоновых задач.
    
    Args:
        email_to: Email получателя
        subject: Тема письма
        html_content: HTML содержимое письма
        background_tasks: Объект фоновых задач FastAPI
    """
    try:
        # Создаем сообщение
        message = MIMEMultipart()
        message["From"] = settings.SMTP_USER
        message["To"] = email_to
        message["Subject"] = subject
        
        # Добавляем HTML содержимое
        message.attach(MIMEText(html_content, "html"))
        
        # Отправляем email в фоновом режиме
        background_tasks.add_task(
            send_email_task,
            email_to=email_to,
            subject=subject,
            html_content=html_content
        )
        
        logger.info(f"Email отправлен на {email_to}")
    except Exception as e:
        logger.error(f"Ошибка при отправке email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при отправке email"
        )

async def send_email_task(
    email_to: str,
    subject: str,
    html_content: str
) -> bool:
    """Отправка email"""
    try:
        message = MIMEMultipart()
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = email_to
        message["Subject"] = subject

        message.attach(MIMEText(html_content, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_TLS
        )
        
        logger.info(f"Email sent successfully to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {str(e)}")
        return False 