import MetaTrader5 as mt5

class CTerminalInfo:
    def __init__(self):
        
        """CTerminalInfo class provides access to the properties of the MetaTrader5 program environment.
        
        """
        
        self._info = mt5.terminal_info()
        
        if self._info is None:
            raise RuntimeError("Failed to retrieve terminal info: ", mt5.last_error())
    
    def is_valid(self):
        return self._info is not None

    def is_connected(self):
        return self._info.connected

    def is_dlls_allowed(self):
        return self._info.dlls_allowed

    def is_trade_allowed(self):
        return self._info.trade_allowed

    def is_email_enabled(self):
        return self._info.email_enabled

    def is_ftp_enabled(self):
        return self._info.ftp_enabled

    def is_community_account(self):
        return self._info.community_account

    def is_community_connection(self):
        return self._info.community_connection

    def are_notifications_enabled(self):
        return self._info.notifications_enabled

    def is_mqid(self):
        return self._info.mqid

    def is_tradeapi_disabled(self):
        return self._info.tradeapi_disabled

    def build(self):
        return self._info.build

    def max_bars(self):
        return self._info.maxbars

    def code_page(self):
        return self._info.codepage

    def ping_last(self):
        return self._info.ping_last

    def community_balance(self):
        return self._info.community_balance

    def retransmission(self):
        return self._info.retransmission

    def name(self):
        return self._info.name

    def company(self):
        return self._info.company

    def language(self):
        return self._info.language

    def path(self):
        return self._info.path

    def data_path(self):
        return self._info.data_path

    def common_data_path(self):
        return self._info.commondata_path
