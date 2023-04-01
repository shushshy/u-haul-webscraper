import os
import csv
import time
import pandas as pd
from pathlib import Path
from loguru import logger
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
# from S02_download_files_in_folder_uhaul import prepare_folder_for_download
from selenium.webdriver.chrome.options import Options
from datetime import datetime


def prepare_folder_for_download(download_folder_path: Path) -> Path:
    """
    The function will take a path to the general download folder, and it will create folder with specific
    date when pricing data will be downloaded

    :param download_folder_path: path to general folder where all other folders for download will be created
    :return: Path to created folder for certain date
    """
    new_folder_name = datetime.now().strftime("%Y-%m-%d")

    download_folder_path = Path.joinpath(download_folder_path) / new_folder_name
    try:
        download_folder_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        logger.warning("Folder is already there")
    else:
        logger.info("Folder was created")

    return download_folder_path


def extract_data_from_pages(folder_name_pth: Path) -> csv:
    logger.info('Extracting data started ...')

    file_headers = ['brand_name', 'name', 'street', 'locality', 'region', 'postal_code', 'FormattedAddress',
                    'hasPricing','size', 'description',
                    'price', 'sale_price', 'promotion', 'url', 'location_external_id', 'latitude',
                    'longitude', 'collection_date']

    header_added = False

    for downloaded_page in folder_name_pth.iterdir():
        if downloaded_page.is_file():
            try:
                html_page = BeautifulSoup(open(downloaded_page, 'r', encoding="utf8"), features="html.parser")
                if '/Results/' in html_page.select("[rel='canonical']")[0]['href'] or\
                        '/Error/' in html_page.select("[rel='canonical']")[0]['href']:
                    continue
            except Exception as e:
                print(e)
                continue
        else:
            logger.warning(f'Cannot open page {downloaded_page}')

        location_details = get_location_data(html_page)

        units = html_page.find_all('div',
                                   class_="grid-x grid-margin-x align-left medium-grid-expand-x large-align-middle")
        if len(units) == 0:
            # units = []
            units.append(False)
            facility_has_pricing = False
        else:
            facility_has_pricing = True

        for storage_unit in units:
            if check_if_unit_valid(storage_unit) or facility_has_pricing is False:
                if facility_has_pricing is False:
                    pricing = [False,'','','','','']
                    facility_row = location_details + pricing
                else:
                    unit_info = get_pricing_data(storage_unit)
                    facility_row = location_details + unit_info

                try:
                    url = html_page.select("[rel='canonical']")[0]['href']
                    facility_row.append(url)

                    location_external_id = "uh" + url.split("/")[-2]
                    facility_row.append(location_external_id)
                except Exception as e:
                    logger.error(e)

                lat, lon = get_lat_lon(' '.join(facility_row[1:5]))
                facility_row.append(lat)
                facility_row.append(lon)

                collection_date = downloaded_page.parent.name
                facility_row.append(collection_date)

                uh_csv_path = Path(f'/mnt/disk/5-major-brands-extracted-data/Pricing_Uhaul_storage/'
                                   f'uh_extracted_data/Uhaul_{downloaded_page.parent.name}.csv')

                if not header_added:
                    all_data = pd.DataFrame(facility_row).T
                    all_data.to_csv(uh_csv_path, mode='a', header=file_headers,
                                    index=False)
                    header_added = True
                else:
                    all_data = pd.DataFrame(facility_row).T
                    all_data.to_csv(uh_csv_path, mode='a', header=False, index=False)

    logger.info('Extracting completed!')


