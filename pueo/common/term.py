# gleaned from lots of different sources

class Term:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLACK = '\033[30m'
    WHITE = '\033[37m'

    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'    
    
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'
    END = '\033[0m'

    CURSOR_POS = lambda x, y : f'\033[{x};{y}f'
    CURSOR_HOME = '\033[H'
    CURSOR_UP = lambda x : f'\033[{x}A'
    CURSOR_DOWN = lambda x : f'\033[{x}B'
    CURSOR_RIGHT = lambda x : f'\033[{x}C'
    CURSOR_LEFT = lambda x : f'\033[{x}D'
    CURSOR_SAVE = '\0337'
    CURSOR_RESTORE = '\0338'

    CLEAR_SCREEN = '\033[2J'
    CLEAR_LINE_RIGHT = '\033[K'
    CLEAR_LINE_LEFT = '\033[1K'
    CLEAR_LINE = '\033[2K'

    SET_TITLE = lambda x : f'\033]2;{x}\007'
    
