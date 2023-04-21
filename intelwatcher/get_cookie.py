import sys
import os
import time
import glob


def _write_cookie(log, cookies):
    final_cookie = ''.join("{}={}; ".format(k, v) for k, v in cookies.items())
    with open('cookie.txt', encoding='utf-8', mode='w') as cookie:
        log.info('Write cookie to cookie.txt...')
        cookie.write(final_cookie)

    log.info("Your cookie:")
    log.info(final_cookie)

    return final_cookie


def mechanize_cookie(config, log):
    """Returns a new Intel Ingress cookie via mechanize."""
    import mechanize

    log.info("Logging into Facebook using mechanize")
    browser = mechanize.Browser()

    if log.level <= 10:
        browser.set_debug_http(True)
        browser.set_debug_responses(True)
        browser.set_debug_redirects(True)

    browser.set_handle_robots(False)
    cookies = mechanize.CookieJar()
    browser.set_cookiejar(cookies)
    browser.addheaders = [
        ('User-agent',
         'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.102 Safari/537.36')
    ]
    browser.set_handle_refresh(False)
    log.info("Everything set - Let's go")

    url = ('https://www.facebook.com/v3.2/dialog/'
           'oauth?client_id=449856365443419&redirect_uri=https%3A%2F%2Fintel.ingress.com%2F')
    browser.open(url)
    log.info("Opened Facebook Login Page")
    log.debug(browser.geturl())

    # sometimes you have to fill in the form multiple times for whatever reason
    tries = 0
    while "https://intel.ingress.com/" not in browser.geturl() and tries < 5:
        tries += 1
        log.info(f"Trying to log into Intel: Attempt {tries}/5")
        try:
            browser.select_form(nr=0)
        except:
            pass
        try:
            browser.form['email'] = config.ingress_user
            browser.form['pass'] = config.ingress_password
        except:
            try:
                form = browser.global_form()
                control = form.find_control(name="submit[Yes]")
                test = control._click()
                #print(test)
                #test = browser.click(name="submit[Yes]", kind=None)
                #print(test)
            except Exception as e:
                log.exception(e)
        response = browser.submit()
        time.sleep(2)
        log.debug(browser.geturl())

    if "https://intel.ingress.com/" in response.geturl() and response.getcode() == 200:
        log.info("Got through. Now getting that cookie")
        log.debug(browser.geturl())

        # this is magic
        req = mechanize.Request(browser.geturl())
        cookie_list = browser._ua_handlers['_cookies'].cookiejar.make_cookies(response, req)

        final_cookie = _write_cookie(log, {c.name: c.value for c in cookie_list})
        return final_cookie
    else:
        log.info(browser.geturl())
        raise Exception("Failed to log into Intel")


