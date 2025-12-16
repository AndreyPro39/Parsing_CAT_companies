import sys
import os
import re
import time
import csv
import requests
from typing import List, Dict
from bs4 import BeautifulSoup

# Добавляем папку проекта в путь поиска
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем парсеры
try:
    from superjob_parser import SuperJobParser
    from rusprofile_parser import RusprofileParser
    print("✅ Модули загружены")
except ImportError as e:
    print(f"❌ Ошибка: {e}")
    print("Убедитесь, что superjob_parser.py и rusprofile_parser.py в той же папке")
    sys.exit(1)

def main():
    # Ключевые слова для CAT-систем и локализации
    cat_keywords = [
        "Trados", "memoQ", "Smartcat", "Crowdin", "Phrase",
        "translation memory", "память переводов", "CAT tool",
        "локализация", "переводчик", "технический писатель", "Technical Writer"
    ]

    # Инициализируем парсеры
    superjob_parser = SuperJobParser()
    rusprofile_parser = RusprofileParser()
    
    print("Начинаем парсинг SuperJob.ru...")
    found_companies = superjob_parser.search_companies_by_keywords(cat_keywords, max_results=30)
    
    print(f"Найдено {len(found_companies)} компаний на SuperJob")
    
    # Дополнительная обработка: попробуем найти ИНН через названия компаний
    filtered_companies = []
    
    for company in found_companies:
        # Попробуем найти компанию на rusprofile по названию
        company_name = company.get('name', '')
        print(f"Поиск ИНН для компании: {company_name}")
        
        try:
            # Предполагаем, что RusprofileParser имеет метод search_inn_by_name
            # Если такого метода нет, вам нужно будет его добавить
            inn_info = rusprofile_parser.search_inn_by_name(company_name)
            
            if inn_info and 'inn' in inn_info:
                company['inn'] = inn_info['inn']
                
                # Получаем финансовую информацию по ИНН
                financials = rusprofile_parser.get_company_info(inn_info['inn'])
                
                # Проверяем выручку (если доступна)
                revenue = financials.get('revenue', 0) if financials else 0
                
                # Фильтруем по выручке (100 млн рублей)
                if revenue >= 100_000_000:
                    company.update(financials or {})
                    filtered_companies.append(company)
                else:
                    print(f"  Пропускаем: выручка {revenue} < 100 млн")
            else:
                print(f"  ИНН не найден для {company_name}")
                
        except Exception as e:
            print(f"  Ошибка при обработке {company_name}: {e}")
            continue
    
    print(f"После фильтрации по выручке: {len(filtered_companies)} компаний")
    
    # Сохраняем в CSV
    if filtered_companies:
        output_file = 'superjob_companies.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            # Определяем все возможные поля
            all_keys = set()
            for company in filtered_companies:
                all_keys.update(company.keys())
            
            fieldnames = ['inn', 'name', 'revenue', 'site', 'source', 'cat_evidence', 
                         'cat_product', 'employees', 'okved_main']
            # Добавляем остальные поля
            for key in sorted(all_keys):
                if key not in fieldnames:
                    fieldnames.append(key)
            
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(filtered_companies)

        print(f"✅ Найдено {len(filtered_companies)} уникальных компаний.")
        print(f"📁 Данные сохранены в файл: '{output_file}'")
        print("\nПервые 5 записей:")
        for i, company in enumerate(filtered_companies[:5]):
            revenue = company.get('revenue', 'не указана')
            inn = company.get('inn', 'не найден')
            print(f"   {i+1}. {company['name']} (ИНН: {inn}, Выручка: {revenue})")
    else:
        print("❌ Компании не найдены после фильтрации.")

if __name__ == "__main__":
    main()
