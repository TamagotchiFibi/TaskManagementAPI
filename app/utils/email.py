from fastapi import BackgroundTasks
from app.core.config import settings
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import smtplib

logger = logging.getLogger(__name__)

async def send_email(
    email_to: str,
    subject: str,
    html_content: str,
    background_tasks: BackgroundTasks
) -> None:
    message = MIMEMultipart()
    message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    message["To"] = email_to
    message["Subject"] = subject
    
    message.attach(MIMEText(html_content, "html"))
    
    background_tasks.add_task(send_email_background, message)

async def send_email_background(message: MIMEMultipart) -> None:
    try:
        async with aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=settings.SMTP_TLS
        ) as smtp:
            await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            await smtp.send_message(message)
    except Exception as e:
        logger.error(f"Error sending email: {e}")

def send_new_account_email(
    email_to: str,
    username: str,
    password: str,
    background_tasks: BackgroundTasks
) -> None:
    subject = "Добро пожаловать в Task Management API"
    html_content = f"""
    <h1>Добро пожаловать в Task Management API!</h1>
    <p>Ваши учетные данные:</p>
    <ul>
        <li>Имя пользователя: {username}</li>
        <li>Пароль: {password}</li>
    </ul>
    <p>Пожалуйста, измените пароль после первого входа.</p>
    """
    background_tasks.add_task(send_email, email_to, subject, html_content, background_tasks)

def send_password_reset_email(
    email_to: str,
    token: str,
    background_tasks: BackgroundTasks
) -> None:
    subject = "Сброс пароля"
    html_content = f"""
    <h1>Сброс пароля</h1>
    <p>Для сброса пароля перейдите по ссылке:</p>
    <a href="http://localhost:8000{settings.API_V1_STR}/reset-password/{token}">
        Сбросить пароль
    </a>
    <p>Ссылка действительна в течение 1 часа.</p>
    """
    background_tasks.add_task(send_email, email_to, subject, html_content, background_tasks)

def send_welcome_email(to_email: str, username: str):
    """Отправляет приветственное email сообщение"""
    subject = "Добро пожаловать в Task Management API"
    body = f"""
    Здравствуйте, {username}!
    
    Спасибо за регистрацию в Task Management API.
    Теперь вы можете создавать и управлять своими задачами.
    
    С уважением,
    Команда Task Management API
    """
    return send_email(to_email, subject, body) 