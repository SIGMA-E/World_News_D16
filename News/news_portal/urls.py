from django.urls import path
from django.views.decorators.cache import cache_page
from .views import (
    PostList, PostDetail, PostSearch, CreateNews, UpdateNews, DeleteNews,
    CreateArticle, upgrade_me, subscribe, delete_subscribe, CheckLogging,
    check_logs_buttons_task_1, check_logs_button_info, check_logs_buttons_task_3,
    check_logs_button_task_4
)


urlpatterns = [
    path('', PostList.as_view(), name='list'),
    path('<int:pk>/', PostDetail.as_view(), name='detail'),
    path('search/', PostSearch.as_view(), name='search'),
    path('create/', CreateNews.as_view(), name='create_news'),
    path('<int:pk>/update/', UpdateNews.as_view(), name='update_news'),
    path('<int:pk>/delete/', DeleteNews.as_view(), name='delete_news'),
    path('article/create/', CreateArticle.as_view(), name='create_article'),
    path('article/<int:pk>/update', UpdateNews.as_view(), name='update_article'),
    path('article/<int:pk>/delete', DeleteNews.as_view(), name='delete_article'),
    path('upgrade/', upgrade_me, name='upgrade_user'),
    path('<int:id_post>/subscribe/<int:id_category>/', subscribe, name='subscribe_category'),
    path('<int:id_post>/delete_subscribe/<int:id_category>/', delete_subscribe, name='delete_subscribe'),
    path('logging/', CheckLogging.as_view(), name='logging'),  # url для теста логирования (основная страница)
    path('logging/debug', check_logs_buttons_task_1, name='debug'),  # кнопка DEBUG для вывода логов в консоль
    path('logging/warning', check_logs_buttons_task_1, name='warning'),  # кнопка WARNING для вывода логов в консоль
    path('logging/error', check_logs_buttons_task_1, name='error'),  # кнопка ERROR для вывода логов в консоль
    path('logging/critical', check_logs_buttons_task_1, name='critical'),  # кнопка CRITICAL для вывода логов в консоль
    path('logging/info', check_logs_button_info, name='info'),  # кнопка INFO для вывода в консоль и файл generals.log
    path('logging/error_t3r', check_logs_buttons_task_3, name='error_t3r'),  # кнопка ERROR для вывода в файл errors.log
    path('logging/critical_t3r', check_logs_buttons_task_3, name='critical_t3r'),  # кнопка CRITICAL для вывода в файл
    path('logging/error_t3s', check_logs_buttons_task_3, name='error_t3s'),  # кнопка ERROR для вывода в файл errors.log
    path('logging/critical_t3s', check_logs_buttons_task_3, name='critical_t3s'),  # кнопка CRITICAL для вывода в файл
    path('logging/error_t3t', check_logs_buttons_task_3, name='error_t3t'),  # кнопка ERROR для вывода в файл errors.log
    path('logging/critical_t3t', check_logs_buttons_task_3, name='critical_t3t'),  # кнопка CRITICAL для вывода в файл
    path('logging/error_t3d', check_logs_buttons_task_3, name='error_t3d'),  # кнопка ERROR для вывода в файл errors.log
    path('logging/critical_t3d', check_logs_buttons_task_3, name='critical_t3d'),  # кнопка CRITICAL для вывода в файл
    path('logging/security_info', check_logs_button_task_4, name='security_info'),  # кнопка INFO в security.log
    path('logging/security_warning', check_logs_button_task_4, name='security_warning'),  # кн. WARNING в security.log
    path('logging/security_error', check_logs_button_task_4, name='security_error'),  # кнопка ERROR в security.log
    path('logging/security_critical', check_logs_button_task_4, name='security_critical'),  # CRITICAL в security.log
]
