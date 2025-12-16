import requests
from bs4 import BeautifulSoup
import time
import re
import csv
from typing import List, Dict

# Класс-заглушка для Rusprofile, пока не реализован парсинг
class RusprofileParser:
    def __init__(self):
        print("Инициализирован RusprofileParser (заглушка)")
    
    def get_financials(self, inn):
        # В реальности здесь должен быть парсинг rusprofile.ru
        # Сейчас возвращаем тестовые данные
        return {
            'inn': inn,
            'name': f'Компания_{inn}',
            'revenue': 150000000,  # Всегда > 100 млн для теста
            'employees': 50,
            'site': f'www.company{inn}.ru',
            'cat_product': 'Trados/Smartcat',
            'okved_main': '62.01'
        }

class SuperJobParser:
    BASE_URL = "https://www.superjob.ru/vakansii/"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search_companies_by_keywords(self, keywords: List[str], max_results: int = 30) -> List[Dict]:
        companies = {}
        session = requests.Session()
        
        for keyword in keywords:
            print(f"🔍 Поиск по слову: '{keyword}'...")
            search_query = keyword.replace(' ', '+')
            url = f"{self.BASE_URL}?keywords={search_query}&town=4"
            
            try:
                response = session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем вакансии (проверьте актуальность селекторов!)
                vacancy_items = soup.find_all('div', class_='f-test-search-result-item')
                if not vacancy_items:
                    vacancy_items = soup.find_all('div', {'class': re.compile(r'.*search-result-item.*')})
                
                for item in vacancy_items[:max_results]:
                    company_block = item.find('span', class_='f-test-text-vacancy-item-company-name')
                    if not company_block:
                        continue
                    
                    company_name = company_block.get_text(strip=True)
                    if not company_name or company_name.lower() == 'скрыто':
                        continue
                    
                    # Генерируем ИНН для теста (в реальности нужно искать на rusprofile)
                    company_id = re.sub(r'\W+', '_', company_name.lower())
                    fake_inn = ''.join([str(ord(c) % 10) for c in company_name[:10]]).ljust(10, '0')[:10]
                    
                    if company_id not in companies:
                        companies[company_id] = {
                            'name': company_name,
                            'inn': fake_inn,  # Тестовый ИНН
                            'source': 'superjob.ru',
                            'cat_evidence': f'Вакансия: {keyword}',
                            'keywords_found': [keyword]
                        }
                    else:
                        if keyword not in companies[company_id]['keywords_found']:
                            companies[company_id]['keywords_found'].append(keyword)
                            companies[company_id]['cat_evidence'] += f', {keyword}'
                
                time.sleep(1)
                
            except Exception as e:
                print(f"   Ошибка: {e}")
                continue
        
        # Преобразуем в список
        result_list = list(companies.values())
        for company in result_list:
            company.pop('keywords_found', None)
        
        return result_list

# --- Запуск ---
if __name__ == "__main__":
    # Установите библиотеки если нужно:
    # pip install requests beautifulsoup4 lxml
    
    cat_keywords = [
        "Trados", "memoQ", "Smartcat", "Crowdin", "Phrase",
        "translation memory", "память переводов", "CAT tool",
        "локализация", "переводчик", "технический писатель"
    ]
    
    parser = SuperJobParser()
    print("Начинаем парсинг SuperJob.ru...")
    found_companies = parser.search_companies_by_keywords(cat_keywords, max_results=15)
    
    print(f"Найдено компаний: {len(found_companies)}")
    
    # Фильтрация через Rusprofile (заглушка)
    rusprofile = RusprofileParser()
    filtered_companies = []
    
    for company in found_companies:
        inn = company.get('inn')
        if inn:
            financials = rusprofile.get_financials(inn)
            if financials and financials.get('revenue', 0) >= 100_000_000:
                # Объединяем данные
                company.update(financials)
                filtered_companies.append(company)
    
    print(f"После фильтрации: {len(filtered_companies)} компаний")
    
    # Сохраняем
    if filtered_companies:
        with open('superjob_companies.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['inn', 'name', 'revenue', 'site', 'source', 
                         'cat_evidence', 'cat_product', 'employees', 'okved_main']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_companies)
        
        print(f"✅ Сохранено в superjob_companies.csv")
        for i, company in enumerate(filtered_companies[:3]):
            print(f"   {i+1}. {company['name']} - {company['revenue']} руб.")
    else:
        print("❌ Нет данных для сохранения")
    pass


