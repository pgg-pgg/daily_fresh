# 使用celery
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_fresh.settings")
django.setup()

from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


app = Celery('celery_tasks.tasks', broker='redis://192.168.1.15:6379/8')


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


@app.task
def generate_static_index_html():
    '''产生首页静态数据页面'''
    # 获取商品的分类信息
    types = GoodsType.objects.all()

    # 获取首页的轮播商品的信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页的促销活动的信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品的展示信息
    for type in types:
        # 获取type种类在首页展示的图片商品的信息和文字商品的信息
        # QuerySet
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)

        # 给type对象增加属性title_banner,image_banner
        # 分别保存type种类在首页展示的文字商品和图片商品的信息
        type.title_banner = title_banner
        type.image_banner = image_banner

    # 判断用户用户是否已登录
    cart_count = 0

    # 组织模板上下文
    context = {
        'types': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
        'cart_count': cart_count
    }

    # 使用模板
    # 1.加载模板文件
    from django.template import loader
    temp = loader.get_template('static_index.html')

    # 2.模板渲染
    static_html = temp.render(context)

    # 生成静态首页文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_html)