def get_location_data(webpage) -> list:
    storage_data = []
    # scraping facility's name
    # if facility is u-haul's affiliate, its name is formatted differently from other facilities,
    # so the code first checks if there exists name formatted like that
    brand_name = 'U-Haul'
    storage_data.append(brand_name)

    try:
        # TODO: find a way to not use driver, try through find "uhaul affiliate"
        if webpage.find('svg').select("[aria-label='U-Haul Affiliate']") is not None:
            name_ = webpage.find('h1', class_="collapse").text.split("24/7")[0].strip().replace("\n", "").replace(
                "\u2009", "")
            storage_data.append(name_)

        else:
            name_ = webpage.find('h2', class_="collapse-half text-dull text-xl text-semibold").text.strip()
            storage_data.append(name_)

    except (AttributeError, IndexError):
        storage_data.append('')

    try:
        street = webpage.find('address').text.split("(")[0].split("\n")[1].replace("  ", "").strip(",").strip(
            "\u2009")
        storage_data.append(street)
    except (AttributeError, IndexError):
        storage_data.append('')

    try:
        locality = webpage.find('address').text.split("(")[0].split("\n")[2].replace("  ", "").strip(",").strip(
            "\u2009")
        storage_data.append(locality)
    except (AttributeError, IndexError):
        storage_data.append('')

    try:
        region = webpage.find('address').text.split("(")[0].split("\n")[3].replace("  ", "").strip(",").strip(
            "\u2009")
        storage_data.append(region)
    except (AttributeError, IndexError):
        storage_data.append('')

    try:
        postal_code = webpage.find('address').text.split("(")[0].split("\n")[4].replace("  ", "").strip(",").strip(
            "\u2009")
        storage_data.append(postal_code)
    except (AttributeError, IndexError):
        storage_data.append('')

    full_address = ', '.join(storage_data[2:5]) + ' ' + ''.join(storage_data[5]) + " USA"
    storage_data.append(full_address)

    return storage_data


def check_if_unit_valid(unit_soup) -> bool:
    try:
        description = unit_soup.find('p').text
    except (AttributeError, IndexError):
        return False

    words_to_exclude = ["RV/Boat", "Lockers", "Office", "Wine", "Warehouse"]
    if not any(word in description for word in words_to_exclude):
        return True
    else:
        return False


def get_pricing_data(unit) -> list:
    pricing_info = []

    has_pricing = True
    pricing_info.append(has_pricing)

    try:
        size = unit.find('h4').text.split(" | ")[-1].replace(" ", "").strip()
        pricing_info.append(size)
    except (AttributeError, IndexError):
        pricing_info.append('')

    # formatting unit description to get rid of weird blank spaces
    try:
        description = unit.find('p').text
        split_ = description.split()
        description = ' '.join(split_)
        pricing_info.append(description)
    except (AttributeError, IndexError):
        pricing_info.append('')

    try:
        price = unit.find('b', class_="text-lg").text.strip().replace("$", "")
        pricing_info.append(price)
    except (AttributeError, IndexError):
        pricing_info.append('')

    # sale_price and promotion variables don't exist for u-haul, so '' is appended twice
    pricing_info.append('')
    pricing_info.append('')
    return pricing_info


def get_lat_lon(address):
    """
    Function will take storage name and storage address, and it will get accurate latitude and longitude for
    forwarded facility
    :param address: Storage address
    :return: Accurate latitude and Longitude for certain facility
    """

    os.environ['WDM_LOG'] = '0'
    options = Options()
    options.headless = True
    web_driver = webdriver.Chrome(service=Service(r"/home/data/PythonProject/scrape-scripts/chromedriver_linux64/"
                                                  r"chromedriver"), options=options)
    try:
        try:
            web_driver.get('https://developers-dot-devsite-v2-prod.appspot.com/maps/documentation/utils/geocoder')
        except (TimeoutException, WebDriverException):
            time.sleep(5)
            web_driver.get('https://developers-dot-devsite-v2-prod.appspot.com/maps/documentation/utils/geocoder')

        time.sleep(3)

        search_bar = web_driver.find_element(By.XPATH,  "/html/body/div[2]/div/div/div[7]/div/div/input[1]")
        search_bar.clear()
        search_bar.send_keys(address, Keys.ENTER)
        time.sleep(3)

        first_element = web_driver.find_element(By.XPATH,
                                                "/html/body/div[2]/div/div/div[12]/div/div/div[2]/div"
                                                "/div/table/tbody/tr/td[2]/p[3]").text.split(',')
        lat = first_element[0].split(':')[1]
        lon = first_element[1].split(' ')[0]
        web_driver.quit()
        return lat, lon

    except (IndexError, NoSuchElementException, WebDriverException):
        lat = ""
        lon = ""
        web_driver.quit()
        return lat, lon


if __name__ == '__main__':

    path = Path(r'/mnt/disk/5-major-brands-extracted-data/Pricing_Uhaul_storage/uh_downloaded_data')
    folder_name_path = prepare_folder_for_download(path)
    extract_data_from_pages(folder_name_path)
    # extract_data_from_pages(Path(r'/mnt/disk/5-major-brands-extracted-data/Pricing_Uhaul_storage/'
    #                              r'uh_downloaded_data/2022-08-31'))
