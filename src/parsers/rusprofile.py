import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, Optional

class RusprofileParser:
    """Парсер для получения финансовых данных компании с Rusprofile.ru"""
    
    def __init__(self):
        self.base_url = "https://www.rusprofile.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_company_info(self, inn: str) -> Optional[Dict]:
        """Основной метод: получает все данные компании по ИНН"""
        try:
            # 1. Получаем HTML страницы компании
            html = self._fetch_company_page(inn)
            if not html:
                return None
            
            # 2. Парсим данные
            soup = BeautifulSoup(html, 'html.parser')
            
            company_data = {
                'inn': inn,
                'name': self._extract_name(soup),
                'revenue': self._extract_revenue(soup),
                'employees': self._extract_employees(soup),
                'site': self._extract_website(soup),
                'okved_main': self._extract_okved(soup),
                'full_address': self._extract_address(soup),
                'ceo': self._extract_ceo(soup),
                'registration_date': self._extract_reg_date(soup),
                'status': self._extract_status(soup)
            }
            
            return company_data
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге компании {inn}: {e}")
            return None
    
    def _fetch_company_page(self, inn: str) -> Optional[str]:
        """Загружает страницу компании"""
        try:
            search_url = f"{self.base_url}/search?query={inn}&type=ul"
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            # Ищем ссылку на карточку компании
            soup = BeautifulSoup(response.text, 'html.parser')
            company_link = soup.find('a', class_='company-item')
            
            if company_link and 'href' in company_link.attrs:
                company_url = self.base_url + company_link['href']
                print(f"🔗 Найдена страница: {company_url}")
                
                time.sleep(1)  # Уважаем сервер
                company_response = self.session.get(company_url, timeout=10)
                company_response.raise_for_status()
                
                return company_response.text
            else:
                print(f"⚠️ Компания с ИНН {inn} не найдена")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Ошибка сети для ИНН {inn}: {e}")
            return None
    
    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Извлекает название компании"""
        try:
            name_tag = soup.find('h1', class_='company-name')
            if name_tag:
                return name_tag.get_text(strip=True)
            
            # Альтернативный поиск
            name_tag = soup.find('div', {'itemprop': 'name'})
            if name_tag:
                return name_tag.get_text(strip=True)
        except:
            pass
        return f"Компания_{soup.find('title').get_text()[:50]}"
    
    def _extract_revenue(self, soup: BeautifulSoup) -> int:
        """Извлекает выручку (последний доступный год)"""
        try:
            # Ищем блок с финансовыми показателями
            fin_section = soup.find('div', class_='company-requisites')
            if not fin_section:
                fin_section = soup.find('section', id='finance')
            
            if fin_section:
                # Ищем выручку по тексту
                fin_text = fin_section.get_text()
                
                # Паттерны для поиска выручки
                patterns = [
                    r'Выручка[^0-9]*([0-9, ]+)\s*(тыс|млн|млрд|₽|руб)',
                    r'Revenue[^0-9]*([0-9, ]+)\s*(тыс|млн|млрд|₽|руb)',
                    r'ВЫРУЧКА[^0-9]*([0-9, ]+)\s*(тыс|млн|млрд|₽|руб)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, fin_text, re.IGNORECASE)
                    if match:
                        revenue_str = match.group(1).replace(' ', '').replace(',', '.')
                        multiplier = self._get_multiplier(match.group(2).lower() if match.group(2) else '')
                        revenue = float(revenue_str) * multiplier
                        return int(revenue)
            
            # Если не нашли в блоке, ищем в таблице
            revenue_cells = soup.find_all('td', string=re.compile(r'Выручка|Revenue', re.I))
            for cell in revenue_cells:
                next_cell = cell.find_next('td')
                if next_cell:
                    value_text = next_cell.get_text(strip=True)
                    return self._parse_financial_value(value_text)
                    
        except Exception as e:
            print(f"⚠️ Ошибка извлечения выручки: {e}")
        
        return 0
    
    def _extract_employees(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлекает количество сотрудников"""
        try:
            # Ищем по ключевым словам
            employee_text = soup.find(string=re.compile(r'сотрудник|работник|персонал|employees|staff', re.I))
            if employee_text:
                # Ищем число рядом с текстом
                parent = employee_text.parent
                if parent:
                    text = parent.get_text()
                    match = re.search(r'(\d[\d ]*)\s*сотрудник', text, re.I)
                    if match:
                        return int(match.group(1).replace(' ', ''))
            
            # Альтернативный поиск в блоке "Общие сведения"
            info_section = soup.find('div', class_='company-info')
            if info_section:
                text = info_section.get_text()
                matches = re.findall(r'(\d+)\s*(?:человек|сотрудник|работник)', text, re.I)
                if matches:
                    return int(matches[-1])
                    
        except:
            pass
        return None
    
    def _extract_website(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает сайт компании"""
        try:
            # Ищем ссылку с классом или атрибутом
            website_tag = soup.find('a', {'class': re.compile(r'website|site|url', re.I)})
            if not website_tag:
                website_tag = soup.find('a', href=re.compile(r'^https?://'))
            
            if website_tag and 'href' in website_tag.attrs:
                url = website_tag['href']
                if not url.startswith('http'):
                    url = 'http://' + url
                return url
                
        except:
            pass
        return None
    
    def _extract_okved(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает основной ОКВЭД"""
        try:
            # Ищем ОКВЭД в тексте
            okved_tags = soup.find_all(string=re.compile(r'ОКВЭД|ОКВЭД2|Вид деятельности', re.I))
            for tag in okved_tags:
                parent = tag.parent
                if parent:
                    # Ищем код ОКВЭД (формат XX.XX или XX.XX.X)
                    text = parent.get_text()
                    match = re.search(r'(\d{2}\.\d{2}(?:\.\d{1,2})?)', text)
                    if match:
                        return match.group(1)
            
            # Поиск в блоке деятельности
            activity_section = soup.find('div', class_=re.compile(r'activity|business|деятельность', re.I))
            if activity_section:
                text = activity_section.get_text()
                match = re.search(r'(\d{2}\.\d{2}(?:\.\d{1,2})?)', text)
                if match:
                    return match.group(1)
                    
        except:
            pass
        return None
    
    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает полный адрес"""
        try:
            address_tag = soup.find('span', {'itemprop': 'address'})
            if not address_tag:
                address_tag = soup.find('div', class_='company-address')
            
            if address_tag:
                return address_tag.get_text(strip=True)
                
        except:
            pass
        return None
    
    def _extract_ceo(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает ФИО генерального директора"""
        try:
            ceo_tags = soup.find_all(string=re.compile(r'Генеральный директор|Директор|Руководитель|CEO', re.I))
            for tag in ceo_tags:
                parent = tag.parent
                if parent:
                    # Берем следующий текстовый элемент после "Директор"
                    text = parent.get_text()
                    # Ищем ФИО (русские буквы, пробелы, дефисы)
                    match = re.search(r'(?:Директор|Ген\.\s*директор|Руководитель)[:\s]+([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)', text)
                    if match:
                        return match.group(1)
        except:
            pass
        return None
    
    def _extract_reg_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает дату регистрации"""
        try:
            reg_tags = soup.find_all(string=re.compile(r'Дата регистрации|Зарегистрирована|Регистрация', re.I))
            for tag in reg_tags:
                parent = tag.parent
                if parent:
                    text = parent.get_text()
                    # Ищем дату в формате ДД.ММ.ГГГГ
                    match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
                    if match:
                        return match.group(1)
        except:
            pass
        return None
    
    def _extract_status(self, soup: BeautifulSoup) -> str:
        """Определяет статус компании"""
        try:
            status_tags = soup.find_all(string=re.compile(r'Статус|Состояние|Status', re.I))
            for tag in status_tags:
                parent = tag.parent
                if parent:
                    text = parent.get_text()
                    if re.search(r'действующ|active|working', text, re.I):
                        return 'Действующая'
                    elif re.search(r'ликвидир|банкрот|liquidated|bankrupt', text, re.I):
                        return 'Ликвидирована'
        except:
            pass
        return 'Неизвестно'
    
    def _parse_financial_value(self, text: str) -> int:
        """Парсит финансовые значения с множителями (тыс, млн, млрд)"""
        try:
            text = text.lower().strip()
            # Удаляем валюту и пробелы
            text = re.sub(r'[₽руб$€]', '', text)
            text = text.replace(' ', '').replace(',', '.')
            
            # Определяем множитель
            multiplier = 1
            if 'млрд' in text:
                multiplier = 1_000_000_000
                text = text.replace('млрд', '')
            elif 'млн' in text:
                multiplier = 1_000_000
                text = text.replace('млн', '')
            elif 'тыс' in text:
                multiplier = 1_000
                text = text.replace('тыс', '')
            
            # Извлекаем число
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                return int(float(match.group(1)) * multiplier)
        except:
            pass
        return 0
    
    def _get_multiplier(self, unit: str) -> int:
        """Возвращает числовой множитель для единиц измерения"""
        multipliers = {
            'тыс': 1_000,
            'млн': 1_000_000,
            'млрд': 1_000_000_000,
            'трлн': 1_000_000_000_000,
            'k': 1_000,
            'm': 1_000_000,
            'b': 1_000_000_000
        }
        return multipliers.get(unit.lower(), 1)
    
    def search_by_name(self, company_name: str, limit: int = 10) -> list:
        """Ищет компании по названию (возвращает список ИНН)"""
        try:
            search_query = company_name.replace(' ', '+')
            url = f"{self.base_url}/search?query={search_query}"
            
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            companies = []
            company_items = soup.find_all('div', class_='company-item')
            
            for item in company_items[:limit]:
                inn_tag = item.find('span', string=re.compile(r'ИНН'))
                if inn_tag:
                    inn_text = inn_tag.get_text()
                    inn_match = re.search(r'\b\d{10,12}\b', inn_text)
                    if inn_match:
                        companies.append({
                            'inn': inn_match.group(0),
                            'name': item.find('a', class_='company-item-title').get_text(strip=True) if item.find('a', class_='company-item-title') else 'Неизвестно'
                        })
            
            return companies
            
        except Exception as e:
            print(f"❌ Ошибка поиска по названию: {e}")
            return []

# --- Пример использования ---
if __name__ == "__main__":
    print("🧪 Тестирование парсера Rusprofile")
    parser = RusprofileParser()
    
    # Тестовые ИНН известных компаний
    test_inns = [
        "4574170000",  # 1C
        "7736207543",  # Яндекс
        "7707049388",  # Сбер
        "7727734900"   # Тинькофф
    ]
    
    for inn in test_inns:
        print(f"\n📊 Парсим компанию с ИНН {inn}...")
        data = parser.get_company_info(inn)
        
        if data:
            print(f"✅ Название: {data.get('name')}")
            print(f"   Выручка: {data.get('revenue'):,} руб" if data.get('revenue') else "   Выручка: не найдена")
            print(f"   Сотрудники: {data.get('employees')}" if data.get('employees') else "   Сотрудники: не найдено")
            print(f"   Сайт: {data.get('site')}" if data.get('site') else "   Сайт: не найден")
            print(f"   ОКВЭД: {data.get('okved_main')}" if data.get('okved_main') else "   ОКВЭД: не найден")
            print(f"   Статус: {data.get('status')}")
            
            # Проверяем критерий 100 млн рублей
            if data.get('revenue', 0) >= 100_000_000:
                print("   🟢 Критерий выручки выполнен (>100 млн руб)")
            else:
                print("   🔴 Критерий выручки не выполнен")
        else:
            print(f"❌ Не удалось получить данные")
        
        time.sleep(2)  # Пауза между запросами
