from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.core.cache import cache

from .models import Subscriber


class SubscribeView(View):
    def post(self, request):
        # Honeypot
        if request.POST.get('website'):
            return JsonResponse({'ok': True})

        # Rate limit: 1 request per 60s per IP
        ip = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
              or request.META.get('REMOTE_ADDR', ''))
        if cache.get(f'subscribe_{ip}'):
            return JsonResponse({'error': 'Подождите перед повторной попыткой'}, status=429)
        cache.set(f'subscribe_{ip}', 1, timeout=60)

        email = request.POST.get('email', '').strip().lower()
        if not email or '@' not in email:
            return JsonResponse({'error': 'Неверный email'}, status=400)

        subscriber, created = Subscriber.objects.get_or_create(
            email=email,
            defaults={
                'consent_given_at': timezone.now(),
                'ip_address': ip,
            }
        )
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.consent_given_at = timezone.now()
            subscriber.save(update_fields=['is_active', 'consent_given_at'])

        return JsonResponse({'ok': True, 'message': 'Спасибо! Вы подписаны на рассылку.'})


class UnsubscribeView(View):
    def get(self, request, token):
        subscriber = get_object_or_404(Subscriber, token=token)
        subscriber.is_active = False
        subscriber.save(update_fields=['is_active'])
        return redirect('/?unsubscribed=1')
