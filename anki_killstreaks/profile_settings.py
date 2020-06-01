from aqt.qt import QDialog, QThread

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

    def __init__(self, parent, network_thread, user_repo):
        super().__init__(parent)
        self.ui = Ui_ProfileSettingsDialog()
        self.ui.setupUi(self)

        self._network_thread = network_thread
        self._user_repo = user_repo

        self._connect_login_button()
        self._connect_logout_button()
        self._connect_signup_button()

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

    def _switchToLogoutPage(self, user_attrs):
        self.ui.userEmailLabel.setText(user_attrs["email"])
        self.ui.stackedWidget.setCurrentIndex(self.logoutPageIndex)

    def on_unauthorized(self, response):
        self.ui.statusLabel.setText(response["errors"][0])

    def on_connection_error(self):
        self.ui.statusLabel.setText("Error connecting to server. Try again later.")

    def _connect_logout_button(self):
        self.ui.logoutButton.clicked.connect(self._logout)

    def _logout(self):
        logout_job = partial(accounts.logout, self._user_repo)
        self._network_thread.perform_later(logout_job)

    def _connect_signup_button(self):
        signup_url = urljoin(sra_base_url, "users/sign_up")
        self.ui.signupLabel.linkActivated.connect(lambda: webbrowser.open(signup_url))

