"""
This module contains code to log debug messages and output text
files more efficiently and easily using the built-in Python logging module. 
Currently, this is only set up to do one piece of logging at a time, using the
root logger. For information on logging, google "python logging".

In the future, it would be good to allow multiple logging at the same time. 
the top of each module, a statement like "logger = logging.getLogger(__name__)"
could be used, and all logging statements could then use "logger.info(msg)" after
configuring the logger. Then the logging would be organized by module.
"""
import logging
import logging.config
import json
import os

_baseLogger = None

################################################################################
# STATIC INPUT

################################################################################
# CLASS DEFINITIONS

# END OF CLASS DEFINITIONS
################################################################################
# FUNCTION DEFINITIONS

# class ResSimLogger(object):
#     """
#     """
#     __instance = None
#     __logger = None
#     __name = None
#     __config = None
    
#     def __new__(cls, cfgdict=None, logLevel=None):
#         """
#         """

#         if cls.__instance is None:
#             print("LOG: Setting up logging")
#             cls.__instance = super(ResSimLogger, cls).__new__(cls)
            
#             # Initialize logging
#             cls.__name = cfgdict.pop('basename')
#             cls.__config = cfgdict
            
#             logging.config.dictConfig(cfgdict)
#             cls.__logger = logging.getLogger(cls.__name)

#         if logLevel is not None:  # We use None instead of a default level so that the default from the config file can be used.
#             cls.__logger.setLevel(logLevel)
#         return cls.__instance

#     def getLogger(self, name, modelsys, logLevel=None):
#         """
#         Create a new logger

#         :param str name:
#         :param str modelsys:
#         :param logLevel
#         """

#         #if _baseLogger is None:
#         #    _baseLogger = configureLogging(network.makeAbsolutePathFromWatershed("shared/pyLoggingConfig.json"))
#         print('Getting Logger:', name, modelsys)
#         print(self.__logger)
#         print(self.__logger.name)
#         print(self.__name)
#         logger = logging.getLogger('.'.join((self.__name, modelsys, name)))
#         if logLevel is not None:
#             logger.setLevel(logLevel)

#         return logger

def configureLogging(basename, configDict):
    """
    Configure logging setup from JSON file, create and return the "base" logger.

    The base logger defaults to 'ResSim'. Note that it is one level down from the 
    root logger so as to allow future logging from other components.

    :param str logcfgFile: filename with logging configuration. 
    :param str basename: Base logger name, optional, default: ResSim
    """

    logging.config.dictConfig(configDict)
    logger =  logging.getLogger(basename)
    return logger

def getLogger(name, modelsys, logLevel=None):
    """
    Create a new logger

    :param network: ResSim network
    :param str name:
    :param str modelsys:
    :param logLevel
    """
    global _baseLogger

    if _baseLogger is None:
        moduleDirectory = os.path.normpath(os.path.dirname(__file__))
        watershedDirectory = moduleDirectory.split("\\scripts\\NWDJyLib")[0]
        logcfgFile = os.path.join(watershedDirectory, "scripts\\NWDJyLib\\rLoggingConfig.json")
        print(moduleDirectory)
        print(watershedDirectory)
        print(logcfgFile)
        configdict = json.load(open(logcfgFile, 'rt'))
        basename = configdict.pop('basename')
        _baseLogger = configureLogging(basename, configdict)

    logger = _baseLogger.getChild('.'.join((modelsys, name)))
    if logLevel is not None:  # We use None instead of a default level so that the default from the config file can be used.
        logger.setLevel(logLevel)

    return logger