import sys, time, re, json, requests
from collections import OrderedDict, defaultdict
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from threading import Lock, Thread
from flask import Flask, request, Response, render_template
from multiprocessing import Queue
from pyvirtualdisplay import Display
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

current_avaliable_bookings = defaultdict(list)
last_bookings_update = None
booking_lock = Lock()
userbookings = defaultdict(list)

users = []
users.append({'nick':'rick', 'username':'rjavelind@gmail.com', 'password':'tomte123'})

display = Display(visible=0, size=(800, 600))
display.start()

binary = FirefoxBinary('/usr/bin/firefox')
driver = webdriver.Firefox(firefox_binary=binary)

wait = ui.WebDriverWait(driver,20)

def get_lane_name_by_id(laneID):
    if int(laneID) > 80:
        return str(26 + int(laneID[1]))
    else:
        return 'Grus ' + str(int(laneID[1]) - 6)

def get_avaliable_bookings():
    driver.get('https://v7003-profitwebsite.pastelldata.com/Start.aspx?GUID=1538&ISIFRAME=0&UNIT=1538&PAGE=LOKALBOKNING')
    try:
        element = wait.until(lambda driver: driver.find_element_by_id('ContentPlaceHolder1_TreatmentBookWUC1_ctl07'))
        element.click()
    except Exception as e:
        print(e)
        driver.quit()
        sys.exit()
        return
    links = []
    for day_id in range(16,23):
        elem = wait.until(lambda driver: driver.find_element_by_xpath(
                                  '//*[@id="ContentPlaceHolder1_TreatmentBookWUC1_ctl'+str(day_id)+'"]/span'))
        parent_text = elem.text
        elem.click()
        time.sleep(1)
        link_elements = driver.find_elements_by_xpath('//a[contains(@href, "AvailableProducts.aspx")]')
        for link_element in link_elements:
            links.append({'parent_text': parent_text, 'link': link_element.get_attribute('href')})

    avaliable_bookings = []
    for link in links:
        m = re.search(r'RID=(\d+(\d{2})).AID=(\d+).DATE=(\d+).DATEHR=((\d{4}-\d{2}-\d{2})%20((\d{2}):(\d{2})))', link['link'])
        obj = {
            'headertext':   link['parent_text'],
            'param_RID':    m.group(1), #RID
            'laneID':       m.group(2),
            'lane':         get_lane_name_by_id(m.group(2)), #Lane -readable
            'param_AID':    m.group(3), #AID
            'param_DATE':   m.group(4), #DATE
            'param_DATEHR': m.group(5), #DATEHR
            'date':         m.group(6), #Date -readable
            'time':         m.group(7), #time -readable
            'hour':         m.group(8), #hour -readable
            'minute':       m.group(9)  #minute -readable
        }
        avaliable_bookings.append(obj)
    return avaliable_bookings

def refresh_bookings():
    global current_avaliable_bookings
    global last_bookings_update
    while(True):
        new_avaliable_bookings = get_avaliable_bookings()
        if new_avaliable_bookings:
            with booking_lock:
                current_avaliable_bookings = new_avaliable_bookings
                last_bookings_update = time.strftime('%Y-%m-%d %H:%M:%S')
        time.sleep(60)

def send_book(nick, booking):
    userinfo = [x for x in users if x['nick'] == nick][0]
    loggedin_driver = webdriver.Firefox(firefox_binary=binary)
    loggedin_wait = ui.WebDriverWait(driver,20)
    loggedin_driver.get('https://v7003-profitwebsite.pastelldata.com/Start.aspx?GUID=1538&ISIFRAME=0&UNIT=1538&PAGE=LOKALBOKNING')
    loggedin_wait.until(lambda driver: loggedin_driver.find_element_by_xpath('//*[@id="SiteNavigationWUC_SITENAVIGATION_LOGIN"]'))

    loggedin_driver.find_element_by_xpath('//*[@id="SiteNavigationWUC_SITENAVIGATION_LOGIN"]').click()
    loggedin_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_UserName"]').send_keys(userinfo['username'])
    loggedin_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_Password"]').send_keys(userinfo['password'])
    loggedin_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_LoginButton"]').click()
    time.sleep(2)
    session = re.search(r'pastelldata\.com/([^/]+)', loggedin_driver.current_url)
    url = ('https://v7003-profitwebsite.pastelldata.com/' + session.group(1) + '/' + '/treatment/AvailableProducts.aspx?RID=' + booking['param_RID']
          +'&AID=' + booking['param_AID'] + '&DATE=' + booking['param_DATE'] + '&UID=1538')
    time.sleep(0.2)
    loggedin_driver.get(url)
    loggedin_driver.find_element_by_xpath('/html/body/div/a').click()
    try:
        loggedin_wait.until(lambda driver: loggedin_driver.find_element_by_xpath('//*[@id="customerBookingDoneDialog"]'))
        user_bookings.append({'nick':userinfo['nick'], 'datetime':booking['param_DATEHR'], 'lane':lane, 'link':None, 'bookid':None})
        loggedin_driver.quit()
        return True
    except:
        loggedin_driver.quit()
        return False

