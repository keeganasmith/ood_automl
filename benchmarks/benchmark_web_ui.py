import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def main() -> None:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("http://localhost:8000")
        wait = WebDriverWait(driver, 30)

        label_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='label-input']"))
        )
        label_input.clear()
        label_input.send_keys("label")

        train_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='train-path-input']"))
        )
        train_input.clear()
        train_input.send_keys("/scratch/user/u.ks124812/datasets/human-face-emotions/2/Data/train.csv")

        data_type_select = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//label[normalize-space()='data_type']/following::div[contains(@class,'n-base-selection')][1]")
            )
        )
        data_type_select.click()
        multimodal_option = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'n-base-select-option')][.//div[normalize-space()='multi-modal']]")
            )
        )
        multimodal_option.click()

        enable_gpu_checkbox = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//label[contains(@class,'n-checkbox')][.//span[normalize-space()='Enable GPU']]")
            )
        )
        enable_gpu_checkbox.click()

        start_button = wait.until(EC.element_to_be_clickable((By.ID, "startBtn")))

        start_time = time.perf_counter()
        start_button.click()
        print("clicked start button")

        wait_long = WebDriverWait(driver, 60000)
        def wait_long_condition(driver):    
            if("[error]" in driver.find_element(By.ID, "log").text.lower()):
                print("error: ")
                print(driver.find_element(By.ID, "log").text)
                return True
        
            return ("finish" in driver.find_element(By.ID, "log").text.lower())
        wait_long.until(
            wait_long_condition
        )
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        print(f"WEB_UI_TRAIN_TIME_SECONDS={elapsed}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
