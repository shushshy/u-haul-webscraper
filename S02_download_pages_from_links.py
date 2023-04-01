import csv
import time
import requests
import os.path
# import pandas as pd
# from pandas.errors import EmptyDataError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from loguru import logger
from datetime import datetime
from requests.exceptions import MissingSchema, ConnectionError
import S03_extract_data_from_pages_uhaul


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


def download_pages(folder_name_for_saving_links: Path, links_file_path):
    logger.info('Start downloading pages.')

    failed_links_file = Path('failed_links.csv')

    with open(links_file_path, 'r', newline='') as fu:
        reader = csv.reader(fu)
        page_urls = []
        for row in reader:
            # page_urls.append(str(row).strip("[").strip("]").strip("'"))
            page_urls.append(row)

    links = sorted(page_urls)

    for link in links:
        link = ''.join(str(e) for e in link)
        folder_path = f"{folder_name_for_saving_links}/"
        file_path = folder_path + link.split("/")[4] + "_" + link.split("/")[5] + ".html"
        if (os.path.exists(file_path)) is False:
            try:
                if '/Self' in link:
                    link = "https://www.uhaul.com/Locations/Self" + \
                           link.strip('"').strip("[").strip("]").split("/Self")[1]
                    time.sleep(2.5)
                    session = requests.Session()
                    retry = Retry(connect=3, backoff_factor=0.5)
                    adapter = HTTPAdapter(max_retries=retry)
                    session.mount('http://', adapter)
                    session.mount('https://', adapter)
                    result = session.get(link)
                    if result:
                        file_name = link.split('/')[-3] + '_' + link.split('/')[-2] + '.html'
                        with open(Path.joinpath(folder_name_for_saving_links) / file_name, 'w', encoding='utf-8') as fi:
                            fi.write(result.text)

                        # lines = open(links_file_path).readlines()
                        # open(links_file_path, 'w').writelines(lines[1:])

                else:
                    logger.info("Following link is invalid and wasn't downloaded: " + link)
                    with open(failed_links_file, 'a+', encoding='UTF8', newline='') as file_:
                        csv_writer = csv.writer(file_)
                        csv_writer.writerow([link])
            except (MissingSchema, ConnectionError):
                with open(failed_links_file, 'a+', encoding='UTF8', newline='') as file_:
                    csv_writer = csv.writer(file_)
                    csv_writer.writerow([link])


def return_last_file_in_folder(full_folder_path):
    files = os.listdir(full_folder_path)
    paths = [os.path.join(full_folder_path, file_name) for file_name in files]
    return max(paths, key=os.path.getctime)


if __name__ == '__main__':
    path = Path(r'/mnt/disk/5-major-brands-extracted-data/Pricing_Uhaul_storage/uh_downloaded_data')
    folder_name_with_date = prepare_folder_for_download(path)
    # folder_name_with_date = Path(r'/mnt/disk/5-major-brands-extracted-data/Pricing_Uhaul_storage/'
    #                              r'uh_downloaded_data/2022-11-27')

    links_file = return_last_file_in_folder(r'/home/data/PythonProject/u-haul-scrape/scraped links')
    download_pages(folder_name_with_date, links_file)
    logger.info('Download complete!')

    S03_extract_data_from_pages_uhaul.extract_data_from_pages(folder_name_with_date)