def get_user_bookings():
    global userbookings
    while(True):
        bookid = 0
        new_user_bookings = []
        for user in users:
	    binary = FirefoxBinary('/usr/bin/firefox')
            user_driver = webdriver.Firefox(firefox_binary=binary)
            user_wait = ui.WebDriverWait(user_driver,10)
            user_driver.get('https://v7003-profitwebsite.pastelldata.com/Start.aspx?GUID=1538&ISIFRAME=0&UNIT=1538&PAGE=LOKALBOKNING')
            user_driver.find_element_by_xpath('//*[@id="SiteNavigationWUC_SITENAVIGATION_LOGIN"]').click()
            user_wait.until(lambda user_driver: user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_UserName"]'))
            user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_UserName"]').send_keys(user['username'])
            user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_Password"]').send_keys(user['password'])
            user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_LoginButton"]').click()
            user_wait.until(lambda user_driver: user_driver.find_element_by_xpath('//*[@id="SiteNavigationWUC_SITENAVIGATION_BOOKINGS"]')).click()
	    user_wait.until(lambda user_driver: user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_RadioButtonBookings"]'))
            cancel_links = user_driver.find_elements_by_xpath('//td[@class="ResBookingsTableCellDebookAllowed"]')
            for link in cancel_links:
                url = link.find_element_by_xpath('a').get_attribute('href')
                if link.text == 'Avboka':
                    elem = link.find_element_by_xpath('preceding-sibling::td[@class="table_cell"]')
                    datetime = elem.text
                    laneinfo = elem.find_element_by_xpath('following-sibling::td').text
                    m = re.search(r'.*-(.*)Tennis', laneinfo)
                    lane = m.group(1).strip()
                    new_user_bookings.append({'nick':user['nick'], 'datetime':datetime, 'lane':lane, 'link':url, 'bookid':str(bookid)})
                    bookid += 1
            user_driver.quit()
            time.sleep(3)
        userbookings = new_user_bookings
        time.sleep(600)

def debook_booking(nick, bookid):
    global userbookings
    userinfo = [x for x in users if x['nick'] == nick][0]
    booking = [x for x in userbookings if x['bookid'] == bookid][0]
    user_driver = webdriver.Firefox(firefox_binary=binary)
    user_wait = ui.WebDriverWait(driver,5)
    user_driver.get('https://v7003-profitwebsite.pastelldata.com/Start.aspx?GUID=1538&ISIFRAME=0&UNIT=1538&PAGE=LOKALBOKNING')
    user_driver.find_element_by_xpath('//*[@id="SiteNavigationWUC_SITENAVIGATION_LOGIN"]').click()
    user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_UserName"]').send_keys(userinfo['username'])
    user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_Password"]').send_keys(userinfo['password'])
    user_driver.find_element_by_xpath('//*[@id="ContentPlaceHolder1_LoginView1_Login1_LoginButton"]').click()
    user_wait.until(lambda driver: user_driver.find_element_by_xpath('//*[@id="SiteNavigationWUC_SITENAVIGATION_BOOKINGS"]')).click()
    user_wait.until(lambda driver: user_driver.find_element_by_xpath('//a[contains(@href,"'+booking['link']+'")]')).click()
    time.sleep(1)
    alert = user_driver.switch_to_alert()
    alert.accept()
    try:
        alert.dismiss()
    except:
        pass
    try:
        user_wait.until_not(lambda driver: user_driver.find_element_by_xpath('//a[contains(@href,"'+booking['link']+'")]'))
        user_driver.quit()
        userbookings = [x for x in userbookings if x['bookid'] != bookid]
        return True
    except:
        user_driver.quit()
        return False



def init():
    t = Thread(target=refresh_bookings,
                   name='refresh_bookings')
    t.setDaemon(True)
    t.start()

    t2 = Thread(target=get_user_bookings,
                   name='get_user_bookings')
    t2.setDaemon(True)
    t2.start()

app = Flask(__name__)

@app.route('/<nick>')
def site_main(nick):
    current_header = ''
    #out = 'Last update: ' + str(last_bookings_update) + '\n\n'
    out = []

    for booking in current_avaliable_bookings:
        header = None
        if current_header != booking['headertext']:
            header = booking['headertext']
            current_header = booking['headertext']
        out.append({'header':header, 'line': booking['date'] + ' ' + booking['time'] + ' Bana ' + booking['lane'],
                    'link': '/book/' + nick + '/' + booking['param_DATE'] + '/' + booking['hour'] + '/' +
                    booking['minute'] + '/' + booking['laneID']})

    return render_template('list.html', booking = out, userbookings = [x for x in userbookings if x['nick'] == nick])

@app.route('/afterhour/<hour>/<nick>')
def afterhour(hour, nick):
    current_header = ''
    out = 'Last update: ' + str(last_bookings_update) + '\n\n'
    b = [booking for booking in current_avaliable_bookings if int(booking['hour']) >= int(hour)]
    out = []
    for booking in b:
        header = None
        if current_header != booking['headertext']:
            header = booking['headertext']
            current_header = booking['headertext']
        out.append({'header':header, 'line': booking['date'] + ' ' + booking['time'] + ' Bana ' + booking['lane'],
                    'link': '/book/' + nick + '/' + booking['param_DATE'] + '/' + booking['hour'] + '/' +
                    booking['minute'] + '/' + booking['laneID']})

    return render_template('list.html', booking = out, userbookings = [x for x in userbookings if x['nick'] == nick])

@app.route('/debook/<nick>/<bookid>')
def debook(nick,bookid):
    status = debook_booking(nick,bookid)
    return Response('Debooked!' if status else 'Debooking FALIED!', mimetype='text/html')

@app.route('/book/<nick>/<param_DATE>/<hour>/<minute>/<laneid>')
def book(nick, param_DATE, hour, minute, laneid):
    thebooking = [b for b in current_avaliable_bookings if b['param_DATE'] == param_DATE and b['hour'] == hour and b['minute'] == minute and b['laneID'] == laneid]
    if len(thebooking) > 1:
        return Response('WTF, more than one booking matched, fuck off!', mimetype='text/html')
    elif len(thebooking) == 0:
        return Response('WTF, no bookings found!', mimetype='text/html')

    book_ok = send_book(nick, thebooking[0])

    return Response('Booking complete' if book_ok else 'Booking falied', mimetype='text/html')


init()
