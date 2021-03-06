# An example of embedding CEF browser in PyGTK on Linux.

import ctypes, os, sys
libcef_so = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libcef.so')
if os.path.exists(libcef_so):
    # Import local module
    ctypes.CDLL(libcef_so, ctypes.RTLD_GLOBAL)
    if 0x02070000 <= sys.hexversion < 0x03000000:
        import cefpython_py27 as cefpython
    else:
        raise Exception("Unsupported python version: %s" % sys.version)
else:
    # Import from package
    from cefpython1 import cefpython

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import re

def GetApplicationPath(file=None):
    import re, os, platform
    # If file is None return current directory without trailing slash.
    if file is None:
        file = ""
    # Only when relative path.
    if not file.startswith("/") and not file.startswith("\\") and (
            not re.search(r"^[\w-]+:", file)):
        if hasattr(sys, "frozen"):
            path = os.path.dirname(sys.executable)
        elif "__file__" in globals():
            path = os.path.dirname(os.path.realpath(__file__))
        else:
            path = os.getcwd()
        path = path + os.sep + file
        if platform.system() == "Windows":
            path = re.sub(r"[/\\]+", re.escape(os.sep), path)
        path = re.sub(r"[/\\]+$", "", path)
        return path
    return str(file)

def ExceptHook(excType, excValue, traceObject):
    import traceback, os, time, codecs
    # This hook does the following: in case of exception write it to
    # the "error.log" file, display it to the console, shutdown CEF
    # and exit application immediately by ignoring "finally" (_exit()).
    errorMsg = "\n".join(traceback.format_exception(excType, excValue,
            traceObject))
    errorFile = GetApplicationPath("error.log")
    try:
        appEncoding = cefpython.g_applicationSettings["string_encoding"]
    except:
        appEncoding = "utf-8"
    if type(errorMsg) == bytes:
        errorMsg = errorMsg.decode(encoding=appEncoding, errors="replace")
    try:
        with codecs.open(errorFile, mode="a", encoding=appEncoding) as fp:
            fp.write("\n[%s] %s\n" % (
                    time.strftime("%Y-%m-%d %H:%M:%S"), errorMsg))
    except:
        print("cefpython: WARNING: failed writing to error file: %s" % (
                errorFile))
    # Convert error message to ascii before printing, otherwise
    # you may get error like this:
    # | UnicodeEncodeError: 'charmap' codec can't encode characters
    errorMsg = errorMsg.encode("ascii", errors="replace")
    errorMsg = errorMsg.decode("ascii", errors="replace")
    print("\n"+errorMsg+"\n")
    cefpython.QuitMessageLoop()
    cefpython.Shutdown()
    os._exit(1)

class PyGTKExample:

    mainWindow = None
    container = None
    browser = None
    exiting = None
    searchEntry = None
    vbox = None

    def __init__(self):

        self.mainWindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.mainWindow.connect('destroy', self.OnExit)
        self.mainWindow.set_size_request(width=600, height=400)
        self.mainWindow.set_title('PyGTK CEF example')
        self.mainWindow.realize()

        self.vbox = gtk.VBox(False, 0)
        self.vbox.pack_start(self.CreateMenu(), False, False, 0)
        self.mainWindow.add(self.vbox)

        m = re.search("GtkVBox at 0x(\w+)", str(self.vbox))
        hexID = m.group(1)
        windowID = int(hexID, 16)

        windowInfo = cefpython.WindowInfo()
        windowInfo.SetAsChild(windowID)
        # Linux requires adding "file://" for local files,
        # otherwise /home/some will be replaced as http://home/some
        self.browser = cefpython.CreateBrowserSync(
            windowInfo,
            # Flash will crash app in CEF 1 on Linux, setting
            # plugins_disabled to True.
            browserSettings={"plugins_disabled": True},
            navigateUrl="file://"+GetApplicationPath("cefsimple.html"))

        # Must be show_all() for VBox otherwise browser doesn't
        # appear when you just call show().
        self.vbox.show()

        self.mainWindow.show()
        gobject.timeout_add(10, self.OnTimer)

    def CreateMenu(self):

        file = gtk.MenuItem('File')
        file.show()
        filemenu = gtk.Menu()
        item = gtk.MenuItem('Open')
        filemenu.append(item)
        item.show()
        item = gtk.MenuItem('Exit')
        filemenu.append(item)
        item.show()
        file.set_submenu(filemenu)

        about = gtk.MenuItem('About')
        about.show()
        aboutmenu = gtk.Menu()
        item = gtk.MenuItem('CEF Python')
        aboutmenu.append(item)
        item.show()
        about.set_submenu(aboutmenu)

        menubar = gtk.MenuBar()
        menubar.append(file)
        menubar.append(about)
        menubar.show()

        return menubar

    def OnWidgetClick(self, widget, data):

        self.mainWindow.get_window().focus()

    def OnTimer(self):

        if self.exiting:
            return False
        cefpython.MessageLoopWork()
        return True

    def OnFocusIn(self, widget, data):

        # This function is currently not called by any of code,
        # but if you would like for browser to have automatic focus
        # add such line:
        # self.mainWindow.connect('focus-in-event', self.OnFocusIn)
        self.browser.SetFocus(True)

    def OnExit(self, widget, data=None):

        self.exiting = True
        gtk.main_quit()

if __name__ == '__main__':

    version = '.'.join(map(str, list(gtk.gtk_version)))
    print('GTK version: %s' % version)

    sys.excepthook = ExceptHook
    cefpython.g_debug = True
    cefpython.g_debugFile = GetApplicationPath("debug.log")
    settings = {
        "log_severity": cefpython.LOGSEVERITY_INFO,
        "log_file": GetApplicationPath("debug.log"),
        "release_dcheck_enabled": True, # Enable only when debugging.
        # This directories must be set on Linux
        "locales_dir_path": cefpython.GetModuleDirectory()+"/locales",
        "resources_dir_path": cefpython.GetModuleDirectory()
    }
    cefpython.Initialize(settings)

    gobject.threads_init() # timer for messageloop
    PyGTKExample()
    gtk.main()

    cefpython.Shutdown()
