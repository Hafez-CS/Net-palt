import flet as ft
import models
from src.chat import user_chat
from src.newlogin import login_view
# 1. Define the component or view function


# 2. Define the main function to run the app
def main(page: ft.Page):
    page.title = "Login window"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    # 3. Add the view to the page's view list
    # When an app starts, it automatically loads the last view in the list,
    # or the view that matches the initial route (which is "/" by default).
    def route_change(route):
        page.views.clear()

        if page.route == "/":
            page.views.append(login_view(page))
        elif page.route == "/main":
            page.views.append(user_chat(page))

        page.update()

    page.on_route_change = route_change
    page.go(page.route)

    
# 4. Run the Flet app
if __name__ == "__main__":
    ft.app(target=main)