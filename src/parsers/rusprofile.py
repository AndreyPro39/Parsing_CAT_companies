import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, Optional, List
from urllib.parse import quote_plus


class RusprofileParser:
    """
    Парсер для получения информации о компаниях с Rusprofile.ru
    """
    
    SEARCH_URL = "https://www.rusprofile.ru/search"
    BASE_URL = "https://www.rusprofile.ru"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_inn_by_name(self, company_name: str) -> Optional[Dict]:
        """
        Ищет компанию по названию и возвращает первую найденную с ИНН
        
        Args:
            company_name: Название компании для поиска
            
        Returns:
            Словарь с информацией о компании или None, если не найдена
        """
        print(f"  Поиск ИНН для: '{company_name}'")
        
        # Кодируем название для URL
        encoded_name = quote_plus(company_name)
        search_url = f"{self.SEARCH_URL}?query={encoded_name}&type=ul"
        
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем первую карточку компании в результатах поиска
            company_card = soup.find('div', class_='company-item')
            
            if not company_card:
                # Пробуем другие возможные селекторы
                company_card = soup.find('div', class_=re.compile(r'company-item'))
            
            if not company_card:
                print(f"    Компания '{company_name}' не найдена в результатах поиска")
                return None
            
            # Извлекаем название компании
            name_element = company_card.find('a', class_='company-name')
            company_name_found = name_element.get_text(strip=True) if name_element else company_name
            
            # Извлекаем ИНН
            inn_element = company_card.find('span', class_='copy-target')
            if not inn_element:
                # Пробуем другой селектор для ИНН
                inn_text = None
                for div in company_card.find_all('div', class_='company-row'):
                    text = div.get_text(strip=True)
                    if 'ИНН' in text:
                        inn_text = text
                        break
                
                if inn_text:
                    # Извлекаем ИНН из текста
                    inn_match = re.search(r'ИНН\s*(\d{10,12})', inn_text)
                    inn = inn_match.group(1) if inn_match else None
                else:
                    inn = None
            else:
                inn = inn_element.get_text(strip=True)
            
            if not inn or not inn.isdigit():
                print(f"    Не удалось извлечь ИНН для '{company_name_found}'")
                return None
            
            # Извлекаем ссылку на страницу компании
            link_element = company_card.find('a', class_='company-name')
            company_url = f"{self.BASE_URL}{link_element['href']}" if link_element and 'href' in link_element.attrs else None
            
            print(f"    Найдено: {company_name_found} (ИНН: {inn})")
            
            return {
                'name': company_name_found,
                'inn': inn,
                'rusprofile_url': company_url,
                'source_query': company_name
            }
            
        except requests.exceptions.RequestException as e:
            print(f"    Ошибка сети при поиске '{company_name}': {e}")
            return None
        except Exception as e:
            print(f"    Ошибка при обработке результатов поиска для '{company_name}': {e}")
            return None
        finally:
            # Уважаем сайт - делаем паузу между запросами
            time.sleep(1)
    
    def get_company_info(self, inn: str) -> Optional[Dict]:
        """
        Получает подробную информацию о компании по ИНН
        
        Args:
            inn: ИНН компании (10 или 12 цифр)
            
        Returns:
            Словарь с информацией о компании или None в случае ошибки
        """
        print(f"  Получение информации по ИНН: {inn}")
        
        if not inn or not re.match(r'^\d{10,12}$', inn):
            print(f"    Неверный формат ИНН: {inn}")
            return None
        
        company_url = f"{self.BASE_URL}/ajax/query"
        
        try:
            # Отправляем POST-запрос для получения данных
            payload = {
                'query': inn,
                'action': 'search',
                'type': 'ul',
                'with_aliases': '1'
            }
            
            response = self.session.post(company_url, data=payload, timeout=10)
            response.raise_for_status()
            
            # Парсим JSON ответ
            data = response.json()
            
            if data.get('success') and data.get('ul_count') > 0:
                company_data = data['ul_list'][0]
                
                # Извлекаем основную информацию
                result = {
                    'inn': inn,
                    'name': company_data.get('name', ''),
                    'full_name': company_data.get('full_name', ''),
                    'ogrn': company_data.get('ogrn', ''),
                    'okved': company_data.get('okved', ''),
                    'okved_main': company_data.get('okved_main', ''),
                    'status': company_data.get('status', ''),
                    'registration_date': company_data.get('registration_date', ''),
                    'authorized_capital': self._parse_money(company_data.get('authorized_capital', '')),
                    'revenue': self._parse_money(company_data.get('revenue', '')),
                    'profit': self._parse_money(company_data.get('profit', '')),
                    'employees': company_data.get('employees_count', ''),
                    'site': company_data.get('site', ''),
                    'email': company_data.get('email', ''),
                    'phone': company_data.get('phone', ''),
                    'address': company_data.get('address', ''),
                    'ceo': company_data.get('ceo_name', ''),
                    'source': 'rusprofile.ru'
                }
                
                print(f"    Получена информация для {result['name']}")
                return result
            
            print(f"    Компания с ИНН {inn} не найдена")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"    Ошибка сети при получении информации по ИНН {inn}: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            print(f"    Ошибка парсинга данных для ИНН {inn}: {e}")
            return None
        except Exception as e:
            print(f"    Неожиданная ошибка для ИНН {inn}: {e}")
            return None
        finally:
            time.sleep(1)
    
    def _parse_money(self, value: str) -> float:
        """
        Преобразует строковое значение денег в число
        
        Args:
            value: Строка вида "1 234 567 ₽" или "12.34 млн ₽"
            
        Returns:
            Числовое значение в рублях
        """
        if not value:
            return 0.0
        
        try:
            # Убираем пробелы и символ валюты
            clean_value = value.replace(' ', '').replace('₽', '').replace(',', '.')
            
            # Проверяем наличие "млн", "тыс" и т.д.
            if 'млн' in clean_value:
                number = float(re.search(r'[\d.]+', clean_value).group())
                return number * 1_000_000
            elif 'тыс' in clean_value:
                number = float(re.search(r'[\d.]+', clean_value).group())
                return number * 1_000
            else:
                return float(re.search(r'[\d.]+', clean_value).group())
        except:
            return 0.0
    
    def search_multiple_companies(self, company_names: List[str]) -> List[Dict]:
        """
        Ищет несколько компаний по названиям
        
        Args:
            company_names: Список названий компаний
            
        Returns:
            Список найденных компаний с ИНН
        """
        results = []
        
        for name in company_names:
            company_info = self.search_inn_by_name(name)
            if company_info:
                results.append(company_info)
        
        return results


# Пример использования
if __name__ == "__main__":
    parser = RusprofileParser()
    
    # Тестируем поиск по названию
    test_companies = ["Яндекс", "Сбербанк", "Газпром"]
    
    print("Тестирование поиска компаний по названиям:")
    for company in test_companies:
        result = parser.search_inn_by_name(company)
        if result:
            print(f"  Найдено: {result['name']} (ИНН: {result['inn']})")
            
            # Получаем полную информацию
            full_info = parser.get_company_info(result['inn'])
            if full_info:
                print(f"    Выручка: {full_info.get('revenue', 'не указана')}")
                print(f"    Сотрудники: {full_info.get('employees', 'не указано')}")
                print(f"    ОКВЭД: {full_info.get('okved_main', 'не указан')}")
        else:
            print(f"  Не найдено: {company}")
