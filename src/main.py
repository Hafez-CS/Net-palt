import flet as ft
import models
from chat import user_chat
from newlogin import login_view
from screeninfo import get_monitors
from admin import admin
# 1. Define the component or view function


# 2. Define the main function to run the app
def main(page: ft.Page):
    page.title = "Login window"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    # page.window_width = 200
    # page.window_height = 400
    page.window_resizable = False
    page.theme_mode = ft.ThemeMode.DARK

    
    # 3. Add the view to the page's view list
    # When an app starts, it automatically loads the last view in the list,
    # or the view that matches the initial route (which is "/" by default).
    def route_change(route):
        page.views.clear()

        if page.route == "/":
            page.views.append(login_view(page))
        elif page.route == "/main":
            page.views.append(user_chat(page))
        elif page.route == "/admin":
            page.views.append(admin(page))


        page.update()

    page.on_route_change = route_change
    # page.go(page.route)
    page.go("/admin")
    
# 4. Run the Flet app
if __name__ == "__main__":

    print(get_monitors())
    for m in get_monitors():
        if m.is_primary:
            primary_monitor = m
            break
    
    if primary_monitor:
        width = primary_monitor.width
        height = primary_monitor.height

    ft.app(target=main)