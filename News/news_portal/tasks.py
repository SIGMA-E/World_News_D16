from celery import shared_task
from .models import Post, PostCategory, SubscriberToCategory, Subscribers
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from dotenv import load_dotenv, find_dotenv
import os
from datetime import datetime, timedelta

load_dotenv(find_dotenv())


@shared_task  # рассылка писем при создании поста
def send_email_by_celery(post_id):
    post = Post.objects.get(id=post_id)

    # получаем список категорий поста
    categories_list = [i['category'] for i in PostCategory.objects.filter(post__id=post.id).values('category')]

    # получаем список всех email по категориям поста
    subscribers_email_list = list()
    for category_i in categories_list:
        subscribers_emails = SubscriberToCategory.objects.filter(category=category_i).values('subscriber__email')
        subscribers_email_i = [i['subscriber__email'] for i in subscribers_emails]
        subscribers_email_list += subscribers_email_i

    # получаем уникальный список email
    subscribers_email_list_unique = list(set(subscribers_email_list))

    # получаем список имен подписчиков по email
    subscribers_name_list = list()
    for email_i in subscribers_email_list_unique:
        subscribers_name_i = [i['name'] for i in Subscribers.objects.filter(email=email_i).values('name')]
        subscribers_name_list += subscribers_name_i

    # если есть подписчика на данный пост отправляем им письма
    if len(subscribers_email_list_unique) != 0:
        print('Sending emails by Celery')
        for i in range(len(subscribers_email_list_unique)):
            html_content = render_to_string('send_message_by_celery.html', {
                'username': subscribers_name_list[i],
                'title': post.title,
                'text_post': post.preview(),
                # подгружено из .env
                'link': f'{os.getenv("WORLD_NEWS_HOST")}{post.get_absolute_url()}'
            })
            message_html = EmailMultiAlternatives(
                subject=f'Вышел новый пост: {post.title}',
                # подгружено из .env
                from_email=os.getenv("DEFAULT_FROM_EMAIL"),
                to=[subscribers_email_list_unique[i]]
            )
            message_html.attach_alternative(html_content, 'text/html')
            message_html.send()
    else:
        print('Subscribers are not exist...')


@shared_task  # еженедельная рассылка писем
def send_email_every_week():
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    # создаем список имен и email всех подписчиков соответственно
    subscribers = Subscribers.objects.all().values('name', 'email')
    subscribers_name = [i['name'] for i in subscribers]
    subscribers_email = [i['email'] for i in subscribers]

    for i, name in enumerate(subscribers_name):
        # создаем список категорий каждого подписчика (у подписчика может быть несколько категорий)
        subscribers_category_id = [i['category'] for i in Subscribers.objects.filter(name=name).values('category')]
        # создаем список id постов на категорию которых подписан пользователь (несколько категорий)
        posts_list_id = list()
        for category_id in subscribers_category_id:
            post_gte = Post.objects.filter(category=category_id, time_post__gte=week_ago).values('id')
            post_list_id_i = [i['id'] for i in post_gte]
            posts_list_id += post_list_id_i

        # создаем уникальный список id постов и формируем QS модели Post отфильтрованных новостей
        posts_list_id_unique = list(set(posts_list_id))
        total_posts_list_qs = Post.objects.filter(id__in=posts_list_id_unique)

        # если у постов за неделю появились подписчики, то отсылаем им список постов
        if len(subscribers_name) != 0 and len(posts_list_id_unique) != 0:
            print(f'Письмо отправлено {name} на email {subscribers_email[i]}')
            html_content = render_to_string('send_posts_week_by_celery.html', {
                'username': name,
                'posts': total_posts_list_qs,
                # подгружено из .env
                'link': f'{os.getenv("WORLD_NEWS_HOST")}/news/'
            })
            message_html = EmailMultiAlternatives(
                subject='Список интересующих вас постов за неделю',
                # подгружено из .env
                from_email=os.getenv("DEFAULT_FROM_EMAIL"),
                to=[subscribers_email[i]]


            )
            message_html.attach_alternative(html_content, 'text/html')
            message_html.send()
        else:
            print('Нет подписчиков или новостей')
