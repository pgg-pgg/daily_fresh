from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.core.cache import cache

from django_redis import get_redis_connection

from goods.models import GoodsSKU, GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from order.models import OrderGoods
from django.core.paginator import Paginator


# Create your views here.
# http://127.0.0.1:8000
# /index
class IndexView(View):
    """首页"""

    def get(self, request):
        """显示"""
        # 尝试从缓存中获取数据
        context = cache.get('index_page_data')  # None pickle

        if context is None:
            # 获取商品的分类信息
            print('设置首页缓存')
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

            # 缓存数据
            context = {
                'types': types,
                'index_banner': index_banner,
                'promotion_banner': promotion_banner,
                'cart_count': 0
            }

            # 设置首页缓存
            # from django.core.cache import cache
            # cache.set('缓存名称', '缓存数据', '缓存有效时间'} pickle
            cache.set('index_page_data', context, 3600)

        # 判断用户用户是否已登录
        cart_count = 0
        if request.user.is_authenticated():
            # 获取redis链接
            conn = get_redis_connection('default')

            print(request.user.id)
            # 拼接key
            cart_key = 'cart_%s' % request.user.id

            # 获取用户购物车中商品的条目数
            # hlen(key)-> 返回属性的数目
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context.update(cart_count=cart_count)

        # 使用模板
        return render(request, 'index.html', context)  # HttpResponse


# /goods/商品id
class DetailView(View):
    '''详情页'''

    def get(self, request, goods_id):
        '''显示详情页'''
        #
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return redirect(reverse('goods:index'))
        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取商品评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一个SPU的其他规格商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        cart_count = 0
        user = request.user
        if user.is_authenticated():
            # 获取redis链接
            conn = get_redis_connection('default')

            print(request.user.id)
            # 拼接key
            cart_key = 'cart_%s' % request.user.id

            # 获取用户购物车中商品的条目数
            # hlen(key)-> 返回属性的数目
            cart_count = conn.hlen(cart_key)

            # 添加历史浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id插入到左侧
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条信息
            conn.ltrim(history_key, 0, 4)

        context = {'sku': sku, 'type': types,
                   'sku_orders': sku_orders,
                   'same_spu_skus': same_spu_skus,
                   'new_skus': new_skus, 'cart_count': cart_count}
        return render(request, 'detail.html', context)


# 种类Id 页码 排序方式
#
class ListView(View):
    '''列表页'''

    def get(self, request, type_id, page):
        '''显示列表页'''
        # 获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))
        # 获取分类商品信息
        types = GoodsType.objects.all()
        # 获取排序方式
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 对数据进行分页
        paginator = Paginator(skus, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        skus_page = paginator.page(page)

        # 页码控制
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页 显示1-5
        # 3.如果当前页是后3页 显示后5页
        # 4.其他情况，显示当前页的前两页，当前页，当前页的后两页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        cart_count = 0
        user = request.user
        if user.is_authenticated():
            # 获取redis链接
            conn = get_redis_connection('default')

            print(request.user.id)
            # 拼接key
            cart_key = 'cart_%s' % request.user.id

            # 获取用户购物车中商品的条目数
            # hlen(key)-> 返回属性的数目
            cart_count = conn.hlen(cart_key)

        # 组织模版上下文
        context = {'type': type, 'types': types,
                   'skus_page': skus_page,
                   'new_skus': new_skus,
                   'cart_count': cart_count,
                   'pages':pages,
                   'sort': sort}

        return render(request, 'list.html', context)
