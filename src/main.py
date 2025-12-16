import sys
import os

# Добавляем папку проекта в путь поиска
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Теперь импортируем
try:
    from superjob_parser import SuperJobParser
    from rusprofile_parser import RusprofileParser
    print("Модули загружены")
except ImportError as e:
    print(f"Ошибка: {e}")
    print("Убедитесь, что superjob_parser.py и rusprofile_parser.py в той же папке")
    sys.exit(1)

def main():
    class SuperJobParser:
        """
        Парсер для поиска компаний на SuperJob.ru по ключевым словам.
        Работает через анализ HTML (API SuperJob недоступно).
        """
        BASE_URL = "https://www.superjob.ru/vakansii/"

    def __init__(self):
        # Эмулируем заголовки браузера
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def search_companies_by_keywords(self, keywords: List[str], max_results: int = 30) -> List[Dict]:
        """
        Ищет вакансии по ключевым словам и возвращает список уникальных работодателей.
        """
        companies = {}
        session = requests.Session()

        for keyword in keywords:
            print(f"Поиск по слову: '{keyword}'...")

            # Формируем URL. Пробелы заменяем на '+'.
            search_query = keyword.replace(' ', '+')
            # Добавляем параметр поиска в Москве, можно изменить на другой регион
            url = f"{self.BASE_URL}?keywords={search_query}&town=4"

            try:
                response = session.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()

                # Проверяем кодировку
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')

                # Контейнер с вакансиями. Класс нужно проверять на актуальность.
                vacancy_items = soup.find_all('div', class_='f-test-search-result-item')
                if not vacancy_items:
                    # Альтернативный селектор, если изменилась верстка
                    vacancy_items = soup.find_all('div', {'class': re.compile(r'.*search-result-item.*')})

                for item in vacancy_items[:max_results]:
                    # Ищем блок с названием компании
                    company_block = item.find('span', class_='f-test-text-vacancy-item-company-name')
                    if not company_block:
                        continue

                    company_name = company_block.get_text(strip=True)
                    if not company_name or company_name.lower() == 'скрыто':
                        continue

                    # Создаем простой ID из названия
                    company_id = re.sub(r'\W+', '_', company_name.lower())

                    if company_id not in companies:
                        companies[company_id] = {
                            'name': company_name,
                            'source': 'superjob.ru',
                            'cat_evidence': f'Вакансия с упоминанием: {keyword}',
                            'keywords_found': [keyword]
                        }
                    else:
                        # Добавляем ключевое слово, если компания уже найдена
                        if keyword not in companies[company_id]['keywords_found']:
                            companies[company_id]['keywords_found'].append(keyword)
                            companies[company_id]['cat_evidence'] += f', {keyword}'

                # Уважаем сайт - делаем паузу
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f"   Ошибка при запросе для '{keyword}': {e}")
                continue
            except Exception as e:
                print(f"   Ошибка при обработке HTML для '{keyword}': {e}")
                continue

        # Преобразуем словарь в список и убираем служебное поле
        result_list = list(companies.values())
        for company in result_list:
            company.pop('keywords_found', None)

        return result_list
-
if __name__ == "__main__":
    print("Установка необходимых библиотек...")
    
    # Ключевые слова для CAT-систем и локализации
    cat_keywords = [
        "Trados", "memoQ", "Smartcat", "Crowdin", "Phrase",
        "translation memory", "память переводов", "CAT tool",
        "локализация", "переводчик", "технический писатель", "Technical Writer"
    ]

    parser = SuperJobParser()
    print("Начинаем парсинг SuperJob.ru...")
    found_companies = parser.search_companies_by_keywords(cat_keywords, max_results=30)

    
    from rusprofile import RusprofileParser

parser = RusprofileParser()
company_data = parser.get_company_info("7706235750")

if company_data and company_data['revenue'] >= 100_000_000:
    print(f"{company_data['name']} подходит: выручка {company_data['revenue']:,} руб")
    
    
    
    rusprofile = RusprofileParser()
    filtered_companies = []
    for company in found_companies:
        inn = company.get('inn')
        if inn:
            financials = rusprofile.get_financials(inn)
            if financials and financials.get('revenue', 0) >= 100_000_000:
                company.update(financials)
                filtered_companies.append(company)

    print(f"После фильтрации по выручке: {len(filtered_companies)} компаний")
    
    # Сохраняем в CSV
    if filtered_companies:
        output_file = 'superjob_companies.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            # Поля соответствуют вашему проекту
            fieldnames = ['inn', 'name', 'revenue', 'site', 'source', 'cat_evidence', 'cat_product', 'employees', 'okved_main']
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(filtered_companies)

        print(f"Найдено {len(filtered_companies)} уникальных компаний.")
        print(f"Данные сохранены в файл: '{output_file}'")
        print("\nПервые 5 записей:")
        for i, company in enumerate(filtered_companies[:5]):
            print(f"   {i+1}. {company['name']} -> {company['cat_evidence']}")
    else:
        print("Компании не найдены.")
    pass

if __name__ == "__main__":
    main()
