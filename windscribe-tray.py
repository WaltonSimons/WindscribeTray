from gi.repository import Gtk, GObject, Notify
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
import sys
import os


class WindscribeTray(object):

    def __init__(self):
        self.locations = self.get_locations()
        self.location = None
        self.running = False
        self.menu = None

    @staticmethod
    def run_windscribe_command(commands, superuser=False):
        process = Popen((['sudo'] if superuser else []) + ['windscribe'] + commands, stdout=PIPE)
        res = process.communicate()[0]
        return res

    @staticmethod
    def show_notification(title, body):
        notification = Notify.Notification.new(title, body)
        notification.show()

    def get_locations(self):
        locations = self.run_windscribe_command(['locations']).split('\n')
        locations.pop(0)
        locations.pop()
        loc_list = []
        for location in locations:
            loc = location.rsplit(' ', 1)
            loc_list.append((loc[0].strip(), loc[1].strip()))
        return loc_list

    def connect_to_location(self, code):
        self.run_windscribe_command(['connect', code])
        self.location = code
        self.show_notification('Connected', 'Connected to location: %s' % code)

    def create_location_submenu(self):
        menu_label = 'Location' + (('[%s]' % self.location) if self.location else '')
        menu_item = Gtk.MenuItem(menu_label)
        menu = Gtk.Menu()
        menu_item.set_submenu(menu)
        for name, code in self.locations:
            item = Gtk.MenuItem(name)
            menu.append(item)
            item.connect_object('activate', self.connect_to_location, code)
        return menu_item

    @staticmethod
    def show_message(data=None):
        msg = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL,
                                Gtk.MessageType.INFO, Gtk.ButtonsType.OK, data)
        msg.run()
        msg.destroy()

    def on_right_click(self, data, event_button, event_time):
        self.make_menu(event_button, event_time)

    def status(self, *args):
        data = self.run_windscribe_command(['status'])
        data = data.replace(',', '\n')
        self.show_message(data)

    def close(self, *args):
        self.running = False
        Gtk.main_quit()

    def disconnect(self, *args):
        res = self.run_windscribe_command(['disconnect'])
        self.location = None
        self.show_notification('Disconnected', 'VPN has been disconnected.')

    def make_menu(self, event_button, event_time):
        menu = Gtk.Menu()
        status_item = Gtk.MenuItem('VPN Status')
        location_item = self.create_location_submenu()
        disconnect_item = Gtk.MenuItem('Disconnect')
        close_item = Gtk.MenuItem('Close App')

        menu.append(status_item)
        menu.append(location_item)
        menu.append(disconnect_item)
        menu.append(close_item)

        status_item.connect_object('activate', self.status, None)
        disconnect_item.connect_object('activate', self.disconnect, None)
        close_item.connect_object('activate', self.close, None)

        status_item.show()
        close_item.show()
        disconnect_item.show()
        location_item.show_all()

        menu.popup(None, None, None, None, event_button, event_time)
        self.menu = menu

    def startup(self):
        is_superuser = os.getuid() == 0
        if 'status: running' not in self.run_windscribe_command(['status']):
            if is_superuser:
                print 'Starting windscribe.'
                self.run_windscribe_command(['start'], superuser=True)
                print 'Windscribe started.'
            else:
                print 'Windscribe is not running. Please start windscribe manually or run this script as a superuser.'
                sys.exit(1)
        status = self.run_windscribe_command(['status'])
        for (name, code) in self.locations:
            if name in status:
                self.location = code
        Notify.init("WindscribeTray")

    def update(self, icon):
        try:
            while self.running:
                if 'DISCONNECTED' not in self.run_windscribe_command(['status']):
                    icon.set_from_stock(Gtk.STOCK_CONNECT)
                else:
                    icon.set_from_stock(Gtk.STOCK_DISCONNECT)
                sleep(1)
        except KeyboardInterrupt:
            Gtk.main_quit()
        finally:
            Notify.uninit()

    def run(self):
        self.startup()
        self.running = True
        icon = Gtk.StatusIcon.new_from_stock(Gtk.STOCK_CONNECT)
        icon.connect('popup-menu', self.on_right_click)
        GObject.threads_init()
        gtk_thread = Thread(target=Gtk.main)

        gtk_thread.start()

        self.update(icon)

if __name__ == '__main__':
    WindscribeTray().run()
