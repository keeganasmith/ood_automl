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
        label_input.send_keys("target")

        train_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='train-path-input']"))
        )
        train_input.clear()
        train_input.send_keys("./sample_datasets/adult.tsv")

        start_button = wait.until(EC.element_to_be_clickable((By.ID, "startBtn")))

        start_time = time.perf_counter()
        start_button.click()

        wait_long = WebDriverWait(driver, 600)
        wait_long.until(
            lambda d: "finish" in d.find_element(By.ID, "log").text.lower()
        )
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        print(f"WEB_UI_TRAIN_TIME_SECONDS={elapsed}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