def selenium_cookie(config, log):
    """Returns a new Intel Ingress cookie via selenium webdriver."""
    from pathlib import Path
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.common.by import By

    def _save_screenshot_on_failure(filename):
        driver.save_screenshot('{}/{}'.format(str(debug_dir), filename))
        driver.quit()
        sys.exit(1)

    def _save_screenshot(filename):
        driver.save_screenshot('{}/{}'.format(str(debug_dir), filename))

    debug_dir = Path(__file__).resolve().parent.parent / 'debug'
    debug_dir.mkdir(exist_ok=True)

    # cleanup screenshots
    files = glob.glob('{}/*.png'.format(str(debug_dir)))
    for f in files:
        os.remove(f)

    user_agent = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'
                  ' Chrome/105.0.5195.102 Safari/537.36')

    profile = None
    if config.webdriver == 'firefox':
        options = webdriver.FirefoxOptions()

        if config.proxy_host:
            profile = webdriver.FirefoxProfile()
            profile.set_preference('network.proxy.type', 1)
            profile.set_preference('network.proxy.http', config.proxy_host)
            profile.set_preference('network.proxy.http_port', config.proxy_port)
            if config.proxy_username or config.proxy_password:
                profile.set_preference('network.proxy.user', config.proxy_username)
                profile.set_preference('network.proxy.password', config.proxy_password)
            profile.update_preferences()
    else:
        options = webdriver.ChromeOptions()
        # options.add_argument(f'user-agent={user_agent}')

    if config.headless_mode:
        options.add_argument('--headless')

    if config.webdriver == 'firefox':
        from webdriver_manager.firefox import GeckoDriverManager
        from selenium.webdriver.firefox.service import Service as FirefoxService

        options.add_argument('--new-instance')
        options.add_argument('--safe-mode')

        driver = webdriver.Firefox(
            service=FirefoxService(GeckoDriverManager().install()),
            options=options,
            firefox_profile=profile
        )
    else:
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')

        if config.webdriver == 'chromium':
            import undetected_chromedriver as uc

            from selenium.webdriver.chrome.service import Service as ChromiumService
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.utils import ChromeType

            driver = uc.Chrome(service=ChromiumService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()))
        else:
            import undetected_chromedriver as uc
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager

            driver = uc.Chrome(service=ChromeService(ChromeDriverManager().install()))

    if config.ingress_login_type == 'google':
        log.info('Login to Google via Stackoverflow')
        driver.get('https://stackoverflow.com/users/login?ssrc=head')

        try:
            driver.find_element(By.CSS_SELECTOR, f'.s-btn__{config.ingress_login_type}').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('google_login_init.png')

        log.info('Enter username...')
        driver.save_screenshot('{}/{}'.format(str(debug_dir), "10.png"))
        # import pdb;pdb.set_trace()
        try:
            driver.find_element(By.XPATH, '//*[@id="identifierId"]').send_keys(config.ingress_user)
            driver.save_screenshot('{}/{}'.format(str(debug_dir), "11.png"))
            driver.find_element(By.XPATH, '//*[@id="identifierNext"]/div/button/span').click()
            driver.save_screenshot('{}/{}'.format(str(debug_dir), "12.png"))
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('google_login_username.png')

        log.info('Enter password...')
        driver.save_screenshot('{}/{}'.format(str(debug_dir), "20.png"))
        try:
            driver.find_element(By.XPATH, '//*[@id="password"]/div[1]/div/div[1]/input').send_keys(config.ingress_password)
            driver.save_screenshot('{}/{}'.format(str(debug_dir), "21.png"))
            driver.find_element(By.XPATH, '//*[@id="passwordNext"]/div/button/span').click()
            driver.save_screenshot('{}/{}'.format(str(debug_dir), "22.png"))
            log.info('Password Click')
            time.sleep(10)
            driver.save_screenshot('{}/{}'.format(str(debug_dir), "23.png"))
            _save_screenshot('google_login_code.png')
            log.info('sleep 60sec')
            time.sleep(60)
        except NoSuchElementException:
            _save_screenshot_on_failure('google_login_password.png')

        log.info('Waiting for login...')
        time.sleep(5)

        if 'https://accounts.google.com/' in driver.current_url:
            log.info('Failed to login into Google')
            _save_screenshot_on_failure('google_login_security.png')

        log.info('Login to Intel Ingress')
        try:
            driver.get(('https://accounts.google.com/o/oauth2/v2/auth?'
                        'client_id=369030586920-h43qso8aj64ft2h5ruqsqlaia9g9huvn.apps.googleusercontent.com&'
                        'redirect_uri=https://intel.ingress.com/&prompt=consent%20select_account&state=GOOGLE'
                        '&scope=email%20profile&response_type=code'))
            driver.find_element("xpath","//div[@data-email='" + config.ingress_user + "']").click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('intel_login_init.png')

        log.info('Waiting for login...')
        time.sleep(5)
        final_cookie = _write_cookie(log, {c['name']: c['value'] for c in driver.get_cookies()})
    elif config.ingress_login_type == 'facebook':
        driver.get('http://intel.ingress.com')
        driver.find_element("xpath", '//div[@id="dashboard_container"]//a[@class="button_link" and contains(text(), "Facebook")]').click()
        driver.implicitly_wait(10)

        log.info('Enter username...')
        driver.find_element("xpath", '//*[@data-cookiebanner="accept_button"]').click()
        try:
            driver.find_element(By.ID, 'email').send_keys(config.ingress_user)
        except NoSuchElementException:
            _save_screenshot_on_failure('fb_login_username.png')

        log.info('Enter password...')
        try:
            driver.find_element(By.ID, 'pass').send_keys(config.ingress_password)
        except NoSuchElementException:
            _save_screenshot_on_failure('fb_login_password.png')

        log.info('Waiting for login...')
        try:
            driver.find_element(By.ID, 'loginbutton').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('fb_login_login.png')

        time.sleep(5)

        log.info('Confirm oauth login when needed...')
        try:
            driver.find_element(By.ID, 'platformDialogForm').submit()
            driver.implicitly_wait(10)
            time.sleep(5)
        except NoSuchElementException:
            pass

        final_cookie = _write_cookie(log, {c['name']: c['value'] for c in driver.get_cookies()})

    driver.quit()
    return final_cookie
