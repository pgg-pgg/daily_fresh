from django.shortcuts import render, redirect
import re
from user.models import User, Address
from goods.models import GoodsSKU
from django.views.generic import View
from django.core.urlresolvers import reverse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.http import HttpResponse
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login, logout
from utils import mixin
from django_redis import get_redis_connection


# Create your views here.


class RegisterView(View):
    '''注册'''

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        '''进行注册处理'''

        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式错误'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理： 进行用户注册
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        # 发送激活邮件，包含激活连接：http://127.0.0.1:8000/user/active/3
        # 激活连接中需要包含用户的身份信息

        # 加密用户的身份信息，生成激活的token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)  # bytes
        token = token.decode('utf8')

        # 发邮件 邮件主题 任务
        send_register_active_email.delay(email, username, token)
        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户激活'''

    def get(self, request, token):
        '''进行用户激活'''
        # 进行解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 跳转到登录页
            return redirect(reverse('user:login'))
        except SignatureExpired as s:
            # 激活连接已过期
            return HttpResponse('激活链接已过期')


class LoginView(View):
    '''登录'''

    def get(self, request):
        '''显示登录页面'''
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        '''登录校验'''
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        # 业务处理
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                '''登录成功'''
                # 记住用户的登录状态
                login(request, user)
                # 获取登录后所要跳转的地址
                # 默认跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)
                # 判断是否需要记住用户名
                remember = request.POST.get('remember')

                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')

                # 跳转到首页
                return response
            else:
                '''用户未激活'''
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            '''登录失败'''
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):
    '''退出登录'''''

    def get(self, request):
        # 清除用户的session信息
        logout(request)
        return redirect(reverse('goods:index'))


class UserInfoView(mixin.LoginRequiredMixin, View):
    '''用户中心信息页'''

    def get(self, request):
        '''显示'''
        # page = 'user'
        # request.user
        # 如果用户未登录 -》 AnonymousUser类的一个实例
        # 如果用户已登录 -》 User的一个实例
        # request.user.is_authenticated()
        # 除了给模版文件传递的变量之外，django框架会把request.user也传给模版文件

        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户的最近浏览
        # from redis import StrictRedis
        # StrictRedis(host='127.0.0.1', port='6379', db=9)
        con = get_redis_connection('default')

        history_key = 'history_%d' % user.id
        # 获取用户最新浏览的5件商品的id
        sku_ids = con.lrange(history_key, 0, 4)
        # 通过id获取商品信息
        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)

        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li}

        return render(request, 'user_center_info.html', context)


class UserOrderView(mixin.LoginRequiredMixin, View):
    '''用户中心信息页'''

    def get(self, request):
        '''显示'''

        # 获取用户的订单信息

        return render(request, 'user_center_order.html', {'page': 'order'})


class AddressView(mixin.LoginRequiredMixin, View):
    '''用户中心信息页'''

    def get(self, request):
        '''显示'''
        # 获取默认收货地址
        user = request.user

        address = Address.objects.get_default_address(user)

        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        # 接受数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '信息不完整'})

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号格式不正确'})
        # 业务处理
        # 如果用户已存在默认收货地址，添加的地址不作为默认收获地址，
        # 获取用户的对应的USer对象
        user = request.user
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user, receiver=receiver, addr=addr,
                               zip_code=zip_code, phone=phone, is_default=is_default)
        # 返回
        return redirect(reverse('user:address'))
