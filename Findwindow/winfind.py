import win32gui

def find_window_by_title(title_substring):
    hwnds = []

    def enum_windows_proc(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title_substring.lower() in title.lower():
                hwnds.append((hwnd, title))

    win32gui.EnumWindows(enum_windows_proc, None)
    return hwnds

def find_first_window(title_substring):
    windows = find_window_by_title(title_substring)
    return windows[0] if windows else None

result = find_first_window("Fork")
if result:
    hwnd, title = result
    print(f"찾은 창: {title} (HWND: {hwnd})")
else:
    print("창을 찾을 수 없습니다.")
