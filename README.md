# U-Haul webscraper

Webscrapers are used for collecting the data from a website. This web scraper collects the data from [U-Haul's website](https://www.uhaul.com/Storage/). U-Haul is one of the major self-storage chains in the US. Scraped data includes information about self-storage facilities in the US and information about units at each facility. The final result will be a csv file with extracted data, ready for furthermore processing and analysis.

## About the files

Script names start with S01,S02 and S03, to indicate the order of the scripts.
-S01_extract_facility_links.py searches for the facilities in the US cities, collects the links to individual facilities, and saves them to a file.
-S02_download_pages_from_links.py goes through the collected links saved in a file, and downloads each page.
-S03_extract_data_from_downloaded_pages goes through the downloaded pages, extracts useful data and saves it to a csv file.

-all_states.xlsx file contains list of all major cities in the US, and the scraper goes through that list while searching
for storage facilities.

## Prerequisites
To successfully run the script, use vpn with location in the US, since the script accesses the US U-Haul website. Any vpn will do, for this project [Proton VPN](https://protonvpn.com/) worked just fine. Choose any of the US servers available.

Python version 3.8.8

## Running the script
1. Clone the repository to your local machine
2. Create a virtual environment.
3. Install requirements.
4. Run the S01_extract_facility_links.py script.
This script takes about 24 hours to finish collecting the links. After finishing, each script automatically runs the script after it. S02 takes about 24 hours to finish, as well as the S03.

