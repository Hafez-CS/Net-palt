import flet as ft

class contact:
    def __init__(self, name, image_path):
        self.name = name
        self.image_path = image_path
        
        self.container = ft.Container(
            content=ft.Row(
                [
                    ft.CircleAvatar(
                        content=ft.Image(src=self.image_path, fit=ft.ImageFit.COVER),
                        radius=20,
                    ),
                    ft.Text(self.name, size=16)
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10
            ),
            padding=ft.padding.all(10),
            width=280,
            height=60,
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
            width=300,
            height=500
        ),
        alignment=ft.alignment.center,
    )

    for i in range(20):
        contact_container = contact(f"Contact {i+1}", "assets/user.png").container
        main_container.content.controls.append(contact_container)

        
    return ft.View(
        "/main",
        [
            main_container
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )