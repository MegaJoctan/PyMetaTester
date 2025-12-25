import MetaTrader5 as mt5

def trade_server_return_code_description(return_code: int) -> str:
    
    """Returns the description of a trade server return code."""
    
    descriptions = {
        mt5.TRADE_RETCODE_REQUOTE: "Requote",
        mt5.TRADE_RETCODE_REJECT: "Request rejected",
        mt5.TRADE_RETCODE_CANCEL: "Request canceled by trader",
        mt5.TRADE_RETCODE_PLACED: "Order placed",
        mt5.TRADE_RETCODE_DONE: "Request completed",
        mt5.TRADE_RETCODE_DONE_PARTIAL: "Only part of the request was completed",
        mt5.TRADE_RETCODE_ERROR: "Request processing error",
        mt5.TRADE_RETCODE_TIMEOUT: "Request canceled by timeout",
        mt5.TRADE_RETCODE_INVALID: "Invalid request",
        mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume in the request",
        mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price in the request",
        mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid stops in the request",
        mt5.TRADE_RETCODE_TRADE_DISABLED: "Trade is disabled",
        mt5.TRADE_RETCODE_MARKET_CLOSED: "Market is closed",
        mt5.TRADE_RETCODE_NO_MONEY: "There is not enough money to complete the request",
        mt5.TRADE_RETCODE_PRICE_CHANGED: "Prices changed",
        mt5.TRADE_RETCODE_PRICE_OFF: "There are no quotes to process the request",
        mt5.TRADE_RETCODE_INVALID_EXPIRATION: "Invalid order expiration date in the request",
        mt5.TRADE_RETCODE_ORDER_CHANGED: "Order state changed",
        mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "Too frequent requests",
        mt5.TRADE_RETCODE_NO_CHANGES: "No changes in request",
        mt5.TRADE_RETCODE_SERVER_DISABLES_AT: "Autotrading disabled by server",
        mt5.TRADE_RETCODE_CLIENT_DISABLES_AT: "Autotrading disabled by client terminal",
        mt5.TRADE_RETCODE_LOCKED: "Request locked for processing",
        mt5.TRADE_RETCODE_FROZEN: "Order or position frozen",
        mt5.TRADE_RETCODE_INVALID_FILL: "Invalid order filling type",
        mt5.TRADE_RETCODE_CONNECTION: "No connection with the trade server",
        mt5.TRADE_RETCODE_ONLY_REAL: "Operation is allowed only for live accounts",
        mt5.TRADE_RETCODE_LIMIT_ORDERS: "The number of pending orders has reached the limit",
        mt5.TRADE_RETCODE_LIMIT_VOLUME: "The volume of orders and positions for the symbol has reached the limit",
    }
    return descriptions.get(return_code, "Invalid return code of the trade server")

