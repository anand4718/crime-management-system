import requests
from bs4 import BeautifulSoup

NEWS_URL = "https://www.indiatoday.in/crime"

def fetch_crime_news():
    news_list = []
    try:
        response = requests.get(NEWS_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('div', class_='B1S3_content__wrap__9mSB6', limit=5)

        for article in articles:
            title_element = article.find('h2')
            link_element = article.find('a')
            if title_element and link_element and link_element.has_attr('href'):
                title = title_element.get_text(strip=True)
                link = "https://www.indiatoday.in" + link_element['href']
                news_list.append({'title': title, 'link': link})
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
    return news_list