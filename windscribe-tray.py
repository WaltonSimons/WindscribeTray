import gtk
import gobject
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
import sys
import os

RUNNING = True
LOCATIONS = []
LOCATION = ''


def get_locations():
    locations = run_windscribe_command(['locations']).split('\n')
    locations.pop(0)
    locations.pop()
    loc_list = []
    for location in locations:
        loc = location.rsplit(' ', 1)
        loc_list.append((loc[0].strip(), loc[1].strip()))
    return loc_list


def message(data=None):
    msg = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                            gtk.MESSAGE_INFO, gtk.BUTTONS_OK, data)
    msg.run()
    msg.destroy()


def run_windscribe_command(commands, superuser=False):
    process = Popen((['sudo'] if superuser else []) + ['windscribe'] + commands, stdout=PIPE)
    res = process.communicate()[0]
    return res


def status_app(*args):
    data = run_windscribe_command(['status'])
    data = data.replace(',', '\n')
    message(data)


def close_app(*args):
    global RUNNING
    RUNNING = False
    gtk.main_quit()


def disconnect_app(*args):
    run_windscribe_command(['disconnect'])
    global LOCATION
    LOCATION = ''


def connect_to_location(code):
    run_windscribe_command(['connect', code])
    global LOCATION
    LOCATION = code


def create_location_submenu():
    menu_item = gtk.MenuItem('Location [%s]' % LOCATION)
    menu = gtk.Menu()
    menu_item.set_submenu(menu)
    loc_list = LOCATIONS
    for name, code in loc_list:
        item = gtk.MenuItem(name)
        menu.append(item)
        item.connect_object('activate', connect_to_location, code)
    return menu_item


def make_menu(event_button, event_time):
    menu = gtk.Menu()
    status_item = gtk.MenuItem('VPN Status')
    location_item = create_location_submenu()
    disconnect_item = gtk.MenuItem('Disconnect')
    close_item = gtk.MenuItem('Close App')

    menu.append(status_item)
    menu.append(location_item)
    menu.append(disconnect_item)
    menu.append(close_item)

    status_item.connect_object('activate', status_app, None)
    disconnect_item.connect_object('activate', disconnect_app, None)
    close_item.connect_object('activate', close_app, None)

    status_item.show()
    close_item.show()
    disconnect_item.show()
    location_item.show_all()

    menu.popup(None, None, None, event_button, event_time)


def on_right_click(data, event_button, event_time):
    make_menu(event_button, event_time)


def update(icon, gtk_thread):
    try:
        while RUNNING:
            if 'DISCONNECTED' not in run_windscribe_command(['status']):
                icon.set_from_stock(gtk.STOCK_CONNECT)
            else:
                icon.set_from_stock(gtk.STOCK_DISCONNECT)
            sleep(1)
    except KeyboardInterrupt:
        gtk.main_quit()


def startup():
    is_superuser = os.getuid() == 0
    if 'status: running' not in run_windscribe_command(['status']):
        if is_superuser:
            print 'Starting windscribe.'
            run_windscribe_command(['start'], superuser=True)
            print 'Windscribe started.'
        else:
            print 'Windscribe is not running. Please start windscribe manually or run this script as a superuser.'
            sys.exit(1)
    global LOCATIONS
    LOCATIONS = get_locations()
    status = run_windscribe_command(['status'])
    for (name, code) in LOCATIONS:
        if name in status:
            global LOCATION
            LOCATION = code

if __name__ == '__main__':
    startup()
    icon = gtk.status_icon_new_from_stock(gtk.STOCK_CONNECT)
    icon.connect('popup-menu', on_right_click)
    gtk.threads_init()
    gtk_thread = Thread(target=gtk.main)

    gtk_thread.start()

    update(icon, gtk_thread)
