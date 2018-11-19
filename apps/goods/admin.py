from django.contrib import admin
from goods.models import GoodsType, IndexPromotionBanner, IndexGoodsBanner, IndexTypeGoodsBanner
from django.core.cache import cache

# Register your models here.
class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''更新表中的数据时调用'''
        super().save_model(request, obj, form, change)

        # 发出任务，让celery worker重新生成首页静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 删除页面缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        '''删除表中数据调用'''
        super().delete_model(request, obj)
        # 发出任务，让celery worker重新生成首页静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 删除页面缓存
        cache.delete('index_page_data')


class IndexPromotionBannerAdmin(admin.ModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(admin.ModelAdmin):
    pass


class IndexGoodsBannerAdmin(admin.ModelAdmin):
    pass


class GoodsTypeAdmin(admin.ModelAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)

admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
