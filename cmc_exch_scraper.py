import sys, pytz, logging, time, csv
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(filename='logfile.log',
                    level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

def setup_driver():
    try:
        chrome_option= webdriver.ChromeOptions()
        chrome_option.add_argument("--headless")
        chrome_option.add_argument("--disable-gpu")
        chrome_option.add_argument("--no-sandbox")
        chrome_option.add_argument("--disable-infobars")
        chrome_option.add_argument("--disable-dev-shm-usage")
        chrome_option.add_argument("enable-automation")

        return webdriver.Chrome(options=chrome_option)

    except Exception as error_message:
        logging.error(f"Error occured while running setup_driver function: \n{error_message}")  
        sys.exit()

def ETL(formatted_timestamp):
    try:
        driver = setup_driver()
        driver.get('https://coinmarketcap.com/rankings/exchanges/')
        driver.implicitly_wait(10)
        driver.execute_script("arguments[0].click();", 
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="__next"]/div/div[1]/div[2]/div/div/div[3]/button')
            )))
        driver.implicitly_wait(10)
        time.sleep(2)

        Screen_height = driver.execute_script("return window.screen.height;")
        driver.implicitly_wait(60)

        ScrollNumber = 1
        Scroll_wait = 1

        while True:
            driver.execute_script(f"window.scrollTo(0,{Screen_height*ScrollNumber})")
            ScrollNumber += 1

            time.sleep(Scroll_wait)

            Scroll_height = driver.execute_script("return document.body.scrollHeight;")
            result = driver.find_element(
                By.XPATH,
                '//*[@id="__next"]/div/div[1]/div[2]/div/div/div[2]/table/tbody'
            )
            page_date   = result.get_attribute("innerHTML")
            soup        = BeautifulSoup(page_date, 'lxml')

            if (Screen_height) * ScrollNumber > Scroll_height:
                driver.quit()
                break

        data = soup.find_all("tr")
        with open (f'data/exchanges_information_{formatted_timestamp}.csv','w',newline='') as outfile:
            csv_writer = csv.writer(outfile)
            csv_writer.writerow(['Exchange Name', 'Trade Volume 24H', 'Average Liquidity',
                                    'Weekly Visit','Num of Markets','Num of Coins'])
            for _, content in enumerate(data):
                td  = content.find_all("td")
                try:
                    volume_24h  = td[2].contents[0].strip()
                except:
                    volume_24h  = ''
                weekly_visits   = td[4].text
                name            = td[1].text
                cmc_link: str   = td[1].find("a", class_="cmc-link")["href"]
                avg_liquidity   = td[3].text
                num_markets     = td[5].text
                num_coins       = td[6].text
                
                scr_result = {}
                try:
                    scr_result = {
                        "name": name,
                        "tradevol_24h":int(volume_24h[1:].replace(',','')),
                        "avg_liquidity": int(avg_liquidity) if avg_liquidity != "--" else "",
                        "weekly_visits":int(weekly_visits.replace(',','')),
                        "num_markets":int(num_markets),
                        "num_coins":int(num_coins),
                        "url":'https://coinmarketcap.com' + cmc_link,
                    }
                except:
                    try:
                        scr_result = {
                        "name": name,
                        "tradevol_24h":None,
                        "avg_liquidity": int(avg_liquidity) if avg_liquidity != "--" else "" ,
                        "weekly_visits":int(weekly_visits.replace(',','')),
                        "num_markets":int(num_markets),
                        "num_coins":int(num_coins),
                        "url":'https://coinmarketcap.com' + cmc_link,
                    }
                    except:
                        scr_result = {
                        "name": name,
                        "tradevol_24h":None,
                        "avg_liquidity": int(avg_liquidity) if avg_liquidity != "--" else "" ,
                        "weekly_visits":None,
                        "num_markets":int(num_markets),
                        "num_coins":int(num_coins),
                        "url":'https://coinmarketcap.com' + cmc_link,
                    }
                csv_writer.writerow([
                    scr_result['name'],
                    scr_result['tradevol_24h'],
                    scr_result['avg_liquidity'],
                    scr_result['weekly_visits'],
                    scr_result['num_markets'],
                    scr_result['num_coins'],
                    scr_result['url']
                ])

        return None

    except Exception as error_message:
        logging.error(f"Error occured while running ETL function: \n{error_message}")
        sys.exit()

def retry_job_with_timeout(formatted_timestamp, max_attempts = 3, delay_seconds=15):
    attempts = 0

    while attempts < max_attempts:
        try:
            ETL(formatted_timestamp)
            logging.info(f"Job completed successfully in {attempts+1} try")
            return None

        except TimeoutException as e:
            attempts +=1
            logging.info(f"Attemp {attempts} failed with TimeoutError: {e}")
            if attempts < max_attempts:
                logging.info(f"Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            else:
                logging.info("Maximum attempts reached. Exiting.")
                raise

if __name__ == '__main__':
    logging.info(f"Scraping Data From CMC Starting")

    now                     = datetime.now(tz=pytz.timezone('Asia/Jakarta'))
    now_with_seconds_zero   = now.replace(second=0)
    formatted_timestamp     = now_with_seconds_zero.strftime("%Y-%m-%d")

    retry_job_with_timeout(formatted_timestamp)
    