import flet as ft
import models

def login_view(page):
    """Creates the login screen View."""
    page.window_height = 400
    page.window_width = 400
    page.window_resizable = False
    
    def autenticate_user(e):
        user_data = models.get_user_by_username(username.value)

        if username.value and password.value:
            if user_data:
                _, stored_password_hash, role = user_data
                if models.check_password_hash(password.value, stored_password_hash):
                    page.go("/main") 
                    return True, username, role
                else:
                    error = ft.AlertDialog(
                        title=ft.Text("Wrong Password"),
                        content=ft.Text("The password you entered is incorrect. Please try again."),
                        alignment=ft.alignment.center
                    )
                    page.open(error)
            else:
                error = ft.AlertDialog(
                title=ft.Text("user not found!"),
                content=ft.Text("the username you entered does not exist. please try again."),
                alignment=ft.alignment.center
                )

                page.open(error)
        else:
            error = ft.AlertDialog(
                title=ft.Text("empty fiealds"),
                content=ft.Text("please fill the fields and try again."),
                alignment=ft.alignment.center
                )

            page.open(error)


    username = ft.TextField(label="Username", width=300, icon=ft.Icons.EMAIL)
    password = ft.TextField(
                            label="Password",
                            width=300,
                            password=True,
                            can_reveal_password=True,
                            icon=ft.Icons.LOCK
                        )
    return ft.View(
        "/",  # Define the route for this view
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Welcome Back! 🔒", size=24, weight=ft.FontWeight.BOLD),
                        username,
                        password,

                        ft.ElevatedButton(
                            "Login",
                            width=300,
                            bgcolor=ft.Colors.BLUE_600,
                            color=ft.Colors.WHITE,
                            on_click=autenticate_user
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15
                ),
                alignment=ft.alignment.center,
                padding=25,
                width=page.width if page.width < 400 else 400,
                # Optional: Add a rounded border for a card-like look
                border_radius=10, 
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.Colors.BLACK26)
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )