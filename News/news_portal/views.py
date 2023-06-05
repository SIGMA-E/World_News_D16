from django.shortcuts import redirect, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from .models import Post, Category, Subscribers, SubscriberToCategory, Author, PostCategory
from .filters import PostFilter
from .forms import CreateNewsForm, UpdateNewsForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from .tasks import send_email_by_celery
from django.core.exceptions import ObjectDoesNotExist, BadRequest, DisallowedHost, FieldError, PermissionDenied
from django.template.exceptions import TemplateSyntaxError

from django.core.cache import cache

import time

import logging


class PostList(ListView):
    model = Post
    ordering = 'time_post'
    template_name = 'news.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):  # создаем форму для поиска по модели Post
        queryset = super().get_queryset()
        self.filterset = PostFilter(self.request.GET, queryset)
        return self.filterset.qs

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filterset'] = self.filterset  # помещаем форму в переменную

        if not self.request.user.is_staff:
            context['is_not_author'] = not self.request.user.groups.filter(name='authors').exists()
        # выводим категории, на которые пользователь подписан, в контекст
        if self.request.user.is_authenticated:
            if Subscribers.objects.filter(email=self.request.user.email).exists():
                subscriber = Subscribers.objects.get(email=self.request.user.email)
                subscriber_category = SubscriberToCategory.objects.filter(subscriber=subscriber)
                context['subscriber_category'] = subscriber_category.values('category__name_category')

        return context


class PostDetail(DetailView):
    model = Post
    template_name = 'post.html'
    context_object_name = 'post'
    # queryset = Post.objects.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_staff:
            context['is_not_author'] = not self.request.user.groups.filter(name='authors').exists()

        # выводим категории, на которые пользователь подписан, в контекст
        if self.request.user.is_authenticated:
            if Subscribers.objects.filter(email=self.request.user.email).exists():
                subscriber = Subscribers.objects.get(email=self.request.user.email)
                subscriber_category = SubscriberToCategory.objects.filter(subscriber=subscriber).values('category')
                context['subscriber_category'] = [i['category'] for i in subscriber_category]

            # если пользователь не подписан не на одну из категорий
            context['is_not_subscriber'] = not Subscribers.objects.filter(email=self.request.user.email).exists()
        return context

    # переопределяем метод get_object
    def get_object(self, queryset=None):
        obj = cache.get(f'post-{self.kwargs["pk"]}', None)  # ищем в кеше значение под собственно-созданным ключом

        # если такого объекта нет (при первом переходе его нет), то вносим в кеш объект из QS и создаем ему имя ключа
        if not obj:
            obj = super().get_object(queryset=self.queryset)
            cache.set(f'post-{self.kwargs["pk"]}', obj)  # поле kwargs достаем из объекта self
        return obj


class PostSearch(LoginRequiredMixin, PostList):  # представление формы поиска поста
    template_name = 'search.html'


class CreateNews(PermissionRequiredMixin, CreateView):  # представление формы для создания новости
    form_class = CreateNewsForm
    model = Post
    template_name = 'create.html'
    permission_required = 'news_portal.add_post'

    def form_valid(self, form):
        news = form.save(commit=False)
        news.type_post = 'nw'
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        super().post(self, request, *args, **kwargs)
        post = Post.objects.get(title=self.request.POST['title'])
        post_id = post.id
        # call task Celery
        send_email_by_celery.apply_async([post_id])
        return redirect(f'/news/{post.id}')


class CreateArticle(PermissionRequiredMixin, CreateView):  # представление для создания статьи
    form_class = CreateNewsForm
    model = Post
    template_name = 'create.html'
    permission_required = 'news_portal.add_post'

    def form_valid(self, form):
        article = form.save(commit=False)
        article.type_post = 'ar'
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        super().post(self, request, *args, **kwargs)
        post = Post.objects.get(title=self.request.POST['title'])
        post_id = post.id
        # call task Celery
        send_email_by_celery.apply_async([post_id])
        return redirect(f'/news/{post.id}')


class UpdateNews(PermissionRequiredMixin, UpdateView):  # представление для редактирования новости/статьи
    form_class = UpdateNewsForm
    model = Post
    template_name = 'update.html'
    permission_required = 'news_portal.change_post'


class DeleteNews(LoginRequiredMixin, DeleteView):  # представление для удаления новости/статьи
    model = Post
    template_name = 'delete.html'
    success_url = reverse_lazy('list')


@login_required
def upgrade_me(request):  # кнопка стать автором
    user = request.user
    author_group = Group.objects.get(name='authors')
    if not request.user.groups.filter(name='authors').exists():
        author_group.user_set.add(user)
    return redirect('/news')


@login_required   # представление для копки стать subscribe
def subscribe(request, id_post, id_category):

    # получаем категорию из БД поля Category модели Post (ManyToMany)
    category = Category.objects.get(id=id_category)
    subscriber_name = request.user.username
    subscriber_email = request.user.email

    # проверяем есть ли subscriber в таблице Subscribers (если нет - добавляем его)
    if not Subscribers.objects.filter(email=subscriber_email):
        subscriber = Subscribers.objects.create(name=subscriber_name, email=subscriber_email)
    else:
        subscriber = Subscribers.objects.get(email=subscriber_email)

    # проверяем есть ли subscriber в таблице SubscribersToCategory (подписывался ли?)
    if not SubscriberToCategory.objects.filter(subscriber=subscriber, category=category):
        SubscriberToCategory.objects.create(subscriber=subscriber, category=category)

    return redirect(f'/news/{id_post}/')  # возвращаемся на то же место сайта


@login_required()  # представление для отписки
def delete_subscribe(request, id_post, id_category):

    # получаем категорию из БД поля Category модели Post (ManyToMany)
    category = Category.objects.get(id=id_category)
    subscriber_name = request.user.username
    subscriber_email = request.user.email

    # проверяем есть ли subscriber в таблице Subscribers
    if Subscribers.objects.filter(email=subscriber_email):
        subscriber = Subscribers.objects.get(email=subscriber_email)

    # проверяем есть ли subscriber в таблице SubscribersToCategory (подписывался ли?)
    subscriber_category = SubscriberToCategory.objects.filter(subscriber=subscriber, category=category)
    if subscriber_category:
        subscriber_category.delete()

    return redirect(f'/news/{id_post}/')  # возвращаемся на то же место сайта


# Страницы для тестирования логирования
class CheckLogging(TemplateView):
    template_name = 'check_logging.html'


logger_task_1 = logging.getLogger('django')
logger_task_3r = logging.getLogger('django.request')
logger_task_3s = logging.getLogger('django.server')
logger_task_3t = logging.getLogger('django.template')
logger_task_3d = logging.getLogger('django.db.backends')
logger_task_4 = logging.getLogger('django.security')


def check_logs_buttons_task_1(request):  # кнопки DEBUG, WARNING, ERROR, CRITICAL для вывода в консоль task_1, task_2
    if request.resolver_match.url_name == 'debug':  # кнопка DEBUG
        logger_task_1.debug('error_DEBUG')
    elif request.resolver_match.url_name == 'warning':  # кнопка WARNING
        logger_task_1.warning('error_WARNING')
    elif request.resolver_match.url_name == 'error':  # кнопка ERROR
        try:
            raise ObjectDoesNotExist
        except ObjectDoesNotExist:
            logger_task_1.error('ERROR: The requested object does not exist', exc_info=True)
    elif request.resolver_match.url_name == 'critical':  # кнопка CRITICAL
        try:
            raise ObjectDoesNotExist
        except ObjectDoesNotExist:
            logger_task_1.error('CRITICAL: The requested object does not exist', exc_info=True)
    return redirect('logging')


def check_logs_button_info(request):  # кнопка INFO для записи логов в файл general.log task_2
    logger_task_1.info('error_INFO')
    return redirect('logging')


def check_logs_buttons_task_3(request):  # кнопка ERROR и CRITICAL для вывода логов в файл errors.log task_3
    if request.resolver_match.url_name == 'error_t3r':  # кнопка ERROR (для django.request)
        try:
            raise BadRequest
        except BadRequest:
            logger_task_3r.error('ERROR Request - The request is malformed and cannot be processed', exc_info=True)
    elif request.resolver_match.url_name == 'critical_t3r':  # кнопка CRITICAL (для django.request)
        try:
            raise BadRequest
        except BadRequest:
            logger_task_3r.critical(
                'CRITICAL Request - The request is malformed and cannot be processed',
                exc_info=True
            )

    elif request.resolver_match.url_name == 'error_t3s':  # кнопка ERROR (для django.server)
        try:
            raise DisallowedHost
        except DisallowedHost:
            logger_task_3s.error('ERROR Server - HTTP_HOST header contains invalid value', exc_info=True)
    elif request.resolver_match.url_name == 'critical_t3s':  # кнопка CRITICAL (для django.server)
        try:
            raise DisallowedHost
        except DisallowedHost:
            logger_task_3s.critical('CRITICAL Server - HTTP_HOST header contains invalid value', exc_info=True)

    elif request.resolver_match.url_name == 'error_t3t':  # кнопка ERROR (для django.template)
        try:
            raise TemplateSyntaxError
        except TemplateSyntaxError:
            logger_task_3t.error(
                'ERROR Template - The exception used for syntax errors during parsing or rendering',
                exc_info=True
            )
    elif request.resolver_match.url_name == 'critical_t3t':  # кнопка CRITICAL (для django.server)
        try:
            raise TemplateSyntaxError
        except TemplateSyntaxError:
            logger_task_3t.critical(
                'CRITICAL Template - The exception used for syntax errors during parsing or rendering',
                exc_info=True
            )

    elif request.resolver_match.url_name == 'error_t3d':  # кнопка ERROR (для django.db.backends)
        try:
            raise FieldError
        except FieldError:
            logger_task_3d.error('ERROR DataBase - Some kind of problem with a model field', exc_info=True)
    elif request.resolver_match.url_name == 'critical_t3d':  # кнопка CRITICAL (для django.db.backends)
        try:
            raise FieldError
        except FieldError:
            logger_task_3d.critical('CRITICAL DataBase - Some kind of problem with a model field', exc_info=True)
    return redirect('logging')


def check_logs_button_task_4(request):  # кнопка INFO, WARNING, ERROR, CRITICAL для вывода логов security.log task_4
    if request.resolver_match.url_name == 'security_info':  # кнопка INFO (для django.security)
        logger_task_4.info('INFO Security - The user did not have permission to do that')
    elif request.resolver_match.url_name == 'security_warning':  # кнопка WARNING (для django.security)
        logger_task_4.warning('INFO Warning - The user did not have permission to do that')
    elif request.resolver_match.url_name == 'security_error':  # кнопка ERROR (для django.security)
        logger_task_4.error('INFO ERROR - The user did not have permission to do that')
    elif request.resolver_match.url_name == 'security_critical':  # кнопка CRITICAL (для django.security)
        logger_task_4.critical('INFO CRITICAL - The user did not have permission to do that')
    return redirect('logging')
