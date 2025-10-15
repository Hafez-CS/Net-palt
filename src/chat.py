import flet as ft

class contact:
    def __init__(self, name, image_path):
        self.name = name
        self.image_path = image_path
        
        self.container = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        ft.CircleAvatar(
                        content=ft.Image(src=self.image_path),
                        radius=20,
                       ),
                       border_radius=30,
                    )
                    ,
                    ft.Text(self.name, size=16)
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
            ),
            padding=ft.padding.all(10),
            width=280,
            height=65,
            border_radius=10,
            alignment=ft.alignment.center_left,
            ink=True,
            on_click=self.on_click
        )
    def on_click(self, e):
        print(f"Contact {self.name} clicked!")


def user_chat(page):

    main_container = ft.Container(
        content= ft.ListView(
            width=450,
            height=600,
            expand=True,
        ),
        border_radius=10,
        width=450,
        bgcolor="#002A46",
    )

    chat_container = ft.Container(
        ft.Column([

            ft.Container(
                ft.ListView(
                    controls=[ft.Text("Chat with Alice", size=20, weight=ft.FontWeight.BOLD),],
                    expand=True,
                ),
                expand=True,
                border_radius=10,
                bgcolor="#001F2E",
                padding=ft.padding.all(10)

            ),

            ft.Row(
                [
                    ft.IconButton(ft.Icons.FILE_OPEN, on_click=lambda e: print("file open clicked")),
                    ft.TextField(label="Type a message", expand=True, border_radius=10, bgcolor="#004466", color=ft.Colors.WHITE, focused_border_color=ft.Colors.BLUE_200, height=50),
                    ft.IconButton(ft.Icons.SEND, on_click=lambda e: print("Send clicked")),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
            

        ],
        alignment=ft.MainAxisAlignment.END,
        ),
        bgcolor="#002D44",
        border_radius=10,
        expand=True,
        height=600,
        alignment=ft.alignment.bottom_center,
        padding=ft.padding.all(30)

    )

    for i in range(20):
        contact_container = contact(f"Contact {i+1}", "src/assets/profile.png").container
        main_container.content.controls.append(contact_container)

        
    return ft.View(
        "/main",
        [
            ft.Row(controls=[
                main_container,
                chat_container]

            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        auto_scroll=True,
        appbar= ft.AppBar(
            title=ft.Text("Chat Application"),
            center_title=True,
            bgcolor="#001F2E",
            actions=[
                ft.IconButton(ft.Icons.SEARCH, on_click=lambda e: print("Search clicked")),
                ft.IconButton(ft.Icons.MORE_VERT, on_click=lambda e: print("More clicked")),
            ],
        )

    )