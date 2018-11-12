# 使用celery
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_fresh.settings")
django.setup()

app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 发邮件 邮件主题
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    recipient_list = [to_email]
    html_msg = '<h1>%s,欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
        username, token, token)
    send_mail(subject, message, sender, recipient_list, html_message=html_msg)
