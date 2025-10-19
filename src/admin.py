import flet as ft

class online_user(ft.Container):

    def __init__(self, username, is_online, avatar ):
        # self.vertical_alignment = ft.CrossAxisAlignment.START
        super().__init__(on_click=self.on_click_p, ink=True, height=65, width=280, border_radius=10)
        self.username = username
        self.is_online = is_online
        self.avatar = avatar
        self.content =ft.Row(
                                [
                                    ft.Container(
                                        ft.CircleAvatar(
                                            content= ft.Image(src=self.avatar),
                                            radius=20
                                        ),
                                        border_radius=30
                                    ),
                                    ft.Text(self.username, size=20)
                                ]
                        )

    def on_click_p(self, e):
        print("clicked")

def admin(page):

    online_users_container = ft.ListView(
        controls=[],
        height=700,
        width=300,
    )

    users_section = ft.Container(
        online_users_container,
        border_radius=10,
        bgcolor= ft.Colors.BLACK87
    )

    online_users_container.controls.append(
        online_user("sadra", is_online=True, avatar="assets/profile.png")
    )

    return ft.View(
        "/admin",
        controls=[
            users_section
        ],

    )



