import streamlit as st
import pandas as pd
import csv
import re
import os
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.summarize import load_summarize_chain
from langchain import PromptTemplate
from langchain.docstore.document import Document
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService



# Function to extract email addresses from text
def extract_emails_and_names(soup):
    emails = set()
    names = set()
    email_pattern = r'[\w\.-]+@[\w\.-]+'
    for string in soup.stripped_strings:
        for match in re.finditer(email_pattern, string):
            email = match.group()
            emails.add(email)
            names.add(email.split('@')[0])
    return list(emails), list(names)


def export_to_csv(details, base_url, existing_emails=set()):
    domain = urlparse(base_url).netloc
    csv_name = f'{domain}_emails.csv'
    file_exists = os.path.isfile(csv_name)
    with open(csv_name, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Company Name', 'URL', 'Email', 'First Name'])
        for detail in details:
            if detail[2] not in existing_emails:
                writer.writerow(detail)
                existing_emails.add(detail[2]) 


def get_domain(url):
    parsed_uri = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    return domain



def scrape_all_pages(base_url, visited_urls=set(), details=[]):
    if base_url in visited_urls:
        return
    service = Service("Email_extraction/chromedriver.exe")  # Update with the path to your chromedriver executable
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    # driver = webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install())
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(driver_version='123').install()))
    driver.get(base_url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    emails, names = extract_emails_and_names(soup)
    company_name = soup.title.string if soup.title else ''
    details.extend([(company_name, base_url, email, name) for email, name in zip(emails, names)])
    export_to_csv(details, base_url)
    print(f"Scraped {len(emails)} email addresses and names from {base_url}")
    visited_urls.add(base_url)
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('http') and get_domain(base_url) in href:
            scrape_all_pages(href, visited_urls, details)
    driver.quit()
    return details

def main():
    st.title("Email Address Extractor")

    # Input URL
    url = st.text_input("Enter the URL here 👇")

    if st.button("Extract Emails"):
        # Extract emails from URL
        emails = scrape_all_pages(url)
        df = pd.DataFrame(emails)

        # Display tabular data
        st.subheader("Email Addresses Extracted")
        st.table(df)

        # Combine email addresses
        combined_emails = ', '.join([email for _, _, email, _ in emails])
        st.subheader("Combined Email Addresses")
        st.write(combined_emails)

        data = [(Document(page_content=combined_emails, metadata={"source":"file_path"}))]  
        print(data)


        GOOGLE_API_KEY="AIzaSyCruOjusCfgSYI7CMsr_7u_uFq8JMR9RtQ"

        model = ChatGoogleGenerativeAI(model="gemini-1.0-pro",google_api_key=GOOGLE_API_KEY,
                                    temperature=0.3,convert_system_message_to_human=True)

        map_prompt = """
        You are a email analysis Expert you have find the pattern from the different emails provided below and give the possible combination:

        "{text}"

        **Existing Email- 

        **Pattern-
            .Prefix - 
            .Suffix -
            .Domain -

        **Example with human names- 
        """
        map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])

        combine_prompt = """
        You are a email analysis Expert you have find the pattern from the different emails provided below and give the possible combination:

        "{text}"

        **Existing Email- 

        **Pattern-
            .Prefix - 
            .Suffix -
            .Domain -
             
        **Example with human names- 
        """

        combine_prompt_template = PromptTemplate(template=combine_prompt, input_variables=["text"])

        summary_chain = load_summarize_chain(llm=model,
                                     chain_type='map_reduce',
                                     map_prompt=map_prompt_template,
                                     combine_prompt=combine_prompt_template,
                                    )
        output = summary_chain.run(data)
        # print(output)
        st.subheader("Email Addresses Pattern")
        st.write(output)


if __name__ == "__main__":
    main()
