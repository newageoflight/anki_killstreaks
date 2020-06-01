from aqt.qt import QDialog, QThread, pyqtSignal

from functools import partial
import json
from queue import Queue
from urllib.parse import urljoin
import webbrowser

from . import accounts
from .networking import sra_base_url
from .ui.forms.profile_settings_dialog import Ui_ProfileSettingsDialog


def show_dialog(parent, network_thread, user_repo):
    ProfileSettingsDialog(parent, network_thread, user_repo).exec_()


class ProfileSettingsDialog(QDialog):
    loginPageIndex = 0
    logoutPageIndex = 1

    logged_in = pyqtSignal(dict)
    unauthorized_login = pyqtSignal(dict)

    def __init__(self, parent, network_thread, user_repo):
        super().__init__(parent)
        self.ui = Ui_ProfileSettingsDialog()
        self.ui.setupUi(self)

        self._network_thread = network_thread
        self._user_repo = user_repo

        self._connect_login_signals()

        self._connect_login_button()
        self._connect_logout_button()
        self._connect_signup_button()

    def _connect_login_signals(self):
        self.logged_in.connect(self.on_successful_login)
        self.unauthorized_login.connect(self.on_unauthorized)

    def _connect_login_button(self):
        self.ui.loginButton.clicked.connect(self._login)

    def _login(self):
        email = self.ui.emailLineEdit.text()
        password = self.ui.passwordLineEdit.text()

        login_job = partial(
            accounts.login,
            email,
            password,
            listener=self,
            user_repo=self._user_repo,
        )
        self._network_thread.perform_later(login_job)

    def on_successful_login(self, user_attrs):
        self._switchToLogoutPage(user_attrs)
        self._clear_login_form()

    def _switchToLogoutPage(self, user_attrs):
        self.ui.userEmailLabel.setText(user_attrs["email"])
        self.ui.stackedWidget.setCurrentIndex(self.logoutPageIndex)

    def _clear_login_form(self):
        email = self.ui.emailLineEdit.setText("")
        password = self.ui.passwordLineEdit.setText("")

    def on_unauthorized(self, response):
        self.ui.statusLabel.setText(response["errors"][0])

    def on_connection_error(self):
        self.ui.statusLabel.setText("Error connecting to server. Try again later.")

    def _connect_logout_button(self):
        self.ui.logoutButton.clicked.connect(self._logout)

    def _logout(self):
        logout_job = partial(
            accounts.logout,
            self._user_repo,
             listener=self
        )
        self._network_thread.perform_later(logout_job)
    
    def on_logout(self):
        self.ui.statusLabel.setText("User logged out successfully.")
        self._switchToLoginPage()
    
    def on_logout_error(self, response):
        self.ui.statusLabel.setText(response["errors"][0])
        self._switchToLoginPage()
    
    def _switchToLoginPage(self):
        self.ui.stackedWidget.setCurrentIndex(self.loginPageIndex)

    def _connect_signup_button(self):
        signup_url = urljoin(sra_base_url, "users/sign_up")
        self.ui.signupLabel.linkActivated.connect(lambda: webbrowser.open(signup_url))

