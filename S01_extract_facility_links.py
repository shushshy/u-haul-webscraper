import os
import csv
import time
import pandas as pd
from pathlib import Path
from loguru import logger
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
import S02_download_files_in_folder_uhaul
from S02_download_files_in_folder_uhaul import prepare_folder_for_download
import S03_extract_data_from_pages_uhaul


# (re)opens uhaul website
def open_website_for_search():
    url_ = 'https://www.uhaul.com/Storage/WY/Results/'
    driver.get(url_)


# searches for the selected city
def city_search(city):
    # checks if there is a search form on the page, in some circumstances due to previous city malfunction there
    # won't be a search form, so this covers that case to prevent code from looping through cities without
    # scraping any data

    if driver.find_elements(By.XPATH, '//*[@id="locationSearchForm"]/div[2]/div[2]/button'):
        driver.find_element(By.XPATH, '//*[@id="movingFromInput"]').clear()
        driver.find_element(By.XPATH, '//*[@id="movingFromInput"]').send_keys(city)
        driver.find_element(By.XPATH, '//*[@id="locationSearchForm"]/div[2]/div[2]/button').click()

        # in case there isn't an exact match to city+state code, it will move on to the next city
        if (driver.find_elements(By.XPATH, '//*[@id="locationAmbigAddresses"]/p')
                or driver.find_elements(By.XPATH, '//*[@id="locationSearchForm"]/fieldset/div/div[1]/ul/li')
                or driver.find_elements(By.XPATH, '//*[@id="mainRow"]/div/div/div/div[1]/div[1]/h1')
                or driver.find_elements(By.XPATH, '//*[@id="locationsResults"]/div/p')):
            #//*[@id="locationsResults"]/div/p
            #/html/body/main/div/div/div/div[1]/div[2]/div[2]/div/p
            open_website_for_search()
        else:
            # if the search is successful, code loops through results page
            loop_through_results_page()

    # in case of malfunction, sets up the page with valid search form for next city
    else:
        open_website_for_search()


# goes through 4 pages of results
def loop_through_results_page():
    time.sleep(2)
    try:
        extract_links()

        # moving to the next 6 results
        # for some cities there is less than 4 pages, so the function checks if there is "more locations" button
        if driver.find_element(By.XPATH, '//*[@id="locationsResults"]/ul[2]/li/a[2]') is not None:
            driver.find_element(By.XPATH, '//*[@id="locationsResults"]/ul[2]/li/a[2]').click()
            extract_links()

            if driver.find_element(By.XPATH, '//*[@id="locationsResults"]/ul[2]/li[2]/a[2]') is not None:
                driver.find_element(By.XPATH, '//*[@id="locationsResults"]/ul[2]/li[2]/a[2]').click()
                extract_links()

                if driver.find_element(By.XPATH, '//*[@id="locationsResults"]/ul[2]/li[2]/a[2]') is not None:
                    driver.find_element(By.XPATH, '//*[@id="locationsResults"]/ul[2]/li[2]/a[2]').click()
                    extract_links()

    except NoSuchElementException:
        pass


# extract links for facilities from results page
def extract_links():

    content = driver.page_source
    soup = BeautifulSoup(content, 'lxml')
    link_elements = soup.find_all("a", class_="button collapse")

    list_of_links = []
    for link in link_elements:
        list_of_links.append(link['href'])

    file_with_all_links = Path(f'scraped links/all_links_{todays_date}.csv')
    if not os.path.exists(file_with_all_links):
        open(file_with_all_links, "w").close()

    unique_facility_urls = open(file_with_all_links, 'r').read()
    with open(file_with_all_links, 'a+', encoding='UTF8', newline='') as file1:
        for facility_url in list_of_links:
            if facility_url not in unique_facility_urls:
                file_writer = csv.writer(file1)
                file_writer.writerow([facility_url])
                print('success')



if __name__ == '__main__':
    # creating new folderfor the downloads with todays date
    path = Path(r'/mnt/disk/5-major-brands-extracted-data/Pricing_Uhaul_storage/uh_downloaded_data')
    folder_name_with_date = prepare_folder_for_download(path)
    todays_date = folder_name_with_date.name.split('/')[-1]

    unique_facilities_urls = []

    os.environ['WDM_LOG'] = '0'
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    # links extraction
    logger.info('Link extraction started!')
    open_website_for_search()
    cities_file = Path(r'all_states.xlsx')
    cities_US = pd.read_excel(cities_file)
    search_entry = cities_US['city'] + " " + cities_US['state_code']
    search_entry.apply(city_search)
    logger.info('Link extraction complete.')
    driver.quit()

    # downloading pages from links
    links_file = S02_download_files_in_folder_uhaul.return_last_file_in_folder(r'/home/data/PythonProject/u-haul-scrape/scraped links')
    S02_download_files_in_folder_uhaul.download_pages(folder_name_with_date, links_file)
    logger.info('Download complete!')

    # extracting pricing info from downloaded pages
    S03_extract_data_from_pages_uhaul.extract_data_from_pages(folder_name_with_date)