def error_description(err_code: int) -> str:
    
    """Returns the description of a runtime error code."""
    
    descriptions = {
        # Standard errors
        0: "The operation completed successfully",
        1: "Unexpected internal error",
        2: "Wrong parameter in the inner call of the client terminal function",
        3: "Wrong parameter when calling the system function",
        4: "Not enough memory to perform the system function",
        5: "The structure contains objects of strings and/or dynamic arrays and/or structure of such objects and/or classes",
        6: "Array of a wrong type, wrong size, or a damaged object of a dynamic array",
        7: "Not enough memory for the relocation of an array, or an attempt to change the size of a static array",
        8: "Not enough memory for the relocation of string",
        9: "Not initialized string",
        10: "Invalid date and/or time",
        11: "Requested array size exceeds 2 GB",
        12: "Wrong pointer",
        13: "Wrong type of pointer",
        14: "System function is not allowed to call",
        
        # Chart errors
        4001: "Wrong chart ID",
        4002: "Chart does not respond",
        4003: "Chart not found",
        4004: "No Expert Advisor in the chart that could handle the event",
        4005: "Chart opening error",
        4006: "Failed to change chart symbol and period",
        4007: "Failed to create timer",
        4008: "Wrong chart property ID",
        4009: "Error creating screenshots",
        4010: "Error navigating through chart",
        4011: "Error applying template",
        4012: "Subwindow containing the indicator was not found",
        4013: "Error adding an indicator to chart",
        4014: "Error deleting an indicator from the chart",
        4015: "Indicator not found on the specified chart",
        
        # Graphical Objects errors
        4201: "Error working with a graphical object",
        4202: "Graphical object was not found",
        4203: "Wrong ID of a graphical object property",
        4204: "Unable to get date corresponding to the value",
        4205: "Unable to get value corresponding to the date",
        
        # MarketInfo errors
        4301: "Unknown symbol",
        4302: "Symbol is not selected in MarketWatch",
        4303: "Wrong identifier of a symbol property",
        4304: "Time of the last tick is not known (no ticks)",
        4305: "Error adding or deleting a symbol in MarketWatch",
        
        # History Access errors
        4401: "Requested history not found",
        4402: "Wrong ID of the history property",
        
        # Global Variables errors
        4501: "Global variable of the client terminal is not found",
        4502: "Global variable of the client terminal with the same name already exists",
        4503: "Email sending failed",
        4504: "Sound playing failed",
        4505: "Wrong identifier of the program property",
        4506: "Wrong identifier of the terminal property",
        4507: "File sending via ftp failed",
        4508: "Error in sending notification",
        
        # Custom Indicator errors
        4601: "Not enough memory for the distribution of indicator buffers",
        4602: "Wrong indicator buffer index",
        4603: "Wrong ID of the custom indicator property",
        
        # Account errors
        4701: "Wrong account property ID",
        4702: "Wrong trade property ID",
        4703: "Trading by Expert Advisors prohibited",
        4704: "Position not found",
        4705: "Order not found",
        4706: "Deal not found",
        4707: "Trade request sending failed",
        
        # Indicator errors
        4801: "Unknown symbol",
        4802: "Indicator cannot be created",
        4803: "Not enough memory to add the indicator",
        4804: "The indicator cannot be applied to another indicator",
        4805: "Error applying an indicator to chart",
        4806: "Requested data not found",
        4807: "Wrong indicator handle",
        4808: "Wrong number of parameters when creating an indicator",
        4809: "No parameters when creating an indicator",
        4810: "The first parameter in the array must be the name of the custom indicator",
        4811: "Invalid parameter type in the array when creating an indicator",
        4812: "Wrong index of the requested indicator buffer",
        
        # Depth of Market errors
        4901: "Depth Of Market can not be added",
        4902: "Depth Of Market can not be removed",
        4903: "The data from Depth Of Market can not be obtained",
        4904: "Error in subscribing to receive new data from Depth Of Market",
        
        # File Operations errors
        5001: "More than 64 files cannot be opened at the same time",
        5002: "Invalid file name",
        5003: "Too long file name",
        5004: "File opening error",
        5005: "Not enough memory for cache to read",
        5006: "File deleting error",
        5007: "A file with this handle was closed, or was not opening at all",
        5008: "Wrong file handle",
        5009: "The file must be opened for writing",
        5010: "The file must be opened for reading",
        5011: "The file must be opened as a binary one",
        5012: "The file must be opened as a text",
        5013: "The file must be opened as a text or CSV",
        5014: "The file must be opened as CSV",
        5015: "File reading error",
        5016: "String size must be specified, because the file is opened as binary",
        5017: "A text file must be for string arrays, for other arrays - binary",
        5018: "This is not a file, this is a directory",
        5019: "File does not exist",
        5020: "File can not be rewritten",
        5021: "Wrong directory name",
        5022: "Directory does not exist",
        5023: "This is a file, not a directory",
        5024: "The directory cannot be removed",
        5025: "Failed to clear the directory (probably one or more files are blocked and removal operation failed)",
        5026: "Failed to write a resource to a file",
        
        # String Casting errors
        5201: "No date in the string",
        5202: "Wrong date in the string",
        5203: "Wrong time in the string",
        5204: "Error converting string to date",
        5205: "Not enough memory for the string",
        5206: "The string length is less than expected",
        5207: "Too large number, more than ULONG_MAX",
        5208: "Invalid format string",
        5209: "Amount of format specifiers more than the parameters",
        5210: "Amount of parameters more than the format specifiers",
        5211: "Damaged parameter of string type",
        5212: "Position outside the string",
        5213: "0 added to the string end, a useless operation",
        5214: "Unknown data type when converting to a string",
        5215: "Damaged string object",
        
        # Array Operations errors
        5401: "Copying incompatible arrays. String array can be copied only to a string array, and a numeric array - in numeric array only",
        5402: "The receiving array is declared as AS_SERIES, and it is of insufficient size",
        5403: "Too small array, the starting position is outside the array",
        5404: "An array of zero length",
        5405: "Must be a numeric array",
        5406: "Must be a one-dimensional array",
        5407: "Timeseries cannot be used",
        5408: "Must be an array of type double",
        5409: "Must be an array of type float",
        5410: "Must be an array of type long",
        5411: "Must be an array of type int",
        5412: "Must be an array of type short",
        5413: "Must be an array of type char",
        
        # OpenCL errors
        5601: "OpenCL functions are not supported on this computer",
        5602: "Internal error occurred when running OpenCL",
        5603: "Invalid OpenCL handle",
        5604: "Error creating the OpenCL context",
        5605: "Failed to create a run queue in OpenCL",
        5606: "Error occurred when compiling an OpenCL program",
        5607: "Too long kernel name (OpenCL kernel)",
        5608: "Error creating an OpenCL kernel",
        5609: "Error occurred when setting parameters for the OpenCL kernel",
        5610: "OpenCL program runtime error",
        5611: "Invalid size of the OpenCL buffer",
        5612: "Invalid offset in the OpenCL buffer",
        5613: "Failed to create and OpenCL buffer",
    }
    
    # Handle user-defined errors (if needed)
    if err_code >= 65536:  # Example range for user-defined errors
        return f"User error {err_code - 65536}"
    
    return descriptions.get(err_code, "Unknown error")