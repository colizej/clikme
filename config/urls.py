from django.contrib import admin
from django.urls import path, include, register_converter
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import RedirectView

class TrailingSlashConverter:
    regex = r'/?'
    
    def to_python(self, value):
        return value.rstrip('/') if value.endswith('/') else value
    
    def to_url(self, value):
        return value

register_converter(TrailingSlashConverter, 'trailing_slash')

urlpatterns = [
    # Редиректы для миграции с OpenCart
    path('about_us/', RedirectView.as_view(url='/contacts/', permanent=True)),
    path('about_us', RedirectView.as_view(url='/contacts/', permanent=True)),
    path('delivery/', RedirectView.as_view(url='/contacts/', permanent=True)),
    path('delivery', RedirectView.as_view(url='/contacts/', permanent=True)),
    
    # Кириллические URL -> латиница
    path('%D0%BA%D0%B0%D0%BA-%D0%B0%D0%B4%D0%B0%D0%BF%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%BA-%D0%B6%D0%B8%D0%B7%D0%BD%D0%B8-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/kak-adaptirovatsya-k-zhizni-vo-vetname/', permanent=True)),
    path('%D0%BA%D0%B0%D0%BA-%D0%B0%D0%B4%D0%B0%D0%BF%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%BA-%D0%B6%D0%B8%D0%B7%D0%BD%D0%B8-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/kak-adaptirovatsya-k-zhizni-vo-vetname/', permanent=True)),
    path('%D0%9A%D0%B0%D0%BA-%D0%B4%D0%BE%D0%B1%D1%80%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%B8%D0%B7-%D0%B0%D1%8D%D1%80%D0%BE%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%9A%D0%B0%D0%BC%D1%80%D0%B0%D0%BD%D1%8C-%D0%B4%D0%BE-%D0%9D%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0/', RedirectView.as_view(url='/kak-dobratsya-iz-aeroporta-kamran-do-nyachanga/', permanent=True)),
    path('%D0%9A%D0%B0%D0%BA-%D0%B4%D0%BE%D0%B1%D1%80%D0%B0%D1%82%D1%8C%D1%81%D1%8F-%D0%B8%D0%B7-%D0%B0%D1%8D%D1%80%D0%BE%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%9A%D0%B0%D0%BC%D1%80%D0%B0%D0%BD%D1%8C-%D0%B4%D0%BE-%D0%9D%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0', RedirectView.as_view(url='/kak-dobratsya-iz-aeroporta-kamran-do-nyachanga/', permanent=True)),
    path('%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D1%8B-2025/', RedirectView.as_view(url='/obmen-valyuty-2025/', permanent=True)),
    path('%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D1%8B-2025', RedirectView.as_view(url='/obmen-valyuty-2025/', permanent=True)),
    path('%D0%B2%D1%81%D0%B5-%D0%BE%D0%B1-%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B5-%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%B2%D0%BE-%D0%B2%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/vse-ob-arende-transporta-vo-vetname/', permanent=True)),
    path('%D0%B2%D1%81%D0%B5-%D0%BE%D0%B1-%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B5-%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%B0-%D0%B2%D0%BE-%D0%B2%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/vse-ob-arende-transporta-vo-vetname/', permanent=True)),
    path('%D0%BF%D0%BB%D1%8F%D0%B6%D0%B8-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0-%D0%B1%D0%B5%D0%B7-%D0%B2%D0%BE%D0%BB%D0%BD/', RedirectView.as_view(url='/plyazhi-nyachanga-bez-voln-kak-dobratsya-interesnye-fakty/', permanent=True)),
    path('%D0%BF%D0%BB%D1%8F%D0%B6%D0%B8-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0-%D0%B1%D0%B5%D0%B7-%D0%B2%D0%BE%D0%BB%D0%BD', RedirectView.as_view(url='/plyazhi-nyachanga-bez-voln-kak-dobratsya-interesnye-fakty/', permanent=True)),
    path('%D0%BD%D0%B0%D0%B9%D1%82%D0%B8-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D1%8B-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/naiti-kvartiry-vietname-soveti-rekomendatsi/', permanent=True)),
    path('%D0%BD%D0%B0%D0%B9%D1%82%D0%B8-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D1%8B-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/naiti-kvartiry-vietname-soveti-rekomendatsi/', permanent=True)),
    path('%D0%BB%D1%83%D1%87%D1%88%D0%B8%D0%B5-%D0%B1%D1%83%D1%84%D0%B5%D1%82%D1%8B-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0/', RedirectView.as_view(url='/luchshie-bufety-nyachanga-gde-poest/', permanent=True)),
    path('%D0%BB%D1%83%D1%87%D1%88%D0%B8%D0%B5-%D0%B1%D1%83%D1%84%D0%B5%D1%82%D1%8B-%D0%BD%D1%8F%D1%87%D0%B0%D0%BD%D0%B3%D0%B0', RedirectView.as_view(url='/luchshie-bufety-nyachanga-gde-poest/', permanent=True)),
    path('%D0%BC%D0%B5%D0%B4%D0%B8%D1%86%D0%B8%D0%BD%D0%B0-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/medicina-vietnam-nado-znat/', permanent=True)),
    path('%D0%BC%D0%B5%D0%B4%D0%B8%D1%86%D0%B8%D0%BD%D0%B0-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/medicina-vietnam-nado-znat/', permanent=True)),
    path('%D0%BA%D0%B0%D0%BA-%D0%BD%D0%B0%D1%87%D0%B0%D1%82%D1%8C-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5/', RedirectView.as_view(url='/kak-nachat-rabotat-vo-vietname/', permanent=True)),
    path('%D0%BA%D0%B0%D0%BA-%D0%BD%D0%B0%D1%87%D0%B0%D1%82%D1%8C-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B2%D0%BE-%D0%92%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC%D0%B5', RedirectView.as_view(url='/kak-nachat-rabotat-vo-vietname/', permanent=True)),
    
    # Канонические URL для статических страниц (slug → короткий путь)
    path('politika-konfidencialnosti/', RedirectView.as_view(url='/privacy/', permanent=True)),
    path('pravila-ispolzovania/', RedirectView.as_view(url='/pravila/', permanent=True)),

    # Вендор id=7: кириллика -> латиница
    path('%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%BB%D0%B0%D1%80%D0%B5%D0%BA/', RedirectView.as_view(url='/muzykalnyy-larek/', permanent=True)),
    path('%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%BB%D0%B0%D1%80%D0%B5%D0%BA', RedirectView.as_view(url='/muzykalnyy-larek/', permanent=True)),

    # Товары: кириллические слаги -> транслитерация
    path('%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BB%D1%8E%D0%B1%D0%B2%D0%B8-%D1%81%D0%B1%D0%BE%D1%80%D0%BD%D0%B8%D0%BA-%D0%BD%D0%BE%D1%82-2/', RedirectView.as_view(url='/istoriya-lyubvi-sbornik-not-2/', permanent=True)),
    path('%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BB%D1%8E%D0%B1%D0%B2%D0%B8-%D1%81%D0%B1%D0%BE%D1%80%D0%BD%D0%B8%D0%BA-%D0%BD%D0%BE%D1%82-2', RedirectView.as_view(url='/istoriya-lyubvi-sbornik-not-2/', permanent=True)),
    path('%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BB%D1%8E%D0%B1%D0%B2%D0%B8-%D1%81%D0%B1%D0%BE%D1%80%D0%BD%D0%B8%D0%BA-%D0%BD%D0%BE%D1%82-1/', RedirectView.as_view(url='/istoriya-lyubvi-sbornik-not-1/', permanent=True)),
    path('%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BB%D1%8E%D0%B1%D0%B2%D0%B8-%D1%81%D0%B1%D0%BE%D1%80%D0%BD%D0%B8%D0%BA-%D0%BD%D0%BE%D1%82-1', RedirectView.as_view(url='/istoriya-lyubvi-sbornik-not-1/', permanent=True)),
    path('%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BB%D1%8E%D0%B1%D0%B2%D0%B8-%D1%81%D0%B1%D0%BE%D1%80%D0%BD%D0%B8%D0%BA-%D0%BD%D0%BE%D1%82-3/', RedirectView.as_view(url='/istoriya-lyubvi-sbornik-not-3/', permanent=True)),
    path('%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BB%D1%8E%D0%B1%D0%B2%D0%B8-%D1%81%D0%B1%D0%BE%D1%80%D0%BD%D0%B8%D0%BA-%D0%BD%D0%BE%D1%82-3', RedirectView.as_view(url='/istoriya-lyubvi-sbornik-not-3/', permanent=True)),
    path('%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-%D0%B4%D0%B5%D0%BD%D0%B5%D0%B3/', RedirectView.as_view(url='/obmen-deneg/', permanent=True)),
    path('%D0%BE%D0%B1%D0%BC%D0%B5%D0%BD-%D0%B4%D0%B5%D0%BD%D0%B5%D0%B3', RedirectView.as_view(url='/obmen-deneg/', permanent=True)),
    path('%D0%A0%D0%B0%D0%B7%D0%BD%D0%BE%D1%81%D0%BE%D0%BB%D1%8B/', RedirectView.as_view(url='/raznosoly/', permanent=True)),
    path('%D0%A0%D0%B0%D0%B7%D0%BD%D0%BE%D1%81%D0%BE%D0%BB%D1%8B', RedirectView.as_view(url='/raznosoly/', permanent=True)),
    path('%D0%9F%D0%B5%D0%BB%D1%8C%D0%BC%D0%B5%D0%BD%D0%B8/', RedirectView.as_view(url='/pelmeni/', permanent=True)),
    path('%D0%9F%D0%B5%D0%BB%D1%8C%D0%BC%D0%B5%D0%BD%D0%B8', RedirectView.as_view(url='/pelmeni/', permanent=True)),
    path('%D0%9A%D0%B5%D0%B4%D1%80%D0%BE%D0%B2%D0%B0%D1%8F-%D1%88%D0%B8%D1%88%D0%BA%D0%B0/', RedirectView.as_view(url='/kedrovaya-shishka/', permanent=True)),
    path('%D0%9A%D0%B5%D0%B4%D1%80%D0%BE%D0%B2%D0%B0%D1%8F-%D1%88%D0%B8%D1%88%D0%BA%D0%B0', RedirectView.as_view(url='/kedrovaya-shishka/', permanent=True)),
    path('%D1%81%D0%B0%D0%BB%D0%B0%D1%82-%D1%86%D0%B5%D0%B7%D0%B0%D1%80%D1%8C/', RedirectView.as_view(url='/salat-tsezar/', permanent=True)),
    path('%D1%81%D0%B0%D0%BB%D0%B0%D1%82-%D1%86%D0%B5%D0%B7%D0%B0%D1%80%D1%8C', RedirectView.as_view(url='/salat-tsezar/', permanent=True)),
    path('%D0%A1%D0%B0%D0%BB%D0%B0%D1%82-%D0%92%D0%B5%D1%81%D0%B5%D0%BD%D0%BD%D0%B8%D0%B9/', RedirectView.as_view(url='/salat-vesenniy/', permanent=True)),
    path('%D0%A1%D0%B0%D0%BB%D0%B0%D1%82-%D0%92%D0%B5%D1%81%D0%B5%D0%BD%D0%BD%D0%B8%D0%B9', RedirectView.as_view(url='/salat-vesenniy/', permanent=True)),
    path('%D0%9A%D1%80%D0%B5%D0%BC-%D1%81%D1%83%D0%BF/', RedirectView.as_view(url='/krem-sup/', permanent=True)),
    path('%D0%9A%D1%80%D0%B5%D0%BC-%D1%81%D1%83%D0%BF', RedirectView.as_view(url='/krem-sup/', permanent=True)),
    path('%D0%9A%D0%B0%D0%BB%D1%8C%D0%BC%D0%B0%D1%80%D1%8B/', RedirectView.as_view(url='/kalmary/', permanent=True)),
    path('%D0%9A%D0%B0%D0%BB%D1%8C%D0%BC%D0%B0%D1%80%D1%8B', RedirectView.as_view(url='/kalmary/', permanent=True)),
    path('%D0%97%D0%B0%D0%BA%D1%83%D1%81%D0%BA%D0%B0-%D0%9A%D0%B0%D0%BF%D1%80%D0%B8%D0%B7/', RedirectView.as_view(url='/zakuska-kapriz/', permanent=True)),
    path('%D0%97%D0%B0%D0%BA%D1%83%D1%81%D0%BA%D0%B0-%D0%9A%D0%B0%D0%BF%D1%80%D0%B8%D0%B7', RedirectView.as_view(url='/zakuska-kapriz/', permanent=True)),
    path('%D0%A1%D1%8B%D1%80%D0%BD%D0%B0%D1%8F-%D1%82%D0%B0%D1%80%D0%B5%D0%BB%D0%BA%D0%B0/', RedirectView.as_view(url='/syrnaya-tarelka/', permanent=True)),
    path('%D0%A1%D1%8B%D1%80%D0%BD%D0%B0%D1%8F-%D1%82%D0%B0%D1%80%D0%B5%D0%BB%D0%BA%D0%B0', RedirectView.as_view(url='/syrnaya-tarelka/', permanent=True)),
    path('%D0%BE%D0%B1%D0%B5%D0%B4-%D0%92%D0%B5%D1%81%D0%B5%D0%BD%D0%BD%D0%B8%D0%B9/', RedirectView.as_view(url='/obed-vesenniy/', permanent=True)),
    path('%D0%BE%D0%B1%D0%B5%D0%B4-%D0%92%D0%B5%D1%81%D0%B5%D0%BD%D0%BD%D0%B8%D0%B9', RedirectView.as_view(url='/obed-vesenniy/', permanent=True)),
    path('%D0%BA%D0%BE%D0%BC%D0%B1%D0%BE-%D1%88%D0%B0%D1%80%D0%BC/', RedirectView.as_view(url='/kombo-sharm/', permanent=True)),
    path('%D0%BA%D0%BE%D0%BC%D0%B1%D0%BE-%D1%88%D0%B0%D1%80%D0%BC', RedirectView.as_view(url='/kombo-sharm/', permanent=True)),
    path('%D0%BA%D0%BE%D0%BC%D0%B1%D0%BE-%D0%B4%D0%BE%D0%BC%D0%B0%D1%88%D0%BD%D0%B8%D0%B9/', RedirectView.as_view(url='/kombo-domashniy/', permanent=True)),
    path('%D0%BA%D0%BE%D0%BC%D0%B1%D0%BE-%D0%B4%D0%BE%D0%BC%D0%B0%D1%88%D0%BD%D0%B8%D0%B9', RedirectView.as_view(url='/kombo-domashniy/', permanent=True)),
    path('%D0%BF%D0%B8%D1%86%D1%86%D0%B0-%D0%9C%D0%B0%D1%80%D0%B3%D0%B0%D1%80%D0%B8%D1%82%D0%B0/', RedirectView.as_view(url='/pitstsa-margarita/', permanent=True)),
    path('%D0%BF%D0%B8%D1%86%D1%86%D0%B0-%D0%9C%D0%B0%D1%80%D0%B3%D0%B0%D1%80%D0%B8%D1%82%D0%B0', RedirectView.as_view(url='/pitstsa-margarita/', permanent=True)),
    path('%D0%BF%D0%B8%D1%86%D1%86%D0%B0-%D0%9F%D0%B5%D0%BF%D0%BF%D0%B5%D1%80%D0%BE%D0%BD%D0%B8/', RedirectView.as_view(url='/pitstsa-pepperoni/', permanent=True)),
    path('%D0%BF%D0%B8%D1%86%D1%86%D0%B0-%D0%9F%D0%B5%D0%BF%D0%BF%D0%B5%D1%80%D0%BE%D0%BD%D0%B8', RedirectView.as_view(url='/pitstsa-pepperoni/', permanent=True)),
    path('%D0%A7%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%81%D1%8B%D1%80%D0%B0/', RedirectView.as_view(url='/chetyre-syra/', permanent=True)),
    path('%D0%A7%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%81%D1%8B%D1%80%D0%B0', RedirectView.as_view(url='/chetyre-syra/', permanent=True)),
    path('%D0%9F%D0%B8%D1%80%D0%BE%D0%B6%D0%BD%D0%BE%D0%B5-%D0%9C%D0%B5%D0%B4%D0%BE%D0%B2%D0%B8%D0%BA/', RedirectView.as_view(url='/pirozhnoe-medovik/', permanent=True)),
    path('%D0%9F%D0%B8%D1%80%D0%BE%D0%B6%D0%BD%D0%BE%D0%B5-%D0%9C%D0%B5%D0%B4%D0%BE%D0%B2%D0%B8%D0%BA', RedirectView.as_view(url='/pirozhnoe-medovik/', permanent=True)),
    path('%D0%BF%D0%B8%D1%80%D0%BE%D0%B6%D0%BD%D0%BE%D0%B5-%D0%A2%D0%B8%D1%80%D0%B0%D0%BC%D0%B8%D1%81%D1%83/', RedirectView.as_view(url='/pirozhnoe-tiramisu/', permanent=True)),
    path('%D0%BF%D0%B8%D1%80%D0%BE%D0%B6%D0%BD%D0%BE%D0%B5-%D0%A2%D0%B8%D1%80%D0%B0%D0%BC%D0%B8%D1%81%D1%83', RedirectView.as_view(url='/pirozhnoe-tiramisu/', permanent=True)),
    path('%D0%94%D0%B5%D1%81%D0%B5%D1%80%D1%82-%D0%AD%D0%BA%D0%B7%D0%BE%D1%82%D0%B8%D0%BA%D0%B0/', RedirectView.as_view(url='/desert-ekzotika/', permanent=True)),
    path('%D0%94%D0%B5%D1%81%D0%B5%D1%80%D1%82-%D0%AD%D0%BA%D0%B7%D0%BE%D1%82%D0%B8%D0%BA%D0%B0', RedirectView.as_view(url='/desert-ekzotika/', permanent=True)),
    path('%D0%9A%D0%BE%D0%BA%D0%B0-%D0%9A%D0%BE%D0%BB%D0%B0/', RedirectView.as_view(url='/koka-kola/', permanent=True)),
    path('%D0%9A%D0%BE%D0%BA%D0%B0-%D0%9A%D0%BE%D0%BB%D0%B0', RedirectView.as_view(url='/koka-kola/', permanent=True)),
    path('%D0%9C%D0%BE%D1%80%D1%81-%D0%9A%D0%BB%D1%8E%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0/', RedirectView.as_view(url='/mors-klyukovka/', permanent=True)),
    path('%D0%9C%D0%BE%D1%80%D1%81-%D0%9A%D0%BB%D1%8E%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0', RedirectView.as_view(url='/mors-klyukovka/', permanent=True)),
    path('%D1%81%D0%B2%D0%B5%D0%B6%D0%B5%D0%B2%D1%8B%D0%B6%D0%B0%D1%82%D1%8B%D0%B9-%D1%81%D0%BE%D0%BA/', RedirectView.as_view(url='/svezhevyzhatyy-sok/', permanent=True)),
    path('%D1%81%D0%B2%D0%B5%D0%B6%D0%B5%D0%B2%D1%8B%D0%B6%D0%B0%D1%82%D1%8B%D0%B9-%D1%81%D0%BE%D0%BA', RedirectView.as_view(url='/svezhevyzhatyy-sok/', permanent=True)),
    path('%D0%B2%D0%B8%D0%B7%D0%B0%D1%80%D0%B0%D0%BD-%D0%B2%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC-45-%D0%B4%D0%BD%D0%B5%D0%B9/', RedirectView.as_view(url='/vizaran-vetnam-45-dney/', permanent=True)),
    path('%D0%B2%D0%B8%D0%B7%D0%B0%D1%80%D0%B0%D0%BD-%D0%B2%D1%8C%D0%B5%D1%82%D0%BD%D0%B0%D0%BC-45-%D0%B4%D0%BD%D0%B5%D0%B9', RedirectView.as_view(url='/vizaran-vetnam-45-dney/', permanent=True)),
    path('pelm%D0%B5%D0%BD%D0%B8-so-smetanoi-nha-trang/', RedirectView.as_view(url='/pelmeni-so-smetanoi-nha-trang/', permanent=True)),
    path('pelm%D0%B5%D0%BD%D0%B8-so-smetanoi-nha-trang', RedirectView.as_view(url='/pelmeni-so-smetanoi-nha-trang/', permanent=True)),
    path('krev%D0%B5%D1%82%D0%BA%D0%B8-tsvety-gril-nha-trang/', RedirectView.as_view(url='/krevetki-tsvety-gril-nha-trang/', permanent=True)),
    path('krev%D0%B5%D1%82%D0%BA%D0%B8-tsvety-gril-nha-trang', RedirectView.as_view(url='/krevetki-tsvety-gril-nha-trang/', permanent=True)),
    path('kur%D0%BE%D1%87%D0%BA%D0%B0-vyalenaya-soul-kitchen-nha-trang/', RedirectView.as_view(url='/kurochka-vyalenaya-soul-kitchen-nha-trang/', permanent=True)),
    path('kur%D0%BE%D1%87%D0%BA%D0%B0-vyalenaya-soul-kitchen-nha-trang', RedirectView.as_view(url='/kurochka-vyalenaya-soul-kitchen-nha-trang/', permanent=True)),

    # Тестовые вендоры из OpenCart (id=8,14,20) — редирект на список компаний
    path('test/', RedirectView.as_view(url='/vendors/', permanent=True)),
    path('test', RedirectView.as_view(url='/vendors/', permanent=True)),
    path('vendor/', RedirectView.as_view(url='/vendors/', permanent=True)),
    path('vendor', RedirectView.as_view(url='/vendors/', permanent=True)),
    path('food-store/', RedirectView.as_view(url='/vendors/', permanent=True)),
    path('food-store', RedirectView.as_view(url='/vendors/', permanent=True)),

    # OpenCart формат index.php
    path('index.php', RedirectView.as_view(url='/vendors/', permanent=True)),
    
    path(f'{settings.ADMIN_URL}/', admin.site.urls),

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),

    # Apps — blog первый (slug_dispatch проверяет статьи)
    path('news/', include('apps.news.urls')),
    path('', include('apps.pages.urls')),
    path('', include('apps.newsletter.urls')),
    path('', include('apps.ads.urls')),
    path('', include('apps.vendors.urls')),  # vendors/ — точное совпадение до catch-all
    path('', include('apps.blog.urls')),     # <slug>/ — catch-all последним

    # Robots
    path('robots.txt', include('apps.pages.robots')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
